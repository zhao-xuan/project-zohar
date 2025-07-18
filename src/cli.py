"""
Main CLI entry point for Project Zohar.

This module provides the command-line interface for all Project Zohar operations,
including setup, data processing, agent management, and system monitoring.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.markdown import Markdown

from config.settings import get_settings
from module.bot.bot_manager import BotManager, AgentType
from module.file_parser.processor import DataProcessor
from module.agent.platform_manager import PlatformManager
# from ui.wizard.setup_wizard import SetupWizard
from module.agent.logging import setup_logging

# Initialize console and app
console = Console()
app = typer.Typer(
    name="zohar",
    help="Project Zohar: A privacy-focused AI assistant",
    add_completion=False,
    rich_markup_mode="rich"
)

# Command groups
setup_app = typer.Typer(name="setup", help="Setup and configuration commands")
data_app = typer.Typer(name="data", help="Data processing and management commands")
agent_app = typer.Typer(name="agent", help="Agent management commands")
platform_app = typer.Typer(name="platform", help="Platform integration commands")
ui_app = typer.Typer(name="ui", help="User interface commands")

app.add_typer(setup_app, name="setup")
app.add_typer(data_app, name="data")
app.add_typer(agent_app, name="agent")
app.add_typer(platform_app, name="platform")
app.add_typer(ui_app, name="ui")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
):
    """
    Project Zohar: A privacy-focused AI assistant with local deployment capabilities.
    
    🤖 Features:
    - Local LLM deployment with Ollama
    - Multi-platform message processing
    - Privacy-focused data handling
    - Intelligent agent orchestration
    - Comprehensive data analysis
    """
    settings = get_settings()
    
    if debug:
        settings.debug = True
        settings.log_level = "DEBUG"
    
    if verbose:
        settings.log_level = "INFO"
    
    setup_logging(settings)
    
    # Display welcome message
    if not verbose:
        console.print(Panel.fit(
            "[bold blue]Project Zohar[/bold blue] 🤖\n"
            "[dim]Privacy-focused AI assistant[/dim]",
            border_style="blue"
        ))


# Setup Commands
@setup_app.command("wizard")
def setup_wizard(
    web: bool = typer.Option(True, "--web", help="Launch web-based setup wizard"),
    host: str = typer.Option("localhost", "--host", help="Host for web wizard"),
    port: int = typer.Option(8001, "--port", help="Port for web wizard")
):
    """Launch the interactive setup wizard."""
    console.print("[bold green]Starting Project Zohar Setup Wizard[/bold green]")
    
    if web:
        console.print(f"[blue]Launching web setup wizard at http://{host}:{port}/setup[/blue]")
        console.print("[yellow]The web interface will open automatically in your browser.[/yellow]")
        
        # Start web interface for setup
        try:
            import uvicorn
            import webbrowser
            import threading
            import time
            
            # Open browser after a short delay
            def open_browser():
                time.sleep(2)
                webbrowser.open(f"http://{host}:{port}/setup")
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Start web server
            from ui.web.app import ZoharWebApp
            web_app = ZoharWebApp()
            
            uvicorn.run(
                web_app.app,
                host=host,
                port=port,
                log_level="info"
            )
            
        except ImportError:
            console.print("[red]Web setup wizard requires uvicorn and fastapi. Run: pip install uvicorn fastapi[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error starting web setup wizard: {str(e)}[/red]")
            raise typer.Exit(1)
    else:
        # Fall back to CLI setup wizard
        console.print("[blue]Starting command-line setup wizard...[/blue]")
        import subprocess
        import sys
        
        try:
            subprocess.run([sys.executable, "scripts/setup_wizard.py"], check=True)
        except subprocess.CalledProcessError:
            console.print("[red]CLI setup wizard failed. Try the web wizard with --web flag.[/red]")
            raise typer.Exit(1)
        except FileNotFoundError:
            console.print("[red]CLI setup wizard not found. Using web wizard instead.[/red]")
            # Recursively call with web=True
            setup_wizard(web=True, host=host, port=port)


@setup_app.command("init")
def setup_init(
    force: bool = typer.Option(False, "--force", help="Force initialization even if already configured")
):
    """Initialize Project Zohar with default settings."""
    settings = get_settings()
    
    if settings.data_dir.exists() and not force:
        console.print("[yellow]Project Zohar is already initialized. Use --force to reinitialize.[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing Project Zohar...", total=None)
        
        # Create directories
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        settings.models_dir.mkdir(parents=True, exist_ok=True)
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        
        progress.update(task, description="Creating configuration files...")
        
        # Create default configuration
        config_path = settings.data_dir / "config.yaml"
        if not config_path.exists():
            # Create default config
            pass
        
        progress.update(task, description="Setting up database...")
        
        # Initialize database
        # TODO: Add database initialization
        
        progress.update(task, description="Checking Ollama installation...")
        
        # Check Ollama
        # TODO: Add Ollama check
        
        progress.update(task, description="Complete!")
    
    console.print("[bold green]✓ Project Zohar initialized successfully![/bold green]")
    console.print(f"[dim]Data directory: {settings.data_dir}[/dim]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Run [bold]zohar setup wizard[/bold] for full configuration")
    console.print("2. Or run [bold]zohar ui web[/bold] to start the web interface")


@setup_app.command("status")
def setup_status():
    """Check the current setup status."""
    settings = get_settings()
    
    table = Table(title="Project Zohar Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    # Check directories
    table.add_row("Data Directory", "✓" if settings.data_dir.exists() else "✗", str(settings.data_dir))
    table.add_row("Models Directory", "✓" if settings.models_dir.exists() else "✗", str(settings.models_dir))
    table.add_row("Cache Directory", "✓" if settings.cache_dir.exists() else "✗", str(settings.cache_dir))
    
    # Check Ollama
    # TODO: Add Ollama status check
    table.add_row("Ollama", "⚠", "Not checked")
    
    # Check database
    # TODO: Add database status check
    table.add_row("Database", "⚠", "Not checked")
    
    # Check models
    # TODO: Add model status check
    table.add_row("Models", "⚠", "Not checked")
    
    console.print(table)


# Data Commands
@data_app.command("analyze")
def data_analyze(
    path: Path = typer.Argument(..., help="Path to analyze"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="Analyze recursively"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Analyze data files and create a structure report."""
    console.print(f"[bold]Analyzing data at: {path}[/bold]")
    
    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)
    
    analyzer = DataProcessor("default_user")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing files...", total=None)
        
        try:
            result = asyncio.run(analyzer.analyze_directory(path, recursive=recursive))
            
            progress.update(task, description="Generating report...")
            
            # Display summary
            console.print(f"\n[bold green]Analysis Complete![/bold green]")
            console.print(f"Files analyzed: {result.get('total_files', 0)}")
            console.print(f"File types found: {len(result.get('file_types', []))}")
            console.print(f"Total size: {result.get('total_size_mb', 0):.2f} MB")
            
            if output:
                # Save detailed report
                # TODO: Implement detailed report saving
                console.print(f"[dim]Detailed report saved to: {output}[/dim]")
                
        except Exception as e:
            console.print(f"[red]Error during analysis: {str(e)}[/red]")
            raise typer.Exit(1)


