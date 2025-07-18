"""
MCP Service Manager for Project Zohar.

This module provides Model Context Protocol (MCP) service management,
including client connections, tool registration, and service orchestration.
"""

import asyncio
import json
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    websockets = None

from config.settings import get_settings
from ..agent.logging import get_logger

logger = get_logger(__name__)


class MCPConnectionType(Enum):
    """MCP connection types."""
    WEBSOCKET = "websocket"
    HTTP = "http"
    STDIO = "stdio"
    SUBPROCESS = "subprocess"


class MCPServiceStatus(Enum):
    """MCP service status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class MCPService:
    """MCP service configuration."""
    id: str
    name: str
    description: str
    connection_type: MCPConnectionType
    endpoint: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    auto_start: bool = True
    restart_on_failure: bool = True
    max_retries: int = 3
    timeout: int = 30
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPService':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]
    service_id: str
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MCPClient:
    """MCP client for communicating with MCP servers."""
    
    def __init__(self, service: MCPService):
        """
        Initialize MCP client.
        
        Args:
            service: MCP service configuration
        """
        self.service = service
        self.connection = None
        self.process = None
        self.status = MCPServiceStatus.STOPPED
        self.last_error = None
        self.tools = {}
        self.retry_count = 0
        
        logger.info(f"MCP client initialized for service: {service.name}")
    
    async def connect(self) -> bool:
        """
        Connect to MCP service.
        
        Returns:
            Success status
        """
        try:
            self.status = MCPServiceStatus.STARTING
            
            if self.service.connection_type == MCPConnectionType.WEBSOCKET:
                await self._connect_websocket()
            elif self.service.connection_type == MCPConnectionType.HTTP:
                await self._connect_http()
            elif self.service.connection_type == MCPConnectionType.STDIO:
                await self._connect_stdio()
            elif self.service.connection_type == MCPConnectionType.SUBPROCESS:
                await self._connect_subprocess()
            else:
                raise ValueError(f"Unsupported connection type: {self.service.connection_type}")
            
            # Initialize the connection
            await self._initialize_connection()
            
            self.status = MCPServiceStatus.RUNNING
            self.retry_count = 0
            
            logger.info(f"Successfully connected to MCP service: {self.service.name}")
            return True
            
        except Exception as e:
            self.status = MCPServiceStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Failed to connect to MCP service {self.service.name}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP service."""
        try:
            self.status = MCPServiceStatus.STOPPING
            
            if self.connection:
                if hasattr(self.connection, 'close'):
                    await self.connection.close()
                self.connection = None
            
            if self.process:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.process.kill()
                self.process = None
            
            self.status = MCPServiceStatus.STOPPED
            logger.info(f"Disconnected from MCP service: {self.service.name}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP service {self.service.name}: {e}")
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call a tool via MCP.
        
        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters
            timeout: Request timeout
            
        Returns:
            Tool result
        """
        try:
            if self.status != MCPServiceStatus.RUNNING:
                raise RuntimeError(f"Service {self.service.name} is not running")
            
            if tool_name not in self.tools:
                raise ValueError(f"Tool {tool_name} not found in service {self.service.name}")
            
            # Prepare request
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            # Send request
            response = await self._send_request(request, timeout)
            
            if "error" in response:
                raise RuntimeError(f"Tool error: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on service {self.service.name}: {e}")
            raise
    
    async def list_tools(self) -> List[MCPTool]:
        """
        List available tools.
        
        Returns:
            List of available tools
        """
        try:
            if self.status != MCPServiceStatus.RUNNING:
                raise RuntimeError(f"Service {self.service.name} is not running")
            
            # Prepare request
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list"
            }
            
            # Send request
            response = await self._send_request(request)
            
            if "error" in response:
                raise RuntimeError(f"List tools error: {response['error']}")
            
            tools = response.get("result", {}).get("tools", [])
            
            # Convert to MCPTool objects
            mcp_tools = []
            for tool_data in tools:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("inputSchema", {}),
                    service_id=self.service.id
                )
                mcp_tools.append(tool)
                self.tools[tool.name] = tool
            
            return mcp_tools
            
        except Exception as e:
            logger.error(f"Failed to list tools for service {self.service.name}: {e}")
            return []
    
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information.
        
        Returns:
            Service information
        """
        try:
            if self.status != MCPServiceStatus.RUNNING:
                return {
                    "service_id": self.service.id,
                    "name": self.service.name,
                    "status": self.status.value,
                    "error": self.last_error
                }
            
            # Prepare request
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "zohar",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send request
            response = await self._send_request(request)
            
            if "error" in response:
                raise RuntimeError(f"Initialize error: {response['error']}")
            
            result = response.get("result", {})
            
            return {
                "service_id": self.service.id,
                "name": self.service.name,
                "status": self.status.value,
                "protocol_version": result.get("protocolVersion", "unknown"),
                "capabilities": result.get("capabilities", {}),
                "server_info": result.get("serverInfo", {}),
                "tools_count": len(self.tools)
            }
            
        except Exception as e:
            logger.error(f"Failed to get service info for {self.service.name}: {e}")
            return {
                "service_id": self.service.id,
                "name": self.service.name,
                "status": self.status.value,
                "error": str(e)
            }
    
    # Private methods
    
    async def _connect_websocket(self):
        """Connect via WebSocket."""
        if not websockets:
            raise ImportError("websockets library is required for WebSocket connections")
        
        self.connection = await websockets.connect(
            self.service.endpoint,
            timeout=self.service.timeout
        )
    
    async def _connect_http(self):
        """Connect via HTTP."""
        # For HTTP, we'll use aiohttp in the actual implementation
        # For now, store endpoint for later use
        self.connection = {"endpoint": self.service.endpoint, "type": "http"}
    
    async def _connect_stdio(self):
        """Connect via STDIO."""
        if not self.service.command:
            raise ValueError("Command is required for STDIO connection")
        
        # Start process
        self.process = await asyncio.create_subprocess_exec(
            self.service.command,
            *self.service.args or [],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.service.env
        )
        
        self.connection = {"stdin": self.process.stdin, "stdout": self.process.stdout}
    
    async def _connect_subprocess(self):
        """Connect via subprocess."""
        await self._connect_stdio()  # Same as STDIO for now
    
    async def _initialize_connection(self):
        """Initialize the MCP connection."""
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "zohar",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise RuntimeError(f"Initialize error: {response['error']}")
        
        # Load available tools
        await self.list_tools()
    
    async def _send_request(
        self,
        request: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send request to MCP service."""
        if self.service.connection_type == MCPConnectionType.WEBSOCKET:
            return await self._send_websocket_request(request, timeout)
        elif self.service.connection_type == MCPConnectionType.HTTP:
            return await self._send_http_request(request, timeout)
        elif self.service.connection_type in [MCPConnectionType.STDIO, MCPConnectionType.SUBPROCESS]:
            return await self._send_stdio_request(request, timeout)
        else:
            raise ValueError(f"Unsupported connection type: {self.service.connection_type}")
    
    async def _send_websocket_request(
        self,
        request: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send WebSocket request."""
        try:
            await self.connection.send(json.dumps(request))
            
            # Wait for response
            response_data = await asyncio.wait_for(
                self.connection.recv(),
                timeout=timeout or self.service.timeout
            )
            
            return json.loads(response_data)
            
        except Exception as e:
            logger.error(f"WebSocket request failed: {e}")
            raise
    
    async def _send_http_request(
        self,
        request: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send HTTP request."""
        # Placeholder implementation
        # In practice, use aiohttp to send HTTP requests
        raise NotImplementedError("HTTP requests not implemented yet")
    
    async def _send_stdio_request(
        self,
        request: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send STDIO request."""
        try:
            # Send request
            request_data = json.dumps(request) + "\n"
            self.connection["stdin"].write(request_data.encode())
            await self.connection["stdin"].drain()
            
            # Read response
            response_data = await asyncio.wait_for(
                self.connection["stdout"].readline(),
                timeout=timeout or self.service.timeout
            )
            
            return json.loads(response_data.decode())
            
        except Exception as e:
            logger.error(f"STDIO request failed: {e}")
            raise


class MCPManager:
    """
    MCP service manager for handling multiple MCP services.
    
    This class provides:
    - Service registration and management
    - Connection pooling
    - Tool discovery and execution
    - Health monitoring
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize MCP manager.
        
        Args:
            config_path: Path to MCP configuration file
        """
        self.settings = get_settings()
        self.config_path = config_path or self.settings.config_dir / "mcp_services.json"
        
        # Service management
        self.services: Dict[str, MCPService] = {}
        self.clients: Dict[str, MCPClient] = {}
        self.tools: Dict[str, MCPTool] = {}
        
        # Health monitoring
        self.health_check_interval = 60  # seconds
        self.health_check_task = None
        
        # Statistics
        self.stats = {
            "services_registered": 0,
            "services_running": 0,
            "tools_available": 0,
            "requests_processed": 0,
            "errors": 0
        }
        
        logger.info("MCP manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the MCP manager.
        
        Returns:
            Success status
        """
        try:
            # Load service configurations
            await self._load_service_configs()
            
            # Start auto-start services
            await self._start_auto_start_services()
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("MCP manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP manager: {e}")
            return False
    
    async def register_service(self, service: MCPService) -> bool:
        """
        Register a new MCP service.
        
        Args:
            service: MCP service configuration
            
        Returns:
            Success status
        """
        try:
            self.services[service.id] = service
            self.stats["services_registered"] += 1
            
            # Create client
            client = MCPClient(service)
            self.clients[service.id] = client
            
            # Auto-start if configured
            if service.auto_start:
                await self.start_service(service.id)
            
            logger.info(f"Registered MCP service: {service.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register MCP service {service.name}: {e}")
            return False
    
    async def unregister_service(self, service_id: str) -> bool:
        """
        Unregister an MCP service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Success status
        """
        try:
            if service_id not in self.services:
                logger.warning(f"Service {service_id} not found")
                return False
            
            # Stop service if running
            await self.stop_service(service_id)
            
            # Remove from registry
            del self.services[service_id]
            del self.clients[service_id]
            
            # Remove tools
            tools_to_remove = [name for name, tool in self.tools.items() if tool.service_id == service_id]
            for tool_name in tools_to_remove:
                del self.tools[tool_name]
            
            logger.info(f"Unregistered MCP service: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister MCP service {service_id}: {e}")
            return False
    
    async def start_service(self, service_id: str) -> bool:
        """
        Start an MCP service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Success status
        """
        try:
            if service_id not in self.clients:
                logger.error(f"Service {service_id} not found")
                return False
            
            client = self.clients[service_id]
            
            if await client.connect():
                # Load tools
                tools = await client.list_tools()
                for tool in tools:
                    self.tools[tool.name] = tool
                
                self.stats["services_running"] += 1
                self.stats["tools_available"] += len(tools)
                
                logger.info(f"Started MCP service: {service_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MCP service {service_id}: {e}")
            return False
    
    async def stop_service(self, service_id: str) -> bool:
        """
        Stop an MCP service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Success status
        """
        try:
            if service_id not in self.clients:
                logger.error(f"Service {service_id} not found")
                return False
            
            client = self.clients[service_id]
            
            # Remove tools
            tools_to_remove = [name for name, tool in self.tools.items() if tool.service_id == service_id]
            for tool_name in tools_to_remove:
                del self.tools[tool_name]
            
            await client.disconnect()
            
            self.stats["services_running"] -= 1
            self.stats["tools_available"] -= len(tools_to_remove)
            
            logger.info(f"Stopped MCP service: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop MCP service {service_id}: {e}")
            return False
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call a tool via MCP.
        
        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters
            timeout: Request timeout
            
        Returns:
            Tool result
        """
        try:
            if tool_name not in self.tools:
                raise ValueError(f"Tool {tool_name} not found")
            
            tool = self.tools[tool_name]
            client = self.clients[tool.service_id]
            
            result = await client.call_tool(tool_name, parameters, timeout)
            
            self.stats["requests_processed"] += 1
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def list_tools(self, service_id: Optional[str] = None) -> List[MCPTool]:
        """
        List available tools.
        
        Args:
            service_id: Optional service ID to filter by
            
        Returns:
            List of available tools
        """
        if service_id:
            return [tool for tool in self.tools.values() if tool.service_id == service_id]
        else:
            return list(self.tools.values())
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get service status.
        
        Args:
            service_id: Optional service ID to get status for
            
        Returns:
            Service status information
        """
        if service_id:
            if service_id not in self.clients:
                return {"error": f"Service {service_id} not found"}
            
            client = self.clients[service_id]
            return await client.get_service_info()
        else:
            # Get status for all services
            status = {}
            for service_id, client in self.clients.items():
                status[service_id] = await client.get_service_info()
            return status
    
    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def restart_service(self, service_id: str) -> bool:
        """
        Restart an MCP service.
        
        Args:
            service_id: Service ID
            
        Returns:
            Success status
        """
        try:
            await self.stop_service(service_id)
            await asyncio.sleep(1)  # Brief pause
            return await self.start_service(service_id)
            
        except Exception as e:
            logger.error(f"Failed to restart MCP service {service_id}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the MCP manager."""
        try:
            # Stop health monitoring
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Stop all services
            for service_id in list(self.clients.keys()):
                await self.stop_service(service_id)
            
            logger.info("MCP manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during MCP manager shutdown: {e}")
    
    # Private methods
    
    async def _load_service_configs(self):
        """Load service configurations from file."""
        try:
            if not self.config_path.exists():
                # Create default configuration
                await self._create_default_config()
                return
            
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            for service_data in config_data.get("services", []):
                service = MCPService.from_dict(service_data)
                self.services[service.id] = service
                
                # Create client
                client = MCPClient(service)
                self.clients[service.id] = client
            
            logger.info(f"Loaded {len(self.services)} MCP service configurations")
            
        except Exception as e:
            logger.error(f"Failed to load service configurations: {e}")
    
    async def _create_default_config(self):
        """Create default MCP configuration."""
        default_config = {
            "version": "1.0.0",
            "services": [
                {
                    "id": "filesystem",
                    "name": "File System",
                    "description": "File system operations",
                    "connection_type": "subprocess",
                    "endpoint": "",
                    "command": "mcp-server-filesystem",
                    "args": [],
                    "auto_start": False  # Disable auto-start until subprocess is properly implemented
                },
                {
                    "id": "brave_search",
                    "name": "Brave Search",
                    "description": "Web search via Brave",
                    "connection_type": "subprocess",
                    "endpoint": "",
                    "command": "mcp-server-brave-search",
                    "args": [],
                    "auto_start": False  # Disable auto-start until subprocess is properly implemented
                }
            ]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info("Created default MCP configuration")
    
    async def _start_auto_start_services(self):
        """Start services configured for auto-start."""
        for service in self.services.values():
            if service.auto_start:
                await self.start_service(service.id)
    
    async def _health_check_loop(self):
        """Health check loop for monitoring services."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                for service_id, client in self.clients.items():
                    if client.status == MCPServiceStatus.RUNNING:
                        # Simple health check - try to list tools
                        try:
                            await client.list_tools()
                        except Exception as e:
                            logger.warning(f"Health check failed for service {service_id}: {e}")
                            
                            # Try to restart if configured
                            service = self.services[service_id]
                            if service.restart_on_failure and client.retry_count < service.max_retries:
                                client.retry_count += 1
                                logger.info(f"Restarting service {service_id} (retry {client.retry_count})")
                                await self.restart_service(service_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                "version": "1.0.0",
                "services": [service.to_dict() for service in self.services.values()]
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Saved MCP configuration")
            
        except Exception as e:
            logger.error(f"Failed to save MCP configuration: {e}")
    
    async def discover_services(self) -> List[Dict[str, Any]]:
        """
        Discover available MCP services.
        
        Returns:
            List of discovered services
        """
        discovered = []
        
        # Try to discover common MCP servers
        common_servers = [
            {
                "command": "mcp-server-filesystem",
                "name": "File System",
                "description": "File system operations"
            },
            {
                "command": "mcp-server-brave-search",
                "name": "Brave Search",
                "description": "Web search via Brave"
            },
            {
                "command": "mcp-server-git",
                "name": "Git",
                "description": "Git repository operations"
            },
            {
                "command": "mcp-server-sqlite",
                "name": "SQLite",
                "description": "SQLite database operations"
            }
        ]
        
        for server in common_servers:
            try:
                # Check if command exists
                result = subprocess.run(
                    ["which", server["command"]],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    discovered.append({
                        "id": server["command"].replace("mcp-server-", ""),
                        "name": server["name"],
                        "description": server["description"],
                        "command": server["command"],
                        "available": True
                    })
                else:
                    discovered.append({
                        "id": server["command"].replace("mcp-server-", ""),
                        "name": server["name"],
                        "description": server["description"],
                        "command": server["command"],
                        "available": False
                    })
                
            except Exception as e:
                logger.debug(f"Error checking server {server['command']}: {e}")
        
        return discovered

    async def start_default_servers(self) -> bool:
        """
        Start default MCP servers configured for auto-start.
        
        Returns:
            Success status
        """
        try:
            # Initialize if not already done
            if not hasattr(self, 'health_check_task') or self.health_check_task is None:
                await self.initialize()
            
            # Start all auto-start services
            started_count = 0
            for service in self.services.values():
                if service.auto_start:
                    if await self.start_service(service.id):
                        started_count += 1
            
            logger.info(f"Started {started_count} default MCP servers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start default servers: {e}")
            return False

    async def stop_all_servers(self) -> bool:
        """
        Stop all running MCP servers.
        
        Returns:
            Success status
        """
        try:
            stopped_count = 0
            for service_id in list(self.clients.keys()):
                if await self.stop_service(service_id):
                    stopped_count += 1
            
            logger.info(f"Stopped {stopped_count} MCP servers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop all servers: {e}")
            return False

    async def get_active_servers(self) -> List[str]:
        """
        Get list of active server IDs.
        
        Returns:
            List of active server IDs
        """
        active_servers = []
        
        for service_id, client in self.clients.items():
            if client.status.value == "running":
                active_servers.append(service_id)
        
        return active_servers
