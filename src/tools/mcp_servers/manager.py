"""
MCP Server Manager for coordinating tool servers
"""
import asyncio
from typing import Dict, List
from rich.console import Console

from src.config.settings import settings

console = Console()


class MCPServerManager:
    """
    Manages MCP (Model Context Protocol) servers for different tools
    """
    
    def __init__(self):
        self.servers = {
            "email": {
                "port": settings.mcp.email_mcp_port,
                "status": "stopped",
                "process": None
            },
            "browser": {
                "port": settings.mcp.browser_mcp_port,
                "status": "stopped", 
                "process": None
            },
            "system": {
                "port": settings.mcp.system_mcp_port,
                "status": "stopped",
                "process": None
            }
        }
    
    async def start_all_servers(self):
        """Start all MCP servers"""
        console.print("🔗 Starting MCP servers...")
        
        for server_name, config in self.servers.items():
            await self.start_server(server_name)
        
        console.print("✅ All MCP servers started!")
    
    async def start_server(self, server_name: str):
        """Start a specific MCP server"""
        if server_name not in self.servers:
            console.print(f"❌ Unknown server: {server_name}")
            return
        
        config = self.servers[server_name]
        port = config["port"]
        
        console.print(f"🚀 Starting {server_name} server on port {port}...")
        
        # TODO: Implement actual server starting
        # For now, just simulate starting
        await asyncio.sleep(1)
        
        config["status"] = "running"
        console.print(f"✅ {server_name.capitalize()} server started on port {port}")
    
    async def stop_all_servers(self):
        """Stop all MCP servers"""
        console.print("🛑 Stopping MCP servers...")
        
        for server_name in self.servers:
            await self.stop_server(server_name)
        
        console.print("✅ All MCP servers stopped!")
    
    async def stop_server(self, server_name: str):
        """Stop a specific MCP server"""
        if server_name not in self.servers:
            console.print(f"❌ Unknown server: {server_name}")
            return
        
        config = self.servers[server_name]
        
        if config["status"] == "stopped":
            console.print(f"ℹ️  {server_name.capitalize()} server is already stopped")
            return
        
        console.print(f"🛑 Stopping {server_name} server...")
        
        # TODO: Implement actual server stopping
        await asyncio.sleep(0.5)
        
        config["status"] = "stopped"
        config["process"] = None
        console.print(f"✅ {server_name.capitalize()} server stopped")
    
    async def get_server_status(self) -> Dict[str, str]:
        """Get status of all servers"""
        return {name: config["status"] for name, config in self.servers.items()}
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all servers"""
        health = {}
        
        for server_name, config in self.servers.items():
            # TODO: Implement actual health check by pinging server
            health[server_name] = config["status"] == "running"
        
        return health 