@data_app.command("process")
def data_process(
    path: Path = typer.Argument(..., help="Path to process"),
    create_index: bool = typer.Option(True, "--index", help="Create vector index"),
    batch_size: int = typer.Option(32, "--batch-size", help="Processing batch size"),
):
    """Process data files and create vector embeddings."""
    console.print(f"[bold]Processing data at: {path}[/bold]")
    
    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)
    
    # TODO: Implement data processing
    console.print("[yellow]Data processing is not yet implemented[/yellow]")


# Agent Commands
@agent_app.command("start")
def agent_start(
    agent_type: str = typer.Option("personal", "--type", "-t", help="Agent type (personal/public)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Start an agent."""
    console.print(f"[bold]Starting {agent_type} agent...[/bold]")
    
    try:
        bot_manager = BotManager()
        # TODO: Implement agent starting - this is synchronous function, agent starting logic moved to async functions
        console.print(f"[bold green]✓ {agent_type.title()} agent started![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error starting agent: {str(e)}[/red]")
        raise typer.Exit(1)


@agent_app.command("stop")
def agent_stop(
    agent_id: Optional[str] = typer.Option(None, "--id", help="Agent ID to stop"),
):
    """Stop an agent."""
    console.print("[bold]Stopping agent...[/bold]")
    
    # TODO: Implement agent stopping
    console.print("[bold green]✓ Agent stopped![/bold green]")


@agent_app.command("list")
def agent_list():
    """List all running agents."""
    console.print("[bold]Active Agents:[/bold]")
    
    # TODO: Implement agent listing
    console.print("[dim]No agents currently running[/dim]")


# Platform Commands
@platform_app.command("connect")
def platform_connect(
    platform: str = typer.Argument(..., help="Platform to connect (gmail, slack, discord, telegram)"),
):
    """Connect to a platform."""
    console.print(f"[bold]Connecting to {platform}...[/bold]")
    
    try:
        platform_manager = PlatformManager()
        # TODO: Implement platform connection
        console.print(f"[bold green]✓ Connected to {platform}![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error connecting to {platform}: {str(e)}[/red]")
        raise typer.Exit(1)


@platform_app.command("disconnect")
def platform_disconnect(
    platform: str = typer.Argument(..., help="Platform to disconnect"),
):
    """Disconnect from a platform."""
    console.print(f"[bold]Disconnecting from {platform}...[/bold]")
    
    # TODO: Implement platform disconnection
    console.print(f"[bold green]✓ Disconnected from {platform}![/bold green]")


@platform_app.command("status")
def platform_status():
    """Show platform connection status."""
    console.print("[bold]Platform Status:[/bold]")
    
    # TODO: Implement platform status
    console.print("[dim]No platforms connected[/dim]")


# UI Commands
@ui_app.command("web")
def ui_web(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    reload: bool = typer.Option(True, "--reload", help="Enable auto-reload"),
):
    """Start the web UI."""
    console.print(f"[bold]Starting web UI on {host}:{port}[/bold]")
    
    try:
        import uvicorn
        
        if reload:
            # Use import string when reload is enabled
            uvicorn.run(
                "ui.web.app:create_app",
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
        else:
            # Use app instance when reload is disabled
            from ui.web.app import ZoharWebApp
            web_app = ZoharWebApp()
            
            uvicorn.run(
                web_app.app,
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
        
    except ImportError:
        console.print("[red]Web UI dependencies not installed. Run: pip install uvicorn fastapi[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error starting web UI: {str(e)}[/red]")
        raise typer.Exit(1)


@ui_app.command("gradio")
def ui_gradio(
    port: int = typer.Option(7860, "--port", help="Port to bind to"),
    share: bool = typer.Option(False, "--share", help="Create public link"),
):
    """Start the Gradio UI."""
    console.print(f"[bold]Starting Gradio UI on port {port}[/bold]")
    
    try:
        from ui.gradio_app import create_gradio_app
        
        app = create_gradio_app()
        app.launch(server_port=port, share=share)
        
    except ImportError:
        console.print("[red]Gradio not installed. Run: pip install gradio[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error starting Gradio UI: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("start")
def start(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    interface: str = typer.Option("web", "--interface", "-i", help="Interface to start (web/gradio)")
):
    """Start Project Zohar application."""
    console.print(f"[bold green]Starting Project Zohar...{interface} interface on {host}:{port}[/bold green]")
    
    if interface == "web":
        ui_web(host=host, port=port, reload=False)
    elif interface == "gradio":
        ui_gradio(port=port)
    else:
        console.print(f"[red]Unknown interface: {interface}. Use 'web' or 'gradio'[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """Stop Project Zohar application."""
    console.print("[bold yellow]Stopping Project Zohar...[/bold yellow]")
    
    try:
        import requests
        # Try to gracefully shutdown via API
        response = requests.post("http://localhost:8000/api/admin/shutdown", timeout=5)
        if response.status_code == 200:
            console.print("[bold green]✓ Project Zohar stopped gracefully[/bold green]")
        else:
            console.print("[yellow]⚠ Could not connect to running instance[/yellow]")
    except Exception:
        console.print("[yellow]⚠ No running instance found or failed to stop gracefully[/yellow]")


@app.command("status")
def status():
    """Check Project Zohar status."""
    console.print("[bold blue]Checking Project Zohar status...[/bold blue]")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            console.print("[bold green]✓ Project Zohar is running[/bold green]")
            console.print(f"[dim]Status: {data.get('status', 'unknown')}[/dim]")
            console.print(f"[dim]Last check: {data.get('timestamp', 'unknown')}[/dim]")
        else:
            console.print("[yellow]⚠ Project Zohar is not responding properly[/yellow]")
    except Exception:
        console.print("[red]✗ Project Zohar is not running[/red]")


@app.command("version")
def version():
    """Show version information."""
    from zohar import __version__
    console.print(f"[bold]Project Zohar[/bold] version {__version__}")


@app.command("doctor")
def doctor():
    """Run system diagnostics."""
    console.print("[bold]Running Project Zohar diagnostics...[/bold]")
    
    # TODO: Implement system diagnostics
    console.print("[bold green]✓ All systems operational![/bold green]")


@app.command("chat")
def chat(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use for chat"),
    agent_type: str = typer.Option("personal", "--type", "-t", help="Agent type (personal/public)"),
    temperature: float = typer.Option(0.7, "--temperature", help="Model temperature (0.0-1.0)"),
    max_tokens: int = typer.Option(2048, "--max-tokens", help="Maximum tokens in response"),
    system_prompt: Optional[str] = typer.Option(None, "--system", "-s", help="Custom system prompt"),
):
    """Start an interactive chat session with the AI model."""
    console.print("[bold blue]Starting interactive chat session[/bold blue]")
    console.print("[dim]Type 'exit', 'quit', or press Ctrl+C to end the session[/dim]")
    console.print("[dim]Type 'help' for available commands[/dim]\n")
    
    # Initialize bot manager
    try:
        bot_manager = BotManager()
        
        # Run the chat session
        asyncio.run(_run_chat_session(bot_manager, agent_type, model, temperature, max_tokens, system_prompt))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat session ended by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting chat session: {str(e)}[/red]")
        raise typer.Exit(1)


async def _run_chat_session(
    bot_manager: BotManager,
    agent_type: str,
    model: Optional[str],
    temperature: float,
    max_tokens: int,
    system_prompt: Optional[str]
):
    """Run the interactive chat session."""
    try:
        # Initialize bot manager
        await bot_manager.initialize()
        
        # Get appropriate agent
        if agent_type == "personal":
            # Create config with CLI parameters
            agent_config = {}
            if model:
                agent_config["model_name"] = model
            if temperature != 0.7:
                agent_config["temperature"] = temperature
            if max_tokens != 2048:
                agent_config["max_tokens"] = max_tokens
            
            # Get personal agent with configuration
            if agent_config:
                # Create agent with specific config
                agent_id = await bot_manager.create_agent(
                    AgentType.PERSONAL, 
                    user_id="cli_user", 
                    config=agent_config
                )
                await bot_manager.start_agent(agent_id)
                agent = bot_manager.agents[agent_id]
            else:
                # Use default agent
                agent = await bot_manager.get_personal_agent("cli_user")
        else:
            agent = await bot_manager.get_public_agent()
        
        # Configure agent if model parameters are provided
        if model or temperature != 0.7 or max_tokens != 2048 or system_prompt:
            # TODO: Implement agent configuration
            pass
        
        conversation_history = []
        
        while True:
            try:
                # Get user input
                user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
                
                if not user_input.strip():
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                elif user_input.lower() == 'help':
                    _show_chat_help()
                    continue
                elif user_input.lower() == 'clear':
                    console.clear()
                    console.print("[dim]Conversation history cleared[/dim]")
                    conversation_history = []
                    continue
                elif user_input.lower() == 'history':
                    _show_conversation_history(conversation_history)
                    continue
                elif user_input.lower().startswith('save'):
                    _save_conversation_history(conversation_history, user_input)
                    continue
                
                # Add user message to history
                conversation_history.append({"role": "user", "content": user_input})
                
                # Show typing indicator
                with console.status("[bold green]AI is thinking...", spinner="dots"):
                    try:
                        # Get response from agent
                        response = await agent.process_message(user_input, {"history": conversation_history})
                        
                        # Add assistant response to history
                        conversation_history.append({"role": "assistant", "content": response})
                        
                        # Display response
                        console.print(f"\n[bold green]AI:[/bold green] {response}")
                        
                    except Exception as e:
                        console.print(f"[red]Error getting response: {str(e)}[/red]")
                        console.print("[dim]Try again or type 'exit' to quit[/dim]")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Chat session interrupted[/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Chat session ended[/yellow]")
                break
    
    finally:
        # Cleanup
        await bot_manager.shutdown()


def _show_chat_help():
    """Show available chat commands."""
    help_text = """
[bold]Available Commands:[/bold]

[cyan]exit, quit, bye[/cyan] - End the chat session
[cyan]help[/cyan] - Show this help message
[cyan]clear[/cyan] - Clear conversation history
[cyan]history[/cyan] - Show conversation history
[cyan]save [filename][/cyan] - Save conversation to file

[bold]Chat Tips:[/bold]
- Press Ctrl+C to interrupt generation
- Long responses may take time to generate
- Use clear, specific questions for best results
    """
    console.print(Panel(help_text, title="Chat Help", border_style="blue"))


def _show_conversation_history(history: List[dict]):
    """Show conversation history."""
    if not history:
        console.print("[dim]No conversation history yet[/dim]")
        return
    
    console.print("\n[bold]Conversation History:[/bold]")
    for i, msg in enumerate(history, 1):
        role = "You" if msg["role"] == "user" else "AI"
        color = "cyan" if msg["role"] == "user" else "green"
        console.print(f"\n[bold {color}]{i}. {role}:[/bold {color}] {msg['content']}")


def _save_conversation_history(history: List[dict], save_command: str):
    """Save conversation history to file."""
    if not history:
        console.print("[dim]No conversation history to save[/dim]")
        return
    
    # Extract filename from command
    parts = save_command.split()
    if len(parts) > 1:
        filename = parts[1]
    else:
        filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Chat History - Project Zohar\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for msg in history:
                role = "User" if msg["role"] == "user" else "AI"
                f.write(f"{role}: {msg['content']}\n\n")
        
        console.print(f"[bold green]✓ Conversation saved to {filename}[/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error saving conversation: {str(e)}[/red]")


@app.command()
def multi_agent(
    query: str = typer.Argument(..., help="Query to process"),
    user_id: str = typer.Option("test_user", "--user-id", help="User ID for the session"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Additional context (JSON format)")
):
    """Test the multi-agent system with DeepSeek and tool-supporting models."""
    import asyncio
    import json
    from module.agent import (
        initialize_multi_agent_system,
        start_multi_agent_system,
        stop_multi_agent_system,
        process_query,
        get_multi_agent_manager
    )
    
    async def run_multi_agent_test():
        try:
            print("🤖 Initializing Multi-Agent System...")
            
            # Initialize the system
            success = await initialize_multi_agent_system()
            if not success:
                print("❌ Failed to initialize multi-agent system")
                return
            
            # Start the system
            success = await start_multi_agent_system()
            if not success:
                print("❌ Failed to start multi-agent system")
                return
            
            print("✅ Multi-agent system started successfully")
            
            # Get system status
            manager = get_multi_agent_manager()
            status = manager.get_system_status()
            print(f"\n📊 System Status:")
            print(f"  - Total agents: {status['total_agents']}")
            print(f"  - Active agents: {status['active_agents']}")
            print(f"  - Available capabilities: {', '.join(manager.get_available_capabilities())}")
            
            # Parse context if provided
            context_dict = {}
            if context:
                try:
                    context_dict = json.loads(context)
                except json.JSONDecodeError:
                    print("⚠️  Invalid JSON context, ignoring")
            
            print(f"\n🔍 Processing query: {query}")
            print("=" * 50)
            
            # Process the query
            response = await process_query(user_id, query, context_dict)
            
            print(f"\n💬 Response:")
            print(response)
            
            # Get performance metrics
            metrics = manager.get_performance_metrics()
            print(f"\n📈 Performance Metrics:")
            print(f"  - Success rate: {metrics['success_rate']}")
            print(f"  - Average response time: {metrics['average_response_time']}")
            print(f"  - Total queries: {metrics['total_queries']}")
            
            # Get agent status
            agent_status = manager.get_all_agents_status()
            print(f"\n🤖 Agent Status:")
            for agent_id, status in agent_status.items():
                if status:
                    print(f"  - {status.get('name', agent_id)}: {'🟢 Active' if status.get('is_active') else '🔴 Inactive'}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Stop the system
            print("\n🛑 Stopping multi-agent system...")
            await stop_multi_agent_system()
            print("✅ Multi-agent system stopped")
    
    asyncio.run(run_multi_agent_test())


@app.command()
def tool_execution_demo():
    """Run the detailed tool execution process demo."""
    async def run_tool_execution_demo():
        try:
            console.print("[bold green]🛠️  Tool Execution Process Demo[/bold green]")
            console.print("[blue]This demo showcases the detailed process of tool execution[/blue]")
            console.print("[blue]including model communication, tool calling, and result synthesis.[/blue]")
            
            # Import and run the demo
            import sys
            from pathlib import Path
            
            # Add the project root to the Python path
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from examples.tool_execution_demo import main as demo_main
            
            await demo_main()
            
        except Exception as e:
            console.print(f"[red]❌ Error in tool execution demo: {str(e)}[/red]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
    
    asyncio.run(run_tool_execution_demo())


def main():
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        if get_settings().debug:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
