"""
MCP (Model Context Protocol) Client for tool integration
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx

from src.config.settings import settings


class MCPClient:
    """
    Client for communicating with MCP servers and tools
    """
    
    def __init__(self):
        self.timeout = settings.mcp.mcp_timeout
        self.available_tools = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Discover available MCP tools and their capabilities"""
        # TODO: Implement actual tool discovery
        # This would connect to MCP servers and get their capabilities
        
        # Placeholder tool definitions
        self.available_tools = {
            "email": {
                "server_url": f"http://localhost:{settings.mcp.email_mcp_port}",
                "capabilities": [
                    "send_email",
                    "read_emails", 
                    "search_emails",
                    "mark_as_read",
                    "delete_email"
                ]
            },
            "browser": {
                "server_url": f"http://localhost:{settings.mcp.browser_mcp_port}",
                "capabilities": [
                    "browse_url",
                    "search_web",
                    "extract_content",
                    "take_screenshot"
                ]
            },
            "system": {
                "server_url": f"http://localhost:{settings.mcp.system_mcp_port}",
                "capabilities": [
                    "execute_command",
                    "list_files",
                    "read_file",
                    "write_file"
                ]
            }
        }
    
    async def call_tool(
        self, 
        tool_category: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Call a specific tool via MCP
        
        Args:
            tool_category: Category of tool (email, browser, system)
            tool_name: Specific tool to call
            parameters: Parameters for the tool
            
        Returns:
            Tool execution result
        """
        try:
            if tool_category not in self.available_tools:
                return f"Error: Tool category '{tool_category}' not available"
            
            tool_config = self.available_tools[tool_category]
            if tool_name not in tool_config["capabilities"]:
                return f"Error: Tool '{tool_name}' not available in category '{tool_category}'"
            
            # Make MCP call
            result = await self._make_mcp_call(
                tool_config["server_url"],
                tool_name,
                parameters
            )
            
            return result
            
        except Exception as e:
            return f"Error calling tool {tool_category}.{tool_name}: {str(e)}"
    
    async def _make_mcp_call(
        self, 
        server_url: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Make the actual HTTP call to MCP server
        
        Args:
            server_url: URL of the MCP server
            tool_name: Name of the tool to call
            parameters: Tool parameters
            
        Returns:
            Server response
        """
        # TODO: Implement actual MCP protocol calls
        # This is a simplified HTTP-based placeholder
        
        payload = {
            "tool": tool_name,
            "parameters": parameters
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{server_url}/execute",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("result", "Tool executed successfully")
                else:
                    return f"MCP server error: {response.status_code} - {response.text}"
                    
        except httpx.ConnectError:
            return f"Could not connect to MCP server at {server_url}"
        except httpx.TimeoutException:
            return f"MCP server timeout after {self.timeout} seconds"
        except Exception as e:
            return f"MCP call failed: {str(e)}"
    
    async def list_available_tools(self) -> Dict[str, List[str]]:
        """
        List all available tools by category
        
        Returns:
            Dictionary of tool categories and their available tools
        """
        tools = {}
        for category, config in self.available_tools.items():
            tools[category] = config["capabilities"]
        return tools
    
    async def check_tool_availability(self, tool_category: str) -> bool:
        """
        Check if a tool category is available
        
        Args:
            tool_category: Category to check
            
        Returns:
            True if available, False otherwise
        """
        if tool_category not in self.available_tools:
            return False
        
        # Try to ping the server
        try:
            server_url = self.available_tools[tool_category]["server_url"]
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{server_url}/health")
                return response.status_code == 200
        except:
            return False
    
    # Convenience methods for common tools
    
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str,
        cc: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> str:
        """Send an email via email tool"""
        parameters = {
            "to": to,
            "subject": subject,
            "body": body
        }
        
        if cc:
            parameters["cc"] = cc
        if attachments:
            parameters["attachments"] = attachments
        
        return await self.call_tool("email", "send_email", parameters)
    
    async def search_emails(self, query: str, limit: int = 10) -> str:
        """Search emails via email tool"""
        parameters = {
            "query": query,
            "limit": limit
        }
        return await self.call_tool("email", "search_emails", parameters)
    
    async def browse_url(self, url: str, extract_content: bool = True) -> str:
        """Browse a URL via browser tool"""
        parameters = {
            "url": url,
            "extract_content": extract_content
        }
        return await self.call_tool("browser", "browse_url", parameters)
    
    async def search_web(self, query: str, num_results: int = 5) -> str:
        """Search the web via browser tool"""
        parameters = {
            "query": query,
            "num_results": num_results
        }
        return await self.call_tool("browser", "search_web", parameters)
    
    async def execute_command(self, command: str, working_dir: Optional[str] = None) -> str:
        """Execute a system command via system tool"""
        parameters = {
            "command": command
        }
        
        if working_dir:
            parameters["working_dir"] = working_dir
        
        return await self.call_tool("system", "execute_command", parameters)
    
    async def list_files(self, directory: str = ".", pattern: Optional[str] = None) -> str:
        """List files via system tool"""
        parameters = {
            "directory": directory
        }
        
        if pattern:
            parameters["pattern"] = pattern
        
        return await self.call_tool("system", "list_files", parameters)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all MCP servers"""
        health_status = {}
        
        for category in self.available_tools:
            health_status[category] = await self.check_tool_availability(category)
        
        return health_status 