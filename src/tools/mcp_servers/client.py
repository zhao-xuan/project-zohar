"""
Tool Client for external service integration (MCP-like protocol)
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx

from src.config.settings import settings
from src.services.ollama_service import ollama_service


class ToolClient:
    """
    Client for communicating with external tools and services
    Uses HTTP-based protocol similar to MCP (Model Context Protocol)
    """
    
    def __init__(self):
        self.timeout = settings.mcp.mcp_timeout
        self.available_tools = {}
        self._setup_tool_definitions()
    
    def _setup_tool_definitions(self):
        """Setup available tool definitions"""
        # Define available tools and their mock endpoints
        # In a real implementation, these would be actual MCP servers
        
        self.available_tools = {
            "email": {
                "server_url": f"http://localhost:{settings.mcp.email_mcp_port}",
                "capabilities": [
                    "send_email",
                    "read_emails", 
                    "search_emails",
                    "mark_as_read",
                    "delete_email"
                ],
                "mock_available": True  # For development without actual servers
            },
            "browser": {
                "server_url": f"http://localhost:{settings.mcp.browser_mcp_port}",
                "capabilities": [
                    "browse_url",
                    "search_web",
                    "extract_content",
                    "take_screenshot"
                ],
                "mock_available": True
            },
            "system": {
                "server_url": f"http://localhost:{settings.mcp.system_mcp_port}",
                "capabilities": [
                    "execute_command",
                    "list_files",
                    "read_file",
                    "write_file"
                ],
                "mock_available": True
            }
        }
    
    async def call_tool(
        self, 
        tool_category: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Call a specific tool via HTTP protocol
        
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
            
            # First try to make actual HTTP call to MCP servers
            result = await self._make_http_call(
                tool_config["server_url"],
                tool_name,
                parameters
            )
            
            return result
            
        except Exception as e:
            return f"Error calling tool {tool_category}.{tool_name}: {str(e)}"
    
    async def _get_ollama_response(
        self, 
        tool_category: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Generate tool response using local Ollama DeepSeek model
        
        Args:
            tool_category: Category of tool
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Ollama-generated response
        """
        try:
            # Check if Ollama is available
            if await ollama_service.is_available():
                return await ollama_service.generate_tool_response(
                    tool_category, tool_name, parameters
                )
            else:
                # Fall back to mock if Ollama is not available
                return await self._get_mock_response(tool_category, tool_name, parameters)
        except Exception as e:
            # Fall back to mock on any error
            return await self._get_mock_response(tool_category, tool_name, parameters)
    
    async def _get_mock_response(
        self, 
        tool_category: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Generate mock responses for development/testing
        
        Args:
            tool_category: Category of tool
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Mock response
        """
        if tool_category == "email":
            if tool_name == "send_email":
                to = parameters.get("to", "unknown@example.com")
                subject = parameters.get("subject", "No Subject")
                return f"Mock: Email sent to {to} with subject '{subject}'"
            elif tool_name == "search_emails":
                query = parameters.get("query", "")
                return f"Mock: Found 3 emails matching '{query}': Email 1, Email 2, Email 3"
            elif tool_name == "read_emails":
                return "Mock: Retrieved 5 recent emails from inbox"
        
        elif tool_category == "browser":
            if tool_name == "browse_url":
                url = parameters.get("url", "unknown-url")
                return f"Mock: Successfully browsed {url}. Content: Sample webpage content with relevant information."
            elif tool_name == "search_web":
                query = parameters.get("query", "")
                return f"Mock: Web search for '{query}' returned 5 results with relevant information"
        
        elif tool_category == "system":
            if tool_name == "execute_command":
                command = parameters.get("command", "")
                return f"Mock: Executed command '{command}'. Output: Command completed successfully."
            elif tool_name == "list_files":
                directory = parameters.get("directory", ".")
                return f"Mock: Listed files in {directory}: file1.txt, file2.py, folder1/"
        
        return f"Mock: {tool_category}.{tool_name} executed with parameters {parameters}"
    
    async def _make_http_call(
        self, 
        server_url: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Make HTTP call to actual tool server
        
        Args:
            server_url: URL of the tool server
            tool_name: Name of the tool to call
            parameters: Tool parameters
            
        Returns:
            Server response
        """
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
                    return f"Tool server error: {response.status_code} - {response.text}"
                    
        except httpx.ConnectError:
            # Fall back to Ollama if MCP server is not available
            return await self._get_ollama_response(
                self._get_category_from_url(server_url), 
                tool_name, 
                parameters
            )
        except httpx.TimeoutException:
            return f"Tool server timeout after {self.timeout} seconds"
        except Exception as e:
            return f"Tool call failed: {str(e)}"
    
    def _get_category_from_url(self, server_url: str) -> str:
        """Extract tool category from server URL"""
        if f":{settings.mcp.email_mcp_port}" in server_url:
            return "email"
        elif f":{settings.mcp.browser_mcp_port}" in server_url:
            return "browser"
        elif f":{settings.mcp.system_mcp_port}" in server_url:
            return "system"
        return "unknown"
    
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
        
        tool_config = self.available_tools[tool_category]
        
        # If mock is available, always return True
        if tool_config.get("mock_available", False):
            return True
        
        # Try to ping the actual server
        try:
            server_url = tool_config["server_url"]
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
        """Check health of all tool categories"""
        health_status = {}
        
        for category in self.available_tools:
            health_status[category] = await self.check_tool_availability(category)
        
        return health_status


# For backward compatibility
MCPClient = ToolClient 