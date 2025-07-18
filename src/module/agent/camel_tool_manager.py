"""
CAMEL AI Tool Manager for Project Zohar.

This module provides integration with CAMEL AI's native toolkit system,
including built-in tools for web search, code execution, file operations,
communication, and data processing.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
from pathlib import Path

from config.settings import get_settings
from .logging import get_logger

# Initialize logger early
logger = get_logger(__name__)

# CAMEL AI imports with graceful fallbacks
try:
    # Core imports that should always work
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.types import RoleType
    
    # Try to import basic toolkits
    available_toolkits = {}
    
    try:
        from camel.toolkits import CodeExecutionToolkit
        available_toolkits['CodeExecutionToolkit'] = CodeExecutionToolkit
    except ImportError:
        logger.warning("CodeExecutionToolkit not available")
    
    try:
        from camel.toolkits import MathToolkit
        available_toolkits['MathToolkit'] = MathToolkit
    except ImportError:
        logger.warning("MathToolkit not available")
    
    try:
        from camel.toolkits import SearchToolkit
        available_toolkits['SearchToolkit'] = SearchToolkit
    except ImportError:
        logger.warning("SearchToolkit not available")
    
    try:
        from camel.toolkits import WeatherToolkit
        available_toolkits['WeatherToolkit'] = WeatherToolkit
    except ImportError:
        logger.warning("WeatherToolkit not available")
    
    try:
        from camel.toolkits import ArxivToolkit
        available_toolkits['ArxivToolkit'] = ArxivToolkit
    except ImportError:
        logger.warning("ArxivToolkit not available")
    
    # Try to import communication toolkits (optional)
    try:
        from camel.toolkits import SlackToolkit
        available_toolkits['SlackToolkit'] = SlackToolkit
    except ImportError:
        logger.debug("SlackToolkit not available")
    
    try:
        from camel.toolkits import TwitterToolkit
        available_toolkits['TwitterToolkit'] = TwitterToolkit
    except ImportError:
        logger.debug("TwitterToolkit not available")
    
    try:
        from camel.toolkits import LinkedInToolkit
        available_toolkits['LinkedInToolkit'] = LinkedInToolkit
    except ImportError:
        logger.debug("LinkedInToolkit not available")
    
    # Try to import OpenAI toolkits (may not be available)
    try:
        from camel.toolkits import OpenAIFunction
        available_toolkits['OpenAIFunction'] = OpenAIFunction
        OPENAI_FUNCTION_AVAILABLE = True
    except ImportError:
        logger.warning("OpenAIFunction not available")
        OPENAI_FUNCTION_AVAILABLE = False
    
    try:
        from camel.toolkits import OpenAIFunctionToolkit
        available_toolkits['OpenAIFunctionToolkit'] = OpenAIFunctionToolkit
        OPENAI_TOOLKITS_AVAILABLE = True
    except ImportError:
        logger.warning("OpenAI toolkits not available")
        OPENAI_TOOLKITS_AVAILABLE = False
    
    logger.info(f"Successfully imported {len(available_toolkits)} CAMEL AI toolkits")
    
except ImportError as e:
    logger.error(f"Failed to import core CAMEL AI components: {e}")
    # Make the toolkits optional for testing purposes
    available_toolkits = {}
    OPENAI_FUNCTION_AVAILABLE = False
    OPENAI_TOOLKITS_AVAILABLE = False
    logger.warning("CAMEL AI toolkits not available, running with limited functionality")


class CamelToolManager:
    """
    CAMEL AI Tool Manager for Project Zohar.
    
    Provides integration with CAMEL AI's native toolkit system,
    including automatic tool discovery, registration, and execution.
    """
    
    def __init__(self):
        """Initialize the CAMEL AI tool manager."""
        self.settings = get_settings()
        self.toolkits = {}
        self.available_tools = {}
        self.tool_functions = {}
        self.execution_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "by_tool": {}
        }
        
        logger.info("CAMEL AI Tool Manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the tool manager with CAMEL AI toolkits.
        
        Returns:
            Success status
        """
        try:
            # Initialize core toolkits
            await self._initialize_core_toolkits()
            
            # Initialize communication toolkits
            await self._initialize_communication_toolkits()
            
            # Initialize specialized toolkits
            await self._initialize_specialized_toolkits()
            
            # Register all tools
            await self._register_all_tools()
            
            logger.info(f"CAMEL AI Tool Manager initialized with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CAMEL AI Tool Manager: {e}")
            return False
    
    async def _initialize_core_toolkits(self):
        """Initialize core CAMEL AI toolkits."""
        try:
            # Code execution toolkit
            if 'CodeExecutionToolkit' in available_toolkits:
                self.toolkits['code_execution'] = available_toolkits['CodeExecutionToolkit']()
            
            # Math toolkit
            if 'MathToolkit' in available_toolkits:
                self.toolkits['math'] = available_toolkits['MathToolkit']()
            
            # Search toolkit (web search)
            if 'SearchToolkit' in available_toolkits:
                self.toolkits['search'] = available_toolkits['SearchToolkit']()
            
            # Weather toolkit
            if 'WeatherToolkit' in available_toolkits:
                self.toolkits['weather'] = available_toolkits['WeatherToolkit']()
            
            # ArXiv toolkit for research papers
            if 'ArxivToolkit' in available_toolkits:
                self.toolkits['arxiv'] = available_toolkits['ArxivToolkit']()
            
            logger.info("Core toolkits initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize core toolkits: {e}")
    
    async def _initialize_communication_toolkits(self):
        """Initialize communication toolkits."""
        try:
            # Slack toolkit
            if ('SlackToolkit' in available_toolkits and 
                hasattr(self.settings, 'slack_token') and self.settings.slack_token):
                self.toolkits['slack'] = available_toolkits['SlackToolkit'](token=self.settings.slack_token)
            
            # Twitter toolkit
            if ('TwitterToolkit' in available_toolkits and 
                hasattr(self.settings, 'twitter_api_key') and self.settings.twitter_api_key):
                self.toolkits['twitter'] = available_toolkits['TwitterToolkit'](
                    api_key=self.settings.twitter_api_key,
                    api_secret=self.settings.twitter_api_secret,
                    access_token=self.settings.twitter_access_token,
                    access_token_secret=self.settings.twitter_access_token_secret
                )
            
            # LinkedIn toolkit
            if ('LinkedInToolkit' in available_toolkits and 
                hasattr(self.settings, 'linkedin_access_token') and self.settings.linkedin_access_token):
                self.toolkits['linkedin'] = available_toolkits['LinkedInToolkit'](
                    access_token=self.settings.linkedin_access_token
                )
            
            logger.info("Communication toolkits initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize communication toolkits: {e}")
    
    async def _initialize_specialized_toolkits(self):
        """Initialize specialized toolkits that require API keys."""
        try:
            # Only initialize if OpenAI API key is available and toolkits are importable
            if (OPENAI_TOOLKITS_AVAILABLE and 
                hasattr(self.settings, 'openai_api_key') and 
                self.settings.openai_api_key):
                try:
                    # OpenAI toolkit
                    self.toolkits['openai'] = OpenAIFunctionToolkit(
                        api_key=self.settings.openai_api_key
                    )
                    
                    # GPT-4 Vision toolkit
                    self.toolkits['gpt_vision'] = GPT4VisionToolkit(
                        api_key=self.settings.openai_api_key
                    )
                    
                    logger.info("Specialized toolkits initialized with OpenAI API key")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI toolkits: {e}")
            else:
                logger.info("OpenAI API key not found or toolkits not available, skipping specialized toolkits")
            
        except Exception as e:
            logger.error(f"Failed to initialize specialized toolkits: {e}")
            # Don't raise the error, continue without specialized toolkits
    
    async def _register_all_tools(self):
        """Register all tools from initialized toolkits."""
        for toolkit_name, toolkit in self.toolkits.items():
            try:
                # Get tools from toolkit
                tools = toolkit.get_tools()
                
                for tool in tools:
                    tool_name = f"{toolkit_name}_{tool.get_function_name()}"
                    self.available_tools[tool_name] = {
                        'toolkit': toolkit_name,
                        'tool': tool,
                        'function': tool.func,
                        'description': tool.get_function_description(),
                        'parameters': tool.parameters
                    }
                    
                    # Convert to OpenAI function format
                    self.tool_functions[tool_name] = tool
                
                logger.debug(f"Registered {len(tools)} tools from {toolkit_name} toolkit")
                
            except Exception as e:
                logger.error(f"Failed to register tools from {toolkit_name}: {e}")
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Optional execution context
            
        Returns:
            Tool execution result
        """
        try:
            logger.info(f"🔧 CAMEL Tool Manager: Executing tool '{tool_name}'")
            logger.info(f"   📝 Parameters: {json.dumps(parameters, indent=2)}")
            logger.info(f"   📋 Context: {context if context else 'None'}")
            
            if tool_name not in self.available_tools:
                error_msg = f"Tool '{tool_name}' not found in available tools"
                logger.error(f"   ❌ {error_msg}")
                logger.info(f"   📊 Available tools: {list(self.available_tools.keys())}")
                raise ValueError(error_msg)
            
            tool_info = self.available_tools[tool_name]
            tool_function = tool_info['function']
            
            logger.info(f"   ✅ Tool found: {tool_name}")
            logger.info(f"   🎯 Toolkit: {tool_info['toolkit']}")
            logger.info(f"   📄 Description: {tool_info.get('description', 'No description')}")
            
            # Update statistics
            self.execution_stats['total_calls'] += 1
            self._update_tool_stats(tool_name, 'calls')
            
            # Execute the tool
            start_time = datetime.now()
            logger.info(f"   🚀 Starting tool execution...")
            
            # Handle async tools
            if asyncio.iscoroutinefunction(tool_function):
                logger.info(f"   🔄 Executing async tool function...")
                result = await tool_function(**parameters)
                logger.info(f"   ✅ Async tool execution completed")
            else:
                logger.info(f"   🔄 Executing sync tool function...")
                result = tool_function(**parameters)
                logger.info(f"   ✅ Sync tool execution completed")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"   📊 Execution time: {execution_time:.2f}s")
            logger.info(f"   📄 Result: {str(result)[:200]}...")
            
            # Update success statistics
            self.execution_stats['successful_calls'] += 1
            self._update_tool_stats(tool_name, 'success')
            
            logger.info(f"   ✅ Tool execution successful")
            
            return {
                'success': True,
                'result': result,
                'tool_name': tool_name,
                'toolkit': tool_info['toolkit'],
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.execution_stats['failed_calls'] += 1
            self._update_tool_stats(tool_name, 'errors')
            
            logger.error(f"   ❌ Tool execution failed for {tool_name}: {e}")
            logger.error(f"   🔍 Error type: {type(e).__name__}")
            logger.error(f"   📋 Error details: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'tool_name': tool_name,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_available_tools(self, toolkit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available tools.
        
        Args:
            toolkit_name: Optional toolkit filter
            
        Returns:
            List of tool information
        """
        tools = []
        
        for tool_name, tool_info in self.available_tools.items():
            if toolkit_name and tool_info['toolkit'] != toolkit_name:
                continue
            
            tools.append({
                'name': tool_name,
                'toolkit': tool_info['toolkit'],
                'description': tool_info['description'],
                'parameters': tool_info['parameters'],
                'stats': self.execution_stats['by_tool'].get(tool_name, {})
            })
        
        return tools
    
    def get_tool_functions_for_agent(self, toolkit_names: Optional[List[str]] = None) -> List[Any]:
        """
        Get tool functions formatted for CAMEL AI agents.
        
        Args:
            toolkit_names: Optional list of toolkit names to filter
            
        Returns:
            List of function tools
        """
        functions = []
        
        for tool_name, tool_info in self.available_tools.items():
            if toolkit_names and tool_info['toolkit'] not in toolkit_names:
                continue
            
            functions.append(tool_info['tool'])
        
        return functions
    
    def get_toolkit_names(self) -> List[str]:
        """Get list of available toolkit names."""
        return list(self.toolkits.keys())
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools filtered by category."""
        category_mapping = {
            'code': ['code_execution'],
            'math': ['math'],
            'search': ['search', 'arxiv'],
            'communication': ['slack', 'twitter', 'linkedin'],
            'development': ['github'],
            'social': ['reddit', 'linkedin', 'twitter'],
            'creative': ['dalle'],
            'research': ['arxiv', 'retrieval'],
            'location': ['google_maps'],
            'weather': ['weather'],
        }
        
        toolkit_names = category_mapping.get(category, [])
        tools = []
        
        for toolkit_name in toolkit_names:
            tools.extend(self.get_available_tools(toolkit_name))
        
        return tools
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search tools by name or description."""
        query_lower = query.lower()
        matching_tools = []
        
        for tool_name, tool_info in self.available_tools.items():
            if (query_lower in tool_name.lower() or 
                query_lower in tool_info['description'].lower()):
                matching_tools.append({
                    'name': tool_name,
                    'toolkit': tool_info['toolkit'],
                    'description': tool_info['description'],
                    'parameters': tool_info['parameters']
                })
        
        return matching_tools
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        return {
            **self.execution_stats,
            'timestamp': datetime.now().isoformat(),
            'total_tools': len(self.available_tools),
            'active_toolkits': len(self.toolkits)
        }
    
    def _update_tool_stats(self, tool_name: str, stat_type: str):
        """Update tool execution statistics."""
        if tool_name not in self.execution_stats['by_tool']:
            self.execution_stats['by_tool'][tool_name] = {
                'calls': 0,
                'success': 0,
                'errors': 0
            }
        
        self.execution_stats['by_tool'][tool_name][stat_type] += 1
    
    async def shutdown(self):
        """Shutdown the tool manager."""
        try:
            # Clean up any resources
            for toolkit_name, toolkit in self.toolkits.items():
                if hasattr(toolkit, 'cleanup'):
                    await toolkit.cleanup()
            
            logger.info(f"CAMEL AI Tool Manager shutdown complete. "
                       f"Processed {self.execution_stats['total_calls']} tool calls.")
            
        except Exception as e:
            logger.error(f"Error during CAMEL AI Tool Manager shutdown: {e}")


