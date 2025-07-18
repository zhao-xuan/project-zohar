"""
Tool Executor Agent for Multi-Agent Framework.

This module implements the tool executor agent that can handle tool calls
and execute various tools on behalf of other agents.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time
import json

from zohar.utils.logging import get_logger
from zohar.config.settings import get_settings
from .base_agent import BaseAgent
from .agent_types import AgentRole, AgentCapability
from .message_types import (
    Message, MessageType, MessageFactory, 
    ToolRequest, ToolResult, AgentRequest, AgentResponse
)
from zohar.tools.camel_tool_manager import CamelToolManager

logger = get_logger(__name__)


class ToolExecutorAgent(BaseAgent):
    """
    Tool executor agent that can handle tool calls.
    
    This agent:
    - Receives tool execution requests from other agents
    - Executes tools using CAMEL AI toolkits
    - Returns tool results to requesting agents
    - Manages tool execution lifecycle
    """
    
    def __init__(self, agent_id: str, model_name: str = None, **kwargs):
        """Initialize the tool executor agent."""
        self.settings = get_settings()
        
        super().__init__(
            agent_id=agent_id,
            name="ToolExecutor",
            model_name=model_name or "llama3.2:latest",  # Use tool-supporting model
            role=AgentRole.TOOL_EXECUTOR,
            capabilities=[
                AgentCapability.TOOL_CALLING,
                AgentCapability.CODE_EXECUTION,
                AgentCapability.MATH,
                AgentCapability.SEARCH,
                AgentCapability.WEATHER,
            ],
            description="Executes tools and provides results to other agents",
            **kwargs
        )
        
        # Tool management
        self.tool_manager = CamelToolManager()
        self.available_tools: Dict[str, Any] = {}
        self.tool_execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # Model for tool execution
        self.model = self._initialize_model()
        
        # Enhanced logging for tool execution process
        self.execution_log = []
        
        logger.info(f"Tool executor agent initialized with model: {self.model_name}")
    
    def _initialize_model(self):
        """Initialize the model for tool execution."""
        try:
            from camel.models import ModelFactory
            from camel.types import ModelPlatformType
            
            # Use a model that supports function calling
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OLLAMA,
                model_type=self.model_name,
                url="http://localhost:11434/v1",
                model_config_dict={
                    "temperature": 0.1,  # Lower temperature for tool execution
                    "max_tokens": 2048
                }
            )
            
            logger.info(f"✅ Model '{self.model_name}' initialized successfully for tool execution")
            return model
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize model '{self.model_name}': {e}")
            return None
    
    async def _initialize_components(self):
        """Initialize tool executor-specific components."""
        # Initialize CAMEL AI tool manager
        success = await self.tool_manager.initialize()
        if success:
            self.available_tools = self.tool_manager.get_available_tools()
            logger.info(f"✅ Initialized {len(self.available_tools)} tools")
            
            # Log available tools
            for tool_name, tool_info in self.available_tools.items():
                logger.debug(f"🔧 Available tool: {tool_name} ({tool_info.get('toolkit', 'unknown')})")
        else:
            logger.warning("❌ Failed to initialize tool manager")
        
        logger.info("Tool executor components initialized")
    
    async def _start_processes(self):
        """Start tool executor-specific processes."""
        # Start tool health monitoring
        asyncio.create_task(self._monitor_tool_health())
        
        logger.info("Tool executor processes started")
    
    async def _stop_processes(self):
        """Stop tool executor-specific processes."""
        # Shutdown tool manager
        if self.tool_manager:
            await self.tool_manager.shutdown()
    
    async def _handle_tool_request(self, message: Message) -> Optional[Message]:
        """Handle a tool execution request."""
        try:
            tool_name = message.metadata.get("tool_name")
            parameters = message.metadata.get("parameters", {})
            timeout = message.metadata.get("timeout", 30.0)
            
            logger.info(f"🛠️  Tool execution request received:")
            logger.info(f"   📋 Tool: {tool_name}")
            logger.info(f"   📝 Parameters: {json.dumps(parameters, indent=2)}")
            logger.info(f"   ⏱️  Timeout: {timeout}s")
            
            # Execute the tool
            result = await self._execute_tool(tool_name, parameters, timeout)
            
            # Create tool result message
            response = MessageFactory.create_tool_result(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                tool_name=tool_name,
                result=result.get("result"),
                success=result.get("success", True),
                error_message=result.get("error"),
                execution_time=result.get("execution_time")
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error handling tool request: {e}")
            return MessageFactory.create_error_message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                error_type="ToolExecutionError",
                error_details=str(e)
            )
    
    async def _handle_agent_request(self, message: Message) -> Optional[Message]:
        """Handle requests from other agents."""
        try:
            requested_capability = message.metadata.get("requested_capability")
            task_description = message.content
            required_tools = message.metadata.get("required_tools", [])
            
            logger.info(f"🤖 Agent request received:")
            logger.info(f"   📋 Task: {task_description[:100]}...")
            logger.info(f"   🎯 Capability: {requested_capability}")
            logger.info(f"   🔧 Required tools: {required_tools}")
            
            # Determine which tools are needed
            tools_needed = self._determine_required_tools(task_description, required_tools)
            
            if not tools_needed:
                logger.info("ℹ️  No tools required for this task")
                return MessageFactory.create_agent_response(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    result="No tools required for this task",
                    confidence=1.0
                )
            
            logger.info(f"🔍 Determined tools needed: {tools_needed}")
            
            # Execute tools and synthesize results
            tool_results = {}
            for tool_name in tools_needed:
                try:
                    logger.info(f"🔄 Processing tool: {tool_name}")
                    
                    # Extract parameters from task description
                    parameters = self._extract_tool_parameters(task_description, tool_name)
                    logger.info(f"   📝 Extracted parameters: {json.dumps(parameters, indent=2)}")
                    
                    # Execute tool
                    result = await self._execute_tool(tool_name, parameters)
                    tool_results[tool_name] = result
                    
                    logger.info(f"   ✅ Tool execution completed: {tool_name}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Error executing tool {tool_name}: {e}")
                    tool_results[tool_name] = {
                        "success": False,
                        "error": str(e),
                        "result": None
                    }
            
            # Synthesize results
            logger.info("🧠 Synthesizing tool results...")
            final_result = self._synthesize_tool_results(task_description, tool_results)
            
            logger.info(f"✅ Task completed successfully")
            
            return MessageFactory.create_agent_response(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                result=final_result,
                confidence=0.9,
                tools_used=list(tools_needed),
                execution_time=sum(
                    result.get("execution_time", 0) 
                    for result in tool_results.values() 
                    if result.get("success")
                )
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling agent request: {e}")
            return MessageFactory.create_error_message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                error_type="AgentRequestError",
                error_details=str(e)
            )
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Execute a specific tool with detailed logging."""
        start_time = time.time()
        execution_id = f"exec_{int(start_time * 1000)}"
        
        logger.info(f"🚀 Starting tool execution [{execution_id}]:")
        logger.info(f"   🔧 Tool: {tool_name}")
        logger.info(f"   📝 Parameters: {json.dumps(parameters, indent=2)}")
        logger.info(f"   ⏱️  Timeout: {timeout}s")
        
        # Log execution start
        self._log_execution_step(execution_id, "START", {
            "tool_name": tool_name,
            "parameters": parameters,
            "timeout": timeout
        })
        
        try:
            # Check if tool is available
            if tool_name not in self.available_tools:
                error_msg = f"Tool '{tool_name}' not available"
                logger.error(f"   ❌ {error_msg}")
                self._log_execution_step(execution_id, "TOOL_NOT_FOUND", {"error": error_msg})
                
                return {
                    "success": False,
                    "error": error_msg,
                    "result": None,
                    "execution_time": time.time() - start_time
                }
            
            logger.info(f"   ✅ Tool '{tool_name}' found in available tools")
            self._log_execution_step(execution_id, "TOOL_FOUND", {"tool_info": self.available_tools[tool_name]})
            
            # Execute tool with timeout
            logger.info(f"   🔄 Executing tool with timeout...")
            self._log_execution_step(execution_id, "EXECUTION_START", {})
            
            task = asyncio.create_task(self._execute_tool_async(tool_name, parameters))
            
            try:
                result = await asyncio.wait_for(task, timeout=timeout)
                execution_time = time.time() - start_time
                
                logger.info(f"   ✅ Tool execution completed successfully")
                logger.info(f"   📊 Execution time: {execution_time:.2f}s")
                logger.info(f"   📄 Result: {str(result)[:200]}...")
                
                # Log successful execution
                self._log_execution_step(execution_id, "EXECUTION_SUCCESS", {
                    "result": str(result)[:500],  # Truncate for logging
                    "execution_time": execution_time
                })
                
                # Update statistics
                self._update_tool_stats(tool_name, True, execution_time)
                
                return {
                    "success": True,
                    "result": result,
                    "execution_time": execution_time
                }
                
            except asyncio.TimeoutError:
                task.cancel()
                error_msg = f"Tool execution timed out after {timeout} seconds"
                logger.error(f"   ⏰ {error_msg}")
                self._log_execution_step(execution_id, "EXECUTION_TIMEOUT", {"timeout": timeout})
                
                return {
                    "success": False,
                    "error": error_msg,
                    "result": None,
                    "execution_time": time.time() - start_time
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"   ❌ Tool execution failed: {error_msg}")
            self._log_execution_step(execution_id, "EXECUTION_ERROR", {
                "error": error_msg,
                "execution_time": execution_time
            })
            
            self._update_tool_stats(tool_name, False, execution_time)
            
            return {
                "success": False,
                "error": error_msg,
                "result": None,
                "execution_time": execution_time
            }
    
    async def _execute_tool_async(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool asynchronously with detailed logging."""
        logger.info(f"   🔄 Executing tool function: {tool_name}")
        
        # Get tool function
        tool_func = self.tool_manager.get_tool_function(tool_name)
        if not tool_func:
            raise ValueError(f"Tool function not found: {tool_name}")
        
        logger.info(f"   ✅ Tool function retrieved successfully")
        
        # Execute tool
        if asyncio.iscoroutinefunction(tool_func):
            logger.info(f"   🔄 Executing async tool function...")
            result = await tool_func(**parameters)
        else:
            logger.info(f"   🔄 Executing sync tool function in thread pool...")
            # Run synchronous function in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, tool_func, **parameters)
        
        logger.info(f"   ✅ Tool function execution completed")
        return result
    
    def _determine_required_tools(self, task_description: str, required_tools: List[str]) -> List[str]:
        """Determine which tools are needed for a task with detailed logging."""
        logger.info(f"🔍 Analyzing task for required tools:")
        logger.info(f"   📋 Task: {task_description[:100]}...")
        logger.info(f"   🎯 Explicitly required: {required_tools}")
        
        if required_tools:
            # Use explicitly required tools
            available_required = [tool for tool in required_tools if tool in self.available_tools]
            logger.info(f"   ✅ Available required tools: {available_required}")
            return available_required
        
        # Analyze task description to determine tools
        task_lower = task_description.lower()
        tools_needed = []
        
        logger.info(f"   🔍 Analyzing task content for tool patterns...")
        
        # Math operations
        if any(word in task_lower for word in ["calculate", "math", "equation", "formula", "+", "-", "*", "/"]):
            math_tools = [tool for tool in self.available_tools if "math" in tool.lower()]
            tools_needed.extend(math_tools)
            logger.info(f"   ➕ Math operations detected -> tools: {math_tools}")
        
        # Code execution
        if any(word in task_lower for word in ["code", "program", "script", "execute", "run"]):
            code_tools = [tool for tool in self.available_tools if "code" in tool.lower()]
            tools_needed.extend(code_tools)
            logger.info(f"   💻 Code execution detected -> tools: {code_tools}")
        
        # Web search
        if any(word in task_lower for word in ["search", "find", "lookup", "information", "news"]):
            search_tools = [tool for tool in self.available_tools if "search" in tool.lower()]
            tools_needed.extend(search_tools)
            logger.info(f"   🔍 Search operations detected -> tools: {search_tools}")
        
        # Weather
        if any(word in task_lower for word in ["weather", "temperature", "forecast", "climate"]):
            weather_tools = [tool for tool in self.available_tools if "weather" in tool.lower()]
            tools_needed.extend(weather_tools)
            logger.info(f"   🌤️  Weather operations detected -> tools: {weather_tools}")
        
        unique_tools = list(set(tools_needed))  # Remove duplicates
        logger.info(f"   📊 Final tool selection: {unique_tools}")
        
        return unique_tools
    
    def _extract_tool_parameters(self, task_description: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters for a tool from task description with detailed logging."""
        logger.info(f"🔍 Extracting parameters for tool '{tool_name}':")
        logger.info(f"   📋 Task description: {task_description[:100]}...")
        
        # Simple parameter extraction - in a real implementation, this would be more sophisticated
        parameters = {}
        
        if "math" in tool_name.lower():
            # Extract numbers for math operations
            import re
            numbers = re.findall(r'\d+(?:\.\d+)?', task_description)
            if len(numbers) >= 2:
                parameters["a"] = float(numbers[0])
                parameters["b"] = float(numbers[1])
                logger.info(f"   ➕ Math parameters extracted: a={parameters['a']}, b={parameters['b']}")
        
        elif "search" in tool_name.lower():
            # Extract search query
            search_keywords = ["search for", "find", "lookup", "information about"]
            for keyword in search_keywords:
                if keyword in task_description.lower():
                    start_idx = task_description.lower().find(keyword) + len(keyword)
                    query = task_description[start_idx:].strip()
                    if query:
                        parameters["query"] = query
                        logger.info(f"   🔍 Search query extracted: '{query}'")
                        break
        
        elif "weather" in tool_name.lower():
            # Extract location for weather
            # This is a simplified version - real implementation would use NLP
            parameters["location"] = "current"  # Default to current location
            logger.info(f"   🌤️  Weather location set to: 'current'")
        
        logger.info(f"   📝 Final parameters: {json.dumps(parameters, indent=2)}")
        return parameters
    
    def _synthesize_tool_results(self, task_description: str, tool_results: Dict[str, Any]) -> str:
        """Synthesize results from multiple tool executions with detailed logging."""
        logger.info(f"🧠 Synthesizing results from {len(tool_results)} tools:")
        
        successful_results = []
        failed_results = []
        
        for tool_name, result in tool_results.items():
            if result.get("success"):
                successful_results.append(f"{tool_name}: {result.get('result')}")
                logger.info(f"   ✅ {tool_name}: Success")
            else:
                failed_results.append(f"{tool_name}: {result.get('error')}")
                logger.warning(f"   ❌ {tool_name}: {result.get('error')}")
        
        # Build response
        response_parts = []
        
        if successful_results:
            response_parts.append("Tool execution results:")
            response_parts.extend(successful_results)
            logger.info(f"   📊 {len(successful_results)} successful tool executions")
        
        if failed_results:
            response_parts.append("\nFailed tool executions:")
            response_parts.extend(failed_results)
            logger.warning(f"   ⚠️  {len(failed_results)} failed tool executions")
        
        if not response_parts:
            response_parts.append("No tools were executed.")
            logger.info(f"   ℹ️  No tools were executed")
        
        final_response = "\n".join(response_parts)
        logger.info(f"   📄 Final synthesized response: {final_response[:200]}...")
        
        return final_response
    
    def _log_execution_step(self, execution_id: str, step: str, data: Dict[str, Any]):
        """Log an execution step for detailed tracking."""
        step_log = {
            "execution_id": execution_id,
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.execution_log.append(step_log)
        
        # Keep only last 1000 entries to prevent memory issues
        if len(self.execution_log) > 1000:
            self.execution_log = self.execution_log[-1000:]
    
    def _update_tool_stats(self, tool_name: str, success: bool, execution_time: float):
        """Update tool execution statistics."""
        if tool_name not in self.tool_execution_stats:
            self.tool_execution_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "last_execution": None
            }
        
        stats = self.tool_execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += execution_time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
        stats["last_execution"] = datetime.now().isoformat()
        
        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
    
    async def _monitor_tool_health(self):
        """Monitor the health of available tools."""
        while self.is_active:
            try:
                # Check tool availability
                current_tools = self.tool_manager.get_available_tools()
                
                # Check for new tools
                new_tools = set(current_tools.keys()) - set(self.available_tools.keys())
                if new_tools:
                    logger.info(f"🆕 New tools available: {new_tools}")
                    self.available_tools.update({tool: current_tools[tool] for tool in new_tools})
                
                # Check for removed tools
                removed_tools = set(self.available_tools.keys()) - set(current_tools.keys())
                if removed_tools:
                    logger.warning(f"🗑️  Tools no longer available: {removed_tools}")
                    for tool in removed_tools:
                        del self.available_tools[tool]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in tool health monitoring: {e}")
                await asyncio.sleep(60)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.available_tools.keys())
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        return self.tool_execution_stats
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        return self.available_tools.get(tool_name)
    
    def get_execution_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution log entries."""
        return self.execution_log[-limit:] if self.execution_log else [] 