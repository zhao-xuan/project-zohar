#!/usr/bin/env python3
"""
Setup Wizard for Project Zohar.

This script provides an interactive setup wizard for configuring
Project Zohar with dependencies, LLM settings, and platform connections.
"""

import os
import sys
import json
import subprocess
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

# Try to import required packages, handle missing imports gracefully
try:
    import rich
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SetupWizard:
    """Interactive setup wizard for Project Zohar."""
    
    def __init__(self):
        """Initialize the setup wizard."""
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        
        # Console for rich output
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
        
        # Configuration data
        self.config = {
            "llm": {
                "provider": "ollama",
                "model": "llama3.2",
                "base_url": "http://localhost:11434",
                "api_key": None,
                "max_tokens": 4096,
                "temperature": 0.7
            },
            "embedding": {
                "model": "all-MiniLM-L6-v2",
                "provider": "sentence-transformers"
            },
            "privacy": {
                "level": "high",
                "local_only": True,
                "anonymize_data": True
            },
            "database": {
                "vector_db": "chroma",
                "conversation_db": "sqlite"
            },
            "platforms": {
                "enabled": [],
                "configs": {}
            },
            "mcp_servers": {
                "enabled": ["filesystem"],
                "configs": {}
            }
        }
        
        # System requirements
        self.requirements = {
            "python": "3.10",
            "packages": [
                "fastapi",
                "uvicorn",
                "camel-ai[all]",
                "chromadb",
                "sentence-transformers",
                "rich",
                "typer",
                "pydantic",
                "python-dotenv"
            ],
            "optional_packages": [
                "torch",
                "transformers",
                "pypdf2",
                "python-docx",
                "pandas",
                "pillow",
                "pytesseract"
            ],
            "system_tools": {
                "ollama": "https://ollama.ai/download",
                "git": "https://git-scm.com/downloads"
            }
        }
        
        logger.info("Setup wizard initialized")
    
    def print(self, text: str, style: Optional[str] = None):
        """Print text with optional styling."""
        if self.console and RICH_AVAILABLE:
            if style:
                self.console.print(text, style=style)
            else:
                self.console.print(text)
        else:
            print(text)
    
    def print_panel(self, text: str, title: str, style: str = "blue"):
        """Print a panel with title."""
        if self.console and RICH_AVAILABLE:
            panel = Panel(text, title=title, border_style=style)
            self.console.print(panel)
        else:
            print(f"\n=== {title} ===")
            print(text)
            print("=" * (len(title) + 8))
    
    def prompt(self, question: str, default: Optional[str] = None, choices: Optional[List[str]] = None) -> str:
        """Prompt user for input."""
        if self.console and RICH_AVAILABLE:
            return Prompt.ask(question, default=default, choices=choices)
        else:
            # Fallback for when rich is not available
            prompt_text = question
            if default:
                prompt_text += f" [{default}]"
            if choices:
                prompt_text += f" ({'/'.join(choices)})"
            prompt_text += ": "
            
            response = input(prompt_text).strip()
            return response if response else (default or "")
    
    def confirm(self, question: str, default: bool = True) -> bool:
        """Ask for confirmation."""
        if self.console and RICH_AVAILABLE:
            return Confirm.ask(question, default=default)
        else:
            # Fallback
            default_text = "Y/n" if default else "y/N"
            response = input(f"{question} [{default_text}]: ").strip().lower()
            
            if not response:
                return default
            return response in ['y', 'yes', 'true', '1']
    
    async def run(self):
        """Run the complete setup wizard."""
        try:
            self.print_welcome()
            
            # Step 1: Check system requirements
            if not await self.check_system_requirements():
                self.print("❌ System requirements check failed", "red")
                return False
            
            # Step 2: Setup directory structure
            self.setup_directories()
            
            # Step 3: Install dependencies
            if not await self.install_dependencies():
                self.print("❌ Dependency installation failed", "red")
                return False
            
            # Step 4: Configure LLM
            await self.configure_llm()
            
            # Step 5: Configure privacy settings
            self.configure_privacy()
            
            # Step 6: Setup platforms (optional)
            if self.confirm("Would you like to configure platform integrations?", False):
                await self.configure_platforms()
            
            # Step 7: Setup MCP servers
            await self.configure_mcp_servers()
            
            # Step 8: Save configuration
            self.save_configuration()
            
            # Step 9: Test installation
            if self.confirm("Would you like to test the installation?", True):
                await self.test_installation()
            
            self.print_completion()
            return True
            
        except KeyboardInterrupt:
            self.print("\n❌ Setup cancelled by user", "yellow")
            return False
        except Exception as e:
            self.print(f"❌ Setup failed: {e}", "red")
            logger.error(f"Setup wizard error: {e}")
            return False
    
    def print_welcome(self):
        """Print welcome message."""
        welcome_text = """
Welcome to Project Zohar Setup Wizard!

This wizard will help you set up your privacy-focused AI assistant.
We'll configure:
• System dependencies
• LLM providers (Ollama recommended)
• Privacy settings
• Platform integrations
• MCP servers for tool access

Let's get started! 🚀
        """
        
        self.print_panel(welcome_text.strip(), "Project Zohar Setup", "green")
    
    async def check_system_requirements(self) -> bool:
        """Check and validate system requirements."""
        self.print("\n🔍 Checking system requirements...", "blue")
        
        requirements_met = True
        
        # Check Python version
        python_version = sys.version_info
        required_version = tuple(map(int, self.requirements["python"].split(".")))
        
        if python_version[:2] >= required_version:
            self.print(f"✅ Python {python_version.major}.{python_version.minor} (required: {self.requirements['python']})", "green")
        else:
            self.print(f"❌ Python {python_version.major}.{python_version.minor} (required: {self.requirements['python']})", "red")
            requirements_met = False
        
        # Check for system tools
        for tool, download_url in self.requirements["system_tools"].items():
            if shutil.which(tool):
                self.print(f"✅ {tool} found", "green")
            else:
                self.print(f"⚠️  {tool} not found - download from: {download_url}", "yellow")
                if tool == "ollama":
                    if not self.confirm(f"Continue without {tool}? (You can install it later)", False):
                        requirements_met = False
        
        # Check available disk space
        try:
            disk_usage = shutil.disk_usage(self.project_root)
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb >= 5.0:  # Require at least 5GB free
                self.print(f"✅ Disk space: {free_gb:.1f}GB available", "green")
            else:
                self.print(f"⚠️  Low disk space: {free_gb:.1f}GB available (recommended: 5GB+)", "yellow")
        except Exception:
            self.print("⚠️  Could not check disk space", "yellow")
        
        return requirements_met
    
    def setup_directories(self):
        """Create necessary directory structure."""
        self.print("\n📁 Setting up directory structure...", "blue")
        
        directories = [
            self.config_dir,
            self.data_dir,
            self.data_dir / "vectordb",
            self.data_dir / "conversations",
            self.logs_dir,
            self.project_root / "agent_workspace"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.print(f"✅ Created: {directory.relative_to(self.project_root)}", "green")
    
    async def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        self.print("\n📦 Installing dependencies...", "blue")
        
        # Check if pip is available
        if not shutil.which("pip"):
            self.print("❌ pip not found. Please install pip first.", "red")
            return False
        
        # Install required packages
        for package in self.requirements["packages"]:
            if not await self.install_package(package):
                self.print(f"❌ Failed to install {package}", "red")
                if not self.confirm(f"Continue without {package}?", False):
                    return False
        
        # Install optional packages
        if self.confirm("Install optional packages for enhanced functionality?", True):
            for package in self.requirements["optional_packages"]:
                await self.install_package(package, optional=True)
        
        return True
    
    async def install_package(self, package: str, optional: bool = False) -> bool:
        """Install a Python package."""
        try:
            self.print(f"Installing {package}...", "yellow")
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.print(f"✅ {package} installed successfully", "green")
                return True
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                if optional:
                    self.print(f"⚠️  Failed to install optional package {package}: {error_msg}", "yellow")
                    return True  # Don't fail for optional packages
                else:
                    self.print(f"❌ Failed to install {package}: {error_msg}", "red")
                    return False
                    
        except Exception as e:
            if optional:
                self.print(f"⚠️  Error installing optional package {package}: {e}", "yellow")
                return True
            else:
                self.print(f"❌ Error installing {package}: {e}", "red")
                return False
    
    async def configure_llm(self):
        """Configure LLM provider and settings."""
        self.print("\n🧠 Configuring LLM provider...", "blue")
        
        # Choose LLM provider
        providers = ["ollama", "openai", "anthropic", "other"]
        provider = self.prompt(
            "Choose LLM provider",
            default="ollama",
            choices=providers
        )
        
        self.config["llm"]["provider"] = provider
        
        if provider == "ollama":
            await self.configure_ollama()
        elif provider == "openai":
            self.configure_openai()
        elif provider == "anthropic":
            self.configure_anthropic()
        else:
            self.configure_custom_llm()
    
    async def configure_ollama(self):
        """Configure Ollama settings."""
        self.print("📝 Configuring Ollama...", "blue")
        
        # Check if Ollama is running
        if shutil.which("ollama"):
            try:
                # Test Ollama connection
                process = await asyncio.create_subprocess_exec(
                    "ollama", "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    self.print("✅ Ollama is running", "green")
                    
                    # Show available models
                    models_output = stdout.decode()
                    if models_output.strip():
                        self.print("Available models:", "blue")
                        print(models_output)
                    
                    # Choose model
                    default_model = "llama3.2"
                    model = self.prompt(
                        "Enter model name",
                        default=default_model
                    )
                    
                    self.config["llm"]["model"] = model
                    
                    # Test model availability
                    if not await self.test_ollama_model(model):
                        if self.confirm(f"Model {model} not available. Download it?", True):
                            await self.download_ollama_model(model)
                
                else:
                    self.print("⚠️  Ollama not running. Please start it manually.", "yellow")
                    
            except Exception as e:
                self.print(f"⚠️  Error checking Ollama: {e}", "yellow")
        else:
            self.print("⚠️  Ollama not installed. Please install from https://ollama.ai", "yellow")
        
        # Configure base URL
        base_url = self.prompt(
            "Ollama base URL",
            default="http://localhost:11434"
        )
        self.config["llm"]["base_url"] = base_url
    
    async def test_ollama_model(self, model: str) -> bool:
        """Test if Ollama model is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ollama", "show", model,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception:
            return False
    
    async def download_ollama_model(self, model: str):
        """Download Ollama model."""
        try:
            self.print(f"⬇️  Downloading model {model}...", "yellow")
            
            process = await asyncio.create_subprocess_exec(
                "ollama", "pull", model,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                output = line.decode().strip()
                if output:
                    self.print(output, "dim")
            
            await process.wait()
            
            if process.returncode == 0:
                self.print(f"✅ Model {model} downloaded successfully", "green")
            else:
                self.print(f"❌ Failed to download model {model}", "red")
                
        except Exception as e:
            self.print(f"❌ Error downloading model: {e}", "red")
    
    def configure_openai(self):
        """Configure OpenAI settings."""
        self.print("📝 Configuring OpenAI...", "blue")
        
        api_key = self.prompt("Enter OpenAI API key")
        self.config["llm"]["api_key"] = api_key
        
        model = self.prompt(
            "Choose model",
            default="gpt-4",
            choices=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        )
        self.config["llm"]["model"] = model
        
        self.config["llm"]["base_url"] = "https://api.openai.com/v1"
    
    def configure_anthropic(self):
        """Configure Anthropic settings."""
        self.print("📝 Configuring Anthropic...", "blue")
        
        api_key = self.prompt("Enter Anthropic API key")
        self.config["llm"]["api_key"] = api_key
        
        model = self.prompt(
            "Choose model",
            default="claude-3-sonnet-20240229",
            choices=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        )
        self.config["llm"]["model"] = model
        
        self.config["llm"]["base_url"] = "https://api.anthropic.com"
    
    def configure_custom_llm(self):
        """Configure custom LLM provider."""
        self.print("📝 Configuring custom LLM...", "blue")
        
        base_url = self.prompt("Enter base URL")
        self.config["llm"]["base_url"] = base_url
        
        api_key = self.prompt("Enter API key (if required, leave empty for none)")
        if api_key.strip():
            self.config["llm"]["api_key"] = api_key
        
        model = self.prompt("Enter model name")
        self.config["llm"]["model"] = model
    
    def configure_privacy(self):
        """Configure privacy settings."""
        self.print("\n🔒 Configuring privacy settings...", "blue")
        
        # Privacy level
        levels = ["low", "medium", "high", "maximum"]
        level = self.prompt(
            "Choose privacy level",
            default="high",
            choices=levels
        )
        self.config["privacy"]["level"] = level
        
        # Local-only mode
        local_only = self.confirm(
            "Enable local-only mode? (No data sent to external services)",
            True
        )
        self.config["privacy"]["local_only"] = local_only
        
        # Data anonymization
        anonymize = self.confirm(
            "Enable automatic data anonymization?",
            True
        )
        self.config["privacy"]["anonymize_data"] = anonymize
        
        self.print(f"✅ Privacy level set to: {level}", "green")
    
    async def configure_platforms(self):
        """Configure platform integrations."""
        self.print("\n🔗 Configuring platform integrations...", "blue")
        
        available_platforms = [
            "gmail", "outlook", "slack", "discord", "telegram",
            "twitter", "linkedin", "notion", "google_drive", "dropbox"
        ]
        
        self.print("Available platforms:", "blue")
        for i, platform in enumerate(available_platforms, 1):
            print(f"  {i}. {platform}")
        
        if self.confirm("Configure platforms now?", False):
            # This would implement platform-specific configuration
            # For now, just show the concept
            platform = self.prompt(
                "Choose platform to configure",
                choices=available_platforms
            )
            
            self.print(f"📝 Platform {platform} configuration would be implemented here", "yellow")
            self.config["platforms"]["enabled"].append(platform)
    
    async def configure_mcp_servers(self):
        """Configure MCP servers."""
        self.print("\n🔧 Configuring MCP servers...", "blue")
        
        available_servers = [
            "filesystem", "brave_search", "git", "sqlite",
            "postgres", "time", "weather", "calendar"
        ]
        
        if self.confirm("Configure MCP servers for tool access?", True):
            self.print("Available MCP servers:", "blue")
            for server in available_servers:
                enable = self.confirm(f"Enable {server} server?", server == "filesystem")
                if enable:
                    self.config["mcp_servers"]["enabled"].append(server)
    
    def save_configuration(self):
        """Save configuration to files."""
        self.print("\n💾 Saving configuration...", "blue")
        
        # Save main config
        config_file = self.config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        # Create environment file
        env_file = self.project_root / "config.env"
        with open(env_file, 'w') as f:
            f.write("# Project Zohar Configuration\n")
            f.write(f"LLM_PROVIDER={self.config['llm']['provider']}\n")
            f.write(f"LLM_MODEL_NAME={self.config['llm']['model']}\n")
            f.write(f"LLM_BASE_URL={self.config['llm']['base_url']}\n")
            
            if self.config['llm'].get('api_key'):
                f.write(f"LLM_API_KEY={self.config['llm']['api_key']}\n")
            
            f.write(f"PRIVACY_LEVEL={self.config['privacy']['level']}\n")
            f.write(f"LOCAL_ONLY={self.config['privacy']['local_only']}\n")
            f.write(f"EMBEDDING_MODEL={self.config['embedding']['model']}\n")
        
        # Create platform configs
        if self.config["platforms"]["enabled"]:
            platforms_file = self.config_dir / "platforms.json"
            with open(platforms_file, 'w') as f:
                json.dump({
                    "version": "1.0.0",
                    "platforms": []
                }, f, indent=2)
        
        # Create MCP config
        if self.config["mcp_servers"]["enabled"]:
            mcp_file = self.config_dir / "mcp_services.json"
            mcp_config = {
                "version": "1.0.0",
                "services": []
            }
            
            for server in self.config["mcp_servers"]["enabled"]:
                mcp_config["services"].append({
                    "id": server,
                    "name": server.title(),
                    "description": f"{server.title()} MCP server",
                    "connection_type": "subprocess",
                    "endpoint": "",
                    "command": f"mcp-server-{server}",
                    "args": [],
                    "auto_start": True
                })
            
            with open(mcp_file, 'w') as f:
                json.dump(mcp_config, f, indent=2)
        
        self.print("✅ Configuration saved", "green")
    
    async def test_installation(self):
        """Test the installation."""
        self.print("\n🧪 Testing installation...", "blue")
        
        try:
            # Test imports
            self.print("Testing imports...", "yellow")
            
            test_imports = [
                "zohar.config.settings",
                "zohar.utils.logging",
                "zohar.core.agents.personal_agent"
            ]
            
            for module in test_imports:
                try:
                    __import__(module)
                    self.print(f"✅ {module}", "green")
                except ImportError as e:
                    self.print(f"❌ {module}: {e}", "red")
            
            # Test configuration loading
            self.print("Testing configuration...", "yellow")
            try:
                from zohar.config.settings import get_settings
                settings = get_settings()
                self.print("✅ Configuration loaded", "green")
            except Exception as e:
                self.print(f"❌ Configuration error: {e}", "red")
            
            # Test LLM connection (if configured)
            if self.config["llm"]["provider"] == "ollama":
                await self.test_ollama_connection()
            
            self.print("✅ Installation test completed", "green")
            
        except Exception as e:
            self.print(f"❌ Test failed: {e}", "red")
    
    async def test_ollama_connection(self):
        """Test Ollama connection."""
        self.print("Testing Ollama connection...", "yellow")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.config['llm']['base_url']}/api/tags"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        self.print("✅ Ollama connection successful", "green")
                    else:
                        self.print(f"⚠️  Ollama connection failed: {response.status}", "yellow")
                        
        except Exception as e:
            self.print(f"⚠️  Ollama connection test failed: {e}", "yellow")
    
    def print_completion(self):
        """Print completion message."""
        completion_text = """
🎉 Setup Complete!

Project Zohar has been successfully configured. Here's what you can do next:

1. Start the CLI:
   python -m zohar.cli start

2. Launch the web interface:
   python -m zohar.cli ui web

3. Run the setup wizard again:
   python scripts/setup_wizard.py

4. Check the documentation:
   • README.md - Main documentation
   • docs/ - Detailed guides

For help and support:
• Check the logs in the logs/ directory
• Review the configuration in config/
• Use 'python -m zohar.cli --help' for CLI help

Happy AI assisting! 🤖
        """
        
        self.print_panel(completion_text.strip(), "Setup Complete! 🎉", "green")


async def main():
    """Main function to run the setup wizard."""
    wizard = SetupWizard()
    
    try:
        success = await wizard.run()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle case where rich is not available
    if not RICH_AVAILABLE:
        print("Installing rich for better user experience...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
        print("Please run the setup wizard again.")
        sys.exit(0)
    
    asyncio.run(main()) 