class ToolEnabledAgent:
    """
    A wrapper for CAMEL AI ChatAgent with tool support.
    
    This class extends the basic ChatAgent to include tool calling capabilities
    using CAMEL AI's native toolkit system.
    """
    
    def __init__(
        self,
        system_message: str,
        model,
        tool_manager: CamelToolManager,
        enabled_toolkits: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize tool-enabled agent.
        
        Args:
            system_message: System message defining the agent's role
            model: CAMEL AI model instance
            tool_manager: Tool manager instance
            enabled_toolkits: List of toolkit names to enable
            **kwargs: Additional arguments for ChatAgent
        """
        self.tool_manager = tool_manager
        self.enabled_toolkits = enabled_toolkits or ['code_execution', 'math', 'search', 'weather']
        
        # Get tools for this agent
        self.tools = self.tool_manager.get_tool_functions_for_agent(self.enabled_toolkits)
        
        # Initialize the CAMEL AI agent with tools
        self.agent = ChatAgent(
            system_message=system_message,
            model=model,
            tools=self.tools,
            **kwargs
        )
        
        logger.info(f"Tool-enabled agent initialized with {len(self.tools)} tools")
    
    async def step(self, message: Union[str, BaseMessage]) -> BaseMessage:
        """
        Process a message and handle tool calls.
        
        Args:
            message: Input message
            
        Returns:
            Agent response
        """
        try:
            logger.info(f"🤖 Tool-Enabled Agent: Processing message")
            
            # Convert string to BaseMessage if needed
            if isinstance(message, str):
                logger.info(f"   📝 Converting string message to BaseMessage")
                message = BaseMessage.make_user_message(
                    role_name="User",
                    content=message
                )
            
            logger.info(f"   📄 Message content: {message.content[:100]}...")
            logger.info(f"   🎯 Message role: {message.role_name}")
            
            # Get response from agent with timeout and error handling
            try:
                logger.info(f"   🚀 Sending message to CAMEL AI agent...")
                logger.info(f"   🔧 Available tools: {len(self.tools)}")
                
                # Log available tools for debugging
                for i, tool in enumerate(self.tools[:5]):  # Log first 5 tools
                    logger.debug(f"   🔧 Tool {i+1}: {tool.get_function_name()}")
                if len(self.tools) > 5:
                    logger.debug(f"   🔧 ... and {len(self.tools) - 5} more tools")
                
                response = self.agent.step(message)
                
                logger.info(f"   ✅ Agent response received")
                
                # Check if response contains tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"   🛠️  Tool calls detected in response:")
                    for i, tool_call in enumerate(response.tool_calls):
                        logger.info(f"      📋 Tool call {i+1}: {tool_call.get('name', 'unknown')}")
                        logger.info(f"      📝 Arguments: {tool_call.get('arguments', {})}")
                else:
                    logger.info(f"   💬 Response contains no tool calls (text response only)")
                
                # Extract the actual message from the response
                if hasattr(response, 'msg'):
                    final_response = response.msg
                    logger.info(f"   📄 Final response extracted from response.msg")
                else:
                    final_response = response
                    logger.info(f"   📄 Using response directly")
                
                logger.info(f"   ✅ Message processing completed successfully")
                return final_response
                
            except Exception as e:
                # Only catch actual agent/tool errors, not HTTP/network errors from model loading
                error_msg = str(e).lower()
                
                logger.error(f"   ❌ Error during agent step: {e}")
                logger.error(f"   🔍 Error type: {type(e).__name__}")
                
                # Don't catch legitimate HTTP requests (model loading, etc.)
                if any(pattern in error_msg for pattern in [
                    'huggingface.co',
                    'model loading',
                    'downloading',
                    'adapter_config.json',
                    'additional_chat_templates'
                ]):
                    logger.info(f"   ℹ️  Legitimate model loading operation detected, re-raising error")
                    # Re-raise these as they're legitimate model loading operations
                    raise e
                
                # Only catch actual tool execution errors
                if any(pattern in error_msg for pattern in [
                    'tool execution failed',
                    'api key',
                    'unauthorized',
                    'rate limit',
                    'service unavailable'
                ]):
                    logger.warning(f"   ⚠️  Tool execution error detected: {e}")
                    logger.info(f"   💬 Returning fallback response")
                    return BaseMessage.make_assistant_message(
                        role_name="Assistant",
                        content=f"I encountered an issue with the tools: {str(e)[:100]}... Let me try to help you in another way."
                    )
                
                # Re-raise other errors
                logger.error(f"   ❌ Unhandled error, re-raising: {e}")
                raise e
            
        except Exception as e:
            logger.error(f"❌ Error in tool-enabled agent step: {e}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            logger.error(f"📋 Error details: {str(e)}")
            
            return BaseMessage.make_assistant_message(
                role_name="Assistant",
                content=f"I apologize, but I encountered an error: {str(e)[:100]}... Please try asking your question differently."
            )
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for this agent."""
        return self.tool_manager.get_available_tools()
    
    def add_toolkit(self, toolkit_name: str):
        """Add a toolkit to this agent."""
        if toolkit_name not in self.enabled_toolkits:
            self.enabled_toolkits.append(toolkit_name)
            self.tools = self.tool_manager.get_tool_functions_for_agent(self.enabled_toolkits)
            self.agent.tools = self.tools
            logger.info(f"Added toolkit '{toolkit_name}' to agent")
    
    def remove_toolkit(self, toolkit_name: str):
        """Remove a toolkit from this agent."""
        if toolkit_name in self.enabled_toolkits:
            self.enabled_toolkits.remove(toolkit_name)
            self.tools = self.tool_manager.get_tool_functions_for_agent(self.enabled_toolkits)
            self.agent.tools = self.tools
            logger.info(f"Removed toolkit '{toolkit_name}' from agent")
