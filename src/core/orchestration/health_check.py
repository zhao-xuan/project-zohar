"""
System Health Checker for Personal Chatbot System
"""
import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config.settings import settings
from src.tools.mcp_servers.client import ToolClient
from src.core.orchestration.bot_manager import BotManager

console = Console()


class SystemHealthChecker:
    """
    Checks the health of all system components
    """
    
    def __init__(self):
        self.tool_client = ToolClient()
        self.bot_manager = BotManager()
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check
        
        Returns:
            Health status of all components
        """
        console.print("📊 Running system health check...\n")
        
        health_results = {
            "overall_status": "healthy",
            "components": {}
        }
        
        # Check different components
        checks = [
            ("Configuration", self._check_configuration),
            ("Data Directories", self._check_data_directories),
            ("Tool Services", self._check_tool_services),
            ("Bot Agents", self._check_bot_agents),
            ("Dependencies", self._check_dependencies),
        ]
        
        for check_name, check_function in checks:
            console.print(f"🔍 Checking {check_name}...")
            try:
                result = await check_function()
                health_results["components"][check_name] = result
                
                if result["status"] != "healthy":
                    health_results["overall_status"] = "degraded"
                
            except Exception as e:
                health_results["components"][check_name] = {
                    "status": "error",
                    "message": str(e)
                }
                health_results["overall_status"] = "error"
        
        # Display results
        self._display_health_results(health_results)
        
        return health_results
    
    async def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration settings"""
        issues = []
        
        # Check critical settings
        if not settings.llm.model_name:
            issues.append("LLM model name not configured")
        
        if not settings.database.vector_db_path:
            issues.append("Vector database path not configured")
        
        # Check data paths exist
        from pathlib import Path
        if not Path(settings.personal_data_path).exists():
            issues.append(f"Personal data path does not exist: {settings.personal_data_path}")
        
        return {
            "status": "healthy" if not issues else "warning",
            "message": "Configuration OK" if not issues else f"Issues: {', '.join(issues)}",
            "details": {
                "model_name": settings.llm.model_name,
                "ollama_host": settings.llm.ollama_host,
                "vector_db_path": settings.database.vector_db_path
            }
        }
    
    async def _check_data_directories(self) -> Dict[str, Any]:
        """Check data directory structure"""
        from pathlib import Path
        
        required_dirs = [
            settings.personal_data_path,
            settings.public_data_path,
            settings.processed_data_path,
            Path(settings.database.vector_db_path).parent,
            Path(settings.log_file_path).parent,
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(str(dir_path))
        
        return {
            "status": "healthy" if not missing_dirs else "warning",
            "message": "All directories exist" if not missing_dirs else f"Missing: {', '.join(missing_dirs)}",
            "details": {
                "required_directories": len(required_dirs),
                "existing_directories": len(required_dirs) - len(missing_dirs)
            }
        }
    
    async def _check_tool_services(self) -> Dict[str, Any]:
        """Check tool services availability"""
        tool_health = await self.tool_client.health_check()
        
        healthy_tools = sum(1 for status in tool_health.values() if status)
        total_tools = len(tool_health)
        
        return {
            "status": "healthy" if healthy_tools == total_tools else "warning",
            "message": f"{healthy_tools}/{total_tools} tool services available",
            "details": tool_health
        }
    
    async def _check_bot_agents(self) -> Dict[str, Any]:
        """Check bot agent health"""
        try:
            bot_health = await self.bot_manager.health_check()
            
            return {
                "status": "healthy" if bot_health["overall_status"] == "healthy" else "warning",
                "message": f"Bot status: {bot_health['overall_status']}",
                "details": bot_health
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Bot check failed: {str(e)}",
                "details": {}
            }
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check critical dependencies"""
        missing_deps = []
        available_deps = []
        
        # Check critical imports
        deps_to_check = [
            ("camel", "CAMEL framework"),
            ("chromadb", "ChromaDB"),
            ("fastapi", "FastAPI"),
            ("rich", "Rich console"),
            ("httpx", "HTTPX client"),
        ]
        
        for module_name, friendly_name in deps_to_check:
            try:
                __import__(module_name)
                available_deps.append(friendly_name)
            except ImportError:
                missing_deps.append(friendly_name)
        
        # Check Ollama connectivity
        ollama_status = await self._check_ollama()
        
        return {
            "status": "healthy" if not missing_deps and ollama_status else "warning",
            "message": f"{len(available_deps)}/{len(deps_to_check)} dependencies available",
            "details": {
                "available": available_deps,
                "missing": missing_deps,
                "ollama_available": ollama_status
            }
        }
    
    async def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(settings.llm.ollama_host)
                return response.status_code == 200
        except:
            return False
    
    def _display_health_results(self, health_results: Dict[str, Any]):
        """Display health check results in a formatted table"""
        table = Table(title="System Health Check Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Message", style="white")
        
        for component, result in health_results["components"].items():
            status = result["status"]
            message = result["message"]
            
            # Add emoji for status
            if status == "healthy":
                status_display = "✅ Healthy"
            elif status == "warning":
                status_display = "⚠️  Warning"
            else:
                status_display = "❌ Error"
            
            table.add_row(component, status_display, message)
        
        console.print(table)
        
        # Overall status
        overall = health_results["overall_status"]
        if overall == "healthy":
            panel_style = "green"
            emoji = "✅"
        elif overall == "degraded":
            panel_style = "yellow"
            emoji = "⚠️"
        else:
            panel_style = "red"
            emoji = "❌"
        
        console.print(Panel(
            f"{emoji} Overall System Status: {overall.upper()}",
            title="Health Summary",
            border_style=panel_style
        )) 