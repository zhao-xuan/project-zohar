"""
Tool Manager for Project Zohar.

This module provides unified tool management, including
built-in tools, MCP servers, and custom tool registration.
"""

import asyncio
import json
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from zohar.config.settings import get_settings
from zohar.utils.logging import get_logger
from zohar.services.mcp_services.mcp_manager import MCPManager, MCPTool

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Tool categories."""
    SYSTEM = "system"
    EMAIL = "email"
    BROWSER = "browser"
    FILE = "file"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    DATA = "data"
    CUSTOM = "custom"


class ToolType(Enum):
    """Tool types."""
    BUILTIN = "builtin"
    MCP = "mcp"
    PLUGIN = "plugin"
    EXTERNAL = "external"


@dataclass
class Tool:
    """Tool definition."""
    name: str
    description: str
    category: ToolCategory
    tool_type: ToolType
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    mcp_service_id: Optional[str] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Don't serialize the handler function
        data.pop("handler", None)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tool':
        """Create from dictionary."""
        data.pop("handler", None)  # Remove handler from data
        return cls(**data)


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}
        self.handlers: Dict[str, Callable] = {}
        self.categories: Dict[ToolCategory, List[str]] = {}
        
        # Initialize category lists
        for category in ToolCategory:
            self.categories[category] = []
    
    def register_tool(
        self,
        tool: Tool,
        handler: Optional[Callable] = None
    ):
        """
        Register a tool.
        
        Args:
            tool: Tool definition
            handler: Tool handler function
        """
        self.tools[tool.name] = tool
        
        if handler:
            self.handlers[tool.name] = handler
        
        # Add to category
        if tool.category not in self.categories:
            self.categories[tool.category] = []
        
        if tool.name not in self.categories[tool.category]:
            self.categories[tool.category].append(tool.name)
        
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool."""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            
            # Remove from category
            if tool.category in self.categories:
                if tool_name in self.categories[tool.category]:
                    self.categories[tool.category].remove(tool_name)
            
            # Remove from registry
            del self.tools[tool_name]
            
            if tool_name in self.handlers:
                del self.handlers[tool_name]
            
            logger.debug(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(tool_name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get all tools in a category."""
        tool_names = self.categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def list_tools(self, enabled_only: bool = True) -> List[Tool]:
        """List all tools."""
        tools = list(self.tools.values())
        
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]
        
        return tools
    
    def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name or description."""
        query = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query in tool.name.lower() or 
                query in tool.description.lower()):
                results.append(tool)
        
        return results


class ToolManager:
    """
    Unified tool manager for Project Zohar.
    
    This class provides:
    - Built-in tool management
    - MCP server integration
    - Custom tool registration
    - Tool execution and monitoring
    """
    
    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """
        Initialize tool manager.
        
        Args:
            mcp_manager: MCP manager instance
        """
        self.settings = get_settings()
        self.registry = ToolRegistry()
        self.mcp_manager = mcp_manager
        
        # Execution tracking
        self.execution_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "by_tool": {},
            "by_category": {}
        }
        
        logger.info("Tool manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the tool manager.
        
        Returns:
            Success status
        """
        try:
            # Register built-in tools
            await self._register_builtin_tools()
            
            # Load MCP tools if manager is available
            if self.mcp_manager:
                await self._load_mcp_tools()
            
            # Load custom tools
            await self._load_custom_tools()
            
            logger.info(f"Tool manager initialized with {len(self.registry.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize tool manager: {e}")
            return False
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            context: Execution context
            
        Returns:
            Tool execution result
        """
        try:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            
            if not tool.enabled:
                raise ValueError(f"Tool {tool_name} is disabled")
            
            # Update stats
            self.execution_stats["total_calls"] += 1
            self._update_tool_stats(tool_name, "calls")
            
            # Execute based on tool type
            if tool.tool_type == ToolType.BUILTIN:
                result = await self._execute_builtin_tool(tool, parameters, context)
            elif tool.tool_type == ToolType.MCP:
                result = await self._execute_mcp_tool(tool, parameters, context)
            elif tool.tool_type == ToolType.PLUGIN:
                result = await self._execute_plugin_tool(tool, parameters, context)
            else:
                raise ValueError(f"Unsupported tool type: {tool.tool_type}")
            
            # Update success stats
            self.execution_stats["successful_calls"] += 1
            self._update_tool_stats(tool_name, "success")
            
            return {
                "success": True,
                "result": result,
                "tool_name": tool_name,
                "tool_type": tool.tool_type.value,
                "execution_time": None,  # Would be calculated in actual implementation
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.execution_stats["failed_calls"] += 1
            self._update_tool_stats(tool_name, "errors")
            
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_available_tools(
        self,
        category: Optional[ToolCategory] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List available tools.
        
        Args:
            category: Filter by category
            enabled_only: Show only enabled tools
            
        Returns:
            List of tool information
        """
        if category:
            tools = self.registry.get_tools_by_category(category)
        else:
            tools = self.registry.list_tools(enabled_only)
        
        return [tool.to_dict() for tool in tools]
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed tool information.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool information or None if not found
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return None
        
        info = tool.to_dict()
        
        # Add execution statistics
        tool_stats = self.execution_stats["by_tool"].get(tool_name, {})
        info["statistics"] = {
            "total_calls": tool_stats.get("calls", 0),
            "successful_calls": tool_stats.get("success", 0),
            "failed_calls": tool_stats.get("errors", 0),
            "success_rate": (
                tool_stats.get("success", 0) / max(tool_stats.get("calls", 1), 1) * 100
            )
        }
        
        return info
    
    async def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tools.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tools
        """
        tools = self.registry.search_tools(query)
        return [tool.to_dict() for tool in tools]
    
    async def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool."""
        tool = self.registry.get_tool(tool_name)
        if tool:
            tool.enabled = True
            logger.info(f"Enabled tool: {tool_name}")
            return True
        return False
    
    async def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool."""
        tool = self.registry.get_tool(tool_name)
        if tool:
            tool.enabled = False
            logger.info(f"Disabled tool: {tool_name}")
            return True
        return False
    
    async def register_custom_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: Dict[str, Any],
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a custom tool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            parameters: Tool parameters schema
            handler: Tool handler function
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            tool = Tool(
                name=name,
                description=description,
                category=category,
                tool_type=ToolType.PLUGIN,
                parameters=parameters,
                metadata=metadata
            )
            
            self.registry.register_tool(tool, handler)
            logger.info(f"Registered custom tool: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register custom tool {name}: {e}")
            return False
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        return {
            **self.execution_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Shutdown the tool manager."""
        try:
            logger.info(f"Tool manager shutting down. Processed {self.execution_stats['total_calls']} tool calls.")
            
        except Exception as e:
            logger.error(f"Error during tool manager shutdown: {e}")
    
    # Private methods
    
    async def _register_builtin_tools(self):
        """Register built-in tools."""
        try:
            # System tools
            self._register_system_tools()
            
            # File tools
            self._register_file_tools()
            
            # Communication tools
            self._register_communication_tools()
            
            # Data processing tools
            self._register_data_tools()
            
            logger.info("Built-in tools registered")
            
        except Exception as e:
            logger.error(f"Failed to register built-in tools: {e}")
    
    def _register_system_tools(self):
        """Register system tools."""
        # Get current time
        def get_current_time(**kwargs):
            return {"current_time": datetime.now().isoformat()}
        
        time_tool = Tool(
            name="get_current_time",
            description="Get the current date and time",
            category=ToolCategory.SYSTEM,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        self.registry.register_tool(time_tool, get_current_time)
        
        # System information
        def get_system_info(**kwargs):
            import platform
            return {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        
        system_tool = Tool(
            name="get_system_info",
            description="Get system information",
            category=ToolCategory.SYSTEM,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        self.registry.register_tool(system_tool, get_system_info)
    
    def _register_file_tools(self):
        """Register file operation tools."""
        # Read file
        async def read_file(file_path: str, **kwargs):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content, "file_path": file_path}
            except Exception as e:
                raise RuntimeError(f"Failed to read file: {e}")
        
        read_tool = Tool(
            name="read_file",
            description="Read content from a file",
            category=ToolCategory.FILE,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        )
        
        self.registry.register_tool(read_tool, read_file)
        
        # List directory
        async def list_directory(directory_path: str, **kwargs):
            try:
                from pathlib import Path
                path = Path(directory_path)
                
                if not path.exists():
                    raise RuntimeError(f"Directory does not exist: {directory_path}")
                
                if not path.is_dir():
                    raise RuntimeError(f"Path is not a directory: {directory_path}")
                
                items = []
                for item in path.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                
                return {"items": items, "directory_path": directory_path}
                
            except Exception as e:
                raise RuntimeError(f"Failed to list directory: {e}")
        
        list_tool = Tool(
            name="list_directory",
            description="List contents of a directory",
            category=ToolCategory.FILE,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    }
                },
                "required": ["directory_path"]
            }
        )
        
        self.registry.register_tool(list_tool, list_directory)
    
    def _register_communication_tools(self):
        """Register communication tools."""
        # Send notification (placeholder)
        async def send_notification(message: str, title: str = "Notification", **kwargs):
            # This would integrate with actual notification systems
            logger.info(f"Notification: {title} - {message}")
            return {"sent": True, "message": message, "title": title}
        
        notification_tool = Tool(
            name="send_notification",
            description="Send a notification message",
            category=ToolCategory.COMMUNICATION,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Notification message"
                    },
                    "title": {
                        "type": "string",
                        "description": "Notification title",
                        "default": "Notification"
                    }
                },
                "required": ["message"]
            }
        )
        
        self.registry.register_tool(notification_tool, send_notification)
    
    def _register_data_tools(self):
        """Register data processing tools."""
        # Calculate
        async def calculate(expression: str, **kwargs):
            try:
                # Simple calculator - in production, use safer evaluation
                import ast
                import operator
                
                # Safe evaluation for basic math
                allowed_ops = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.USub: operator.neg,
                }
                
                def safe_eval(node):
                    if isinstance(node, ast.Constant):
                        return node.value
                    elif isinstance(node, ast.BinOp):
                        left = safe_eval(node.left)
                        right = safe_eval(node.right)
                        op = allowed_ops.get(type(node.op))
                        if op:
                            return op(left, right)
                        else:
                            raise ValueError(f"Unsupported operation: {type(node.op)}")
                    elif isinstance(node, ast.UnaryOp):
                        operand = safe_eval(node.operand)
                        op = allowed_ops.get(type(node.op))
                        if op:
                            return op(operand)
                        else:
                            raise ValueError(f"Unsupported operation: {type(node.op)}")
                    else:
                        raise ValueError(f"Unsupported node type: {type(node)}")
                
                tree = ast.parse(expression, mode='eval')
                result = safe_eval(tree.body)
                
                return {"result": result, "expression": expression}
                
            except Exception as e:
                raise RuntimeError(f"Calculation failed: {e}")
        
        calc_tool = Tool(
            name="calculate",
            description="Perform mathematical calculations",
            category=ToolCategory.DATA,
            tool_type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        )
        
        self.registry.register_tool(calc_tool, calculate)
    
    async def _load_mcp_tools(self):
        """Load tools from MCP manager."""
        try:
            if not self.mcp_manager:
                return
            
            # Get all MCP tools
            mcp_tools = await self.mcp_manager.list_tools()
            
            for mcp_tool in mcp_tools:
                # Convert MCP tool to our Tool format
                tool = Tool(
                    name=mcp_tool.name,
                    description=mcp_tool.description,
                    category=ToolCategory.CUSTOM,  # Could be smarter about categorization
                    tool_type=ToolType.MCP,
                    parameters=mcp_tool.parameters,
                    mcp_service_id=mcp_tool.service_id,
                    metadata=mcp_tool.metadata
                )
                
                self.registry.register_tool(tool)
            
            logger.info(f"Loaded {len(mcp_tools)} MCP tools")
            
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
    
    async def _load_custom_tools(self):
        """Load custom tools from plugins."""
        # This would load tools from plugin directories
        # For now, it's a placeholder
        logger.debug("Custom tool loading not implemented yet")
    
    async def _execute_builtin_tool(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute a built-in tool."""
        handler = self.registry.handlers.get(tool.name)
        if not handler:
            raise RuntimeError(f"No handler found for tool {tool.name}")
        
        # Add context to parameters if provided
        if context:
            parameters = {**parameters, "context": context}
        
        # Execute handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            return handler(**parameters)
    
    async def _execute_mcp_tool(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute an MCP tool."""
        if not self.mcp_manager:
            raise RuntimeError("MCP manager not available")
        
        return await self.mcp_manager.call_tool(tool.name, parameters)
    
    async def _execute_plugin_tool(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute a plugin tool."""
        handler = self.registry.handlers.get(tool.name)
        if not handler:
            raise RuntimeError(f"No handler found for plugin tool {tool.name}")
        
        # Add context to parameters if provided
        if context:
            parameters = {**parameters, "context": context}
        
        # Execute handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            return handler(**parameters)
    
    def _update_tool_stats(self, tool_name: str, stat_type: str):
        """Update tool execution statistics."""
        if tool_name not in self.execution_stats["by_tool"]:
            self.execution_stats["by_tool"][tool_name] = {}
        
        current = self.execution_stats["by_tool"][tool_name].get(stat_type, 0)
        self.execution_stats["by_tool"][tool_name][stat_type] = current + 1
        
        # Update category stats
        tool = self.registry.get_tool(tool_name)
        if tool:
            category = tool.category.value
            if category not in self.execution_stats["by_category"]:
                self.execution_stats["by_category"][category] = {}
            
            current = self.execution_stats["by_category"][category].get(stat_type, 0)
            self.execution_stats["by_category"][category][stat_type] = current + 1 