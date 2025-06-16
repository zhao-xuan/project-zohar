#!/usr/bin/env python3
"""
Main entry point for the Personal Multi-Agent Chatbot System
"""
import asyncio
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel

from src.config.settings import settings
from src.ui.web.app import create_web_app
from src.ui.terminal.cli import run_terminal_interface
from src.core.orchestration.bot_manager import BotManager

console = Console()
app = typer.Typer(help="Personal Multi-Agent Chatbot System")


@app.command()
def web(
    bot_type: str = typer.Option(
        "both",
        "--type",
        "-t",
        help="Type of bot to run: 'personal', 'public', or 'both'"
    ),
    host: str = typer.Option(
        settings.web_ui.host,
        "--host",
        "-h",
        help="Host to bind the web server"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development"
    )
):
    """Run the web interface for the chatbot system"""
    console.print(Panel.fit(
        f"🤖 Starting {settings.app_name} v{settings.app_version}\n"
        f"Bot Type: {bot_type.upper()}\n"
        f"Host: {host}\n"
        f"Personal Bot: http://{host}:{settings.web_ui.personal_bot_port}\n"
        f"Public Bot: http://{host}:{settings.web_ui.public_bot_port}",
        title="Web Interface",
        border_style="blue"
    ))
    
    # Import here to avoid circular imports
    import uvicorn
    
    if bot_type in ["personal", "both"]:
        console.print(f"🔐 Starting Personal Bot on port {settings.web_ui.personal_bot_port}")
        # Run personal bot in background
        asyncio.create_task(
            uvicorn.run(
                "src.ui.web.app:create_personal_app",
                host=host,
                port=settings.web_ui.personal_bot_port,
                reload=reload,
                factory=True
            )
        )
    
    if bot_type in ["public", "both"] and settings.security.enable_public_bot:
        console.print(f"🌐 Starting Public Bot on port {settings.web_ui.public_bot_port}")
        uvicorn.run(
            "src.ui.web.app:create_public_app",
            host=host,
            port=settings.web_ui.public_bot_port,
            reload=reload,
            factory=True
        )
    elif bot_type in ["public", "both"]:
        console.print("⚠️  Public bot is disabled in configuration")


@app.command()
def terminal(
    bot_type: str = typer.Option(
        "personal",
        "--type",
        "-t",
        help="Type of bot to use: 'personal' or 'public'"
    )
):
    """Run the terminal interface for the chatbot system"""
    console.print(Panel.fit(
        f"💻 {settings.app_name} - Terminal Interface\n"
        f"Bot Type: {bot_type.upper()}\n"
        f"Type 'help' for commands, 'exit' to quit",
        title="Terminal Interface",
        border_style="green"
    ))
    
    if bot_type == "public" and not settings.security.enable_public_bot:
        console.print("⚠️  Public bot is disabled in configuration")
        return
    
    asyncio.run(run_terminal_interface(bot_type))


@app.command()
def setup():
    """Initial setup and configuration wizard"""
    console.print(Panel.fit(
        "🔧 Setting up Personal Multi-Agent Chatbot System",
        title="Setup Wizard",
        border_style="yellow"
    ))
    
    # Import setup module
    from scripts.setup_wizard import run_setup_wizard
    run_setup_wizard()


@app.command()
def index_data(
    source_path: str = typer.Option(
        None,
        "--source",
        "-s",
        help="Path to data source to index"
    ),
    data_type: str = typer.Option(
        "auto",
        "--type",
        "-t",
        help="Type of data: 'email', 'documents', 'auto'"
    ),
    force_reindex: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reindexing of existing data"
    )
):
    """Index personal data for RAG (Retrieval-Augmented Generation)"""
    console.print(Panel.fit(
        f"📚 Indexing data for RAG system\n"
        f"Source: {source_path or 'Default data directories'}\n"
        f"Type: {data_type}",
        title="Data Indexing",
        border_style="cyan"
    ))
    
    from src.rag.indexer import DataIndexer
    indexer = DataIndexer()
    
    asyncio.run(indexer.index_data(
        source_path=source_path,
        data_type=data_type,
        force_reindex=force_reindex
    ))


@app.command()
def start_mcp_servers():
    """Start all MCP (Model Context Protocol) servers"""
    console.print(Panel.fit(
        "🔗 Starting MCP Servers\n"
        f"Email Server: Port {settings.mcp.email_mcp_port}\n"
        f"Browser Server: Port {settings.mcp.browser_mcp_port}\n"
        f"System Server: Port {settings.mcp.system_mcp_port}",
        title="MCP Servers",
        border_style="magenta"
    ))
    
    from src.tools.mcp_servers.manager import MCPServerManager
    manager = MCPServerManager()
    
    asyncio.run(manager.start_all_servers())


@app.command()
def status():
    """Check system status and health"""
    console.print(Panel.fit(
        f"📊 System Status Check",
        title="Health Check",
        border_style="blue"
    ))
    
    from src.core.orchestration.health_check import SystemHealthChecker
    checker = SystemHealthChecker()
    
    asyncio.run(checker.run_health_check())


@app.command()
def version():
    """Show version information"""
    console.print(Panel.fit(
        f"{settings.app_name}\n"
        f"Version: {settings.app_version}\n"
        f"Debug Mode: {settings.debug}",
        title="Version Info",
        border_style="blue"
    ))


if __name__ == "__main__":
    app() 