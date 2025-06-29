#!/usr/bin/env python3
"""
Setup Wizard for Personal Chatbot System
"""
import os
import sys
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_setup_wizard():
    """Run the interactive setup wizard"""
    console.print(Panel.fit(
        "🚀 Welcome to Personal Chatbot Setup",
        title="Setup Wizard",
        border_style="blue"
    ))
    
    # Check system requirements
    console.print("\n📋 Checking system requirements...")
    check_system_requirements()
    
    # Gather configuration
    config = gather_configuration()
    
    # Create directory structure
    console.print("\n📁 Creating directory structure...")
    create_directory_structure()
    
    # Install Ollama and DeepSeek
    console.print("\n🤖 Setting up local LLM...")
    setup_ollama()
    
    # Create configuration files
    console.print("\n⚙️  Creating configuration files...")
    create_config_files(config)
    
    # Create sample data files
    console.print("\n📄 Creating sample data files...")
    create_sample_data()
    
    # Final instructions
    console.print("\n✅ Setup complete!")
    show_next_steps()


def check_system_requirements():
    """Check if system meets requirements"""
    requirements = [
        ("Python 3.8+", sys.version_info >= (3, 8)),
        ("pip", check_command_exists("pip") or check_command_exists("pip3")),
        ("git", check_command_exists("git")),
    ]
    
    table = Table(title="System Requirements")
    table.add_column("Requirement", style="cyan")
    table.add_column("Status", style="green")
    
    for requirement, met in requirements:
        status = "✅ Met" if met else "❌ Missing"
        table.add_row(requirement, status)
    
    console.print(table)
    
    if not all(met for _, met in requirements):
        console.print("\n⚠️  Please install missing requirements before continuing.")
        sys.exit(1)


def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system"""
    return os.system(f"which {command} > /dev/null 2>&1") == 0


def gather_configuration() -> Dict:
    """Gather configuration from user"""
    console.print("\n🔧 Configuration Setup")
    
    config = {}
    
    # Basic settings
    config['user_name'] = Prompt.ask("What's your name?", default="User")
    config['enable_public_bot'] = Confirm.ask("Enable public bot?", default=True)
    
    # Email configuration
    console.print("\n📧 Email Configuration (optional)")
    config['setup_email'] = Confirm.ask("Set up email integration?", default=False)
    
    if config['setup_email']:
        email_providers = ["gmail", "outlook", "qq", "other"]
        config['email_provider'] = Prompt.ask(
            "Email provider",
            choices=email_providers,
            default="gmail"
        )
        
        if config['email_provider'] == "gmail":
            config['gmail_setup'] = True
            console.print("📝 You'll need to set up Gmail API credentials later.")
        elif config['email_provider'] == "qq":
            config['qq_email'] = Prompt.ask("QQ Email address", default="")
            console.print("📝 You'll need to enable IMAP and get an app password.")
    
    # LLM settings
    console.print("\n🧠 LLM Configuration")
    config['install_ollama'] = Confirm.ask("Install Ollama and DeepSeek?", default=True)
    
    if not config['install_ollama']:
        config['ollama_host'] = Prompt.ask(
            "Ollama host URL",
            default="http://localhost:11434"
        )
    
    # Data sources
    console.print("\n📚 Data Sources")
    config['data_sources'] = []
    
    if Confirm.ask("Import documents from a folder?", default=False):
        folder = Prompt.ask("Documents folder path", default="~/Documents")
        config['data_sources'].append(('documents', folder))
    
    return config


def create_directory_structure():
    """Create the necessary directory structure"""
    directories = [
        "data/personal",
        "data/public",
        "data/processed/vector_db",
        "data/credentials",
        "logs",
        "scripts",
        "src/core/agents",
        "src/core/orchestration",
        "src/core/memory",
        "src/rag/embeddings",
        "src/rag/retrieval",
        "src/rag/storage",
        "src/tools/mcp_servers",
        "src/tools/email",
        "src/tools/browser",
        "src/tools/system",
        "src/ui/web",
        "src/ui/terminal",
        "tests/unit",
        "tests/integration",
        "examples",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        console.print(f"  ✅ Created: {directory}")


def setup_ollama():
    """Set up Ollama and download DeepSeek model"""
    if not check_command_exists("ollama"):
        console.print("📥 Installing Ollama...")
        if sys.platform == "darwin":  # macOS
            os.system("curl -fsSL https://ollama.ai/install.sh | sh")
        else:
            console.print("Please install Ollama manually from https://ollama.ai")
            return
    
    console.print("🤖 Downloading DeepSeek model...")
    result = os.system("ollama pull deepseek")
    
    if result == 0:
        console.print("  ✅ DeepSeek model installed successfully")
    else:
        console.print("  ⚠️  Failed to download DeepSeek model. You can try manually: ollama pull deepseek")


def create_config_files(config: Dict):
    """Create configuration files based on user input"""
    # Create .env file
    env_content = f"""# Personal Chatbot System Configuration
# Generated by setup wizard

DEBUG=false
SECRET_KEY={generate_secret_key()}

# LLM Settings
LLM_MODEL_NAME=deepseek
OLLAMA_HOST=http://localhost:11434
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7

# Web UI Settings
PERSONAL_BOT_PORT=5000
PUBLIC_BOT_PORT=5001
ENABLE_PUBLIC_BOT={str(config['enable_public_bot']).lower()}

# Data Paths
PERSONAL_DATA_PATH=./data/personal
PUBLIC_DATA_PATH=./data/public
PROCESSED_DATA_PATH=./data/processed

# Persona Configuration
TONE_EXAMPLES_PATH=./data/personal/tone_examples.txt
PERSONAL_BIO_PATH=./data/personal/bio.txt
PUBLIC_BIO_PATH=./data/public/public_bio.txt

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/chatbot.log
"""
    
    if config.get('setup_email'):
        env_content += "\n# Email Configuration\n"
        if config.get('gmail_setup'):
            env_content += """GMAIL_CREDENTIALS_PATH=./data/credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=./data/credentials/gmail_token.json
"""
        if config.get('qq_email'):
            env_content += f"""QQ_EMAIL={config['qq_email']}
# QQ_APP_PASSWORD=your-app-password-here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    console.print("  ✅ Created .env configuration file")


def create_sample_data():
    """Create sample data files"""
    # Personal bio
    personal_bio = f"""I am {input('Enter your name: ') or 'a professional'} with expertise in technology and AI.

KEY INFORMATION:
- Experienced in software development and AI systems
- Interested in productivity tools and automation
- Values privacy and data security
- Prefers direct, helpful communication

BACKGROUND:
- Works with various programming languages and frameworks
- Has experience with machine learning and AI systems
- Enjoys building tools that improve efficiency
- Believes in the importance of local, privacy-preserving AI

CURRENT PROJECTS:
- Building personal AI assistant systems
- Exploring multi-agent architectures
- Working on data privacy solutions
"""
    
    with open('data/personal/bio.txt', 'w') as f:
        f.write(personal_bio)
    
    # Public bio (sanitized version)
    public_bio = """A technology professional with expertise in AI and software development.

PUBLIC INFORMATION:
- Software developer and AI enthusiast
- Interested in productivity tools and automation
- Advocates for privacy-preserving AI solutions
- Available for general technology discussions

AREAS OF EXPERTISE:
- Machine learning and AI systems
- Software architecture and development
- Data privacy and security
- Personal productivity tools

Feel free to ask about technology topics, AI developments, or general professional inquiries.
"""
    
    with open('data/public/public_bio.txt', 'w') as f:
        f.write(public_bio)
    
    # Tone examples
    tone_examples = """Here are examples of my communication style:

CASUAL MESSAGES:
"Hey! Thanks for reaching out. I'd be happy to help with that project."
"That's a great question! Let me think through this..."
"Absolutely! I think we can definitely make this work."

PROFESSIONAL MESSAGES:
"Thank you for your inquiry. I'd be pleased to assist with this matter."
"I appreciate you bringing this to my attention."
"Please let me know if you need any additional information."

TECHNICAL DISCUSSIONS:
"The implementation looks solid, but we might want to consider edge cases."
"This approach should scale well, especially with proper caching."
"I like the architecture - it's clean and maintainable."

GENERAL STYLE:
- Direct and helpful
- Uses friendly but professional tone
- Asks clarifying questions when needed
- Provides detailed explanations when helpful
- Shows enthusiasm with appropriate use of exclamation points
"""
    
    with open('data/personal/tone_examples.txt', 'w') as f:
        f.write(tone_examples)
    
    console.print("  ✅ Created sample data files")
    console.print("  📝 You can edit these files to customize your AI's personality")


def generate_secret_key() -> str:
    """Generate a random secret key"""
    import secrets
    return secrets.token_urlsafe(32)


def show_next_steps():
    """Show next steps after setup"""
    console.print(Panel.fit(
        """🎉 Setup Complete! Here's what you can do next:

1. 📝 Customize your persona:
   • Edit data/personal/bio.txt with your information
   • Update data/personal/tone_examples.txt with your communication style
   • Modify data/public/public_bio.txt for public interactions

2. 🔐 Set up email integration (if chosen):
   • Follow the email setup guide in docs/email_setup.md
   • Add your credentials to the data/credentials/ folder

3. 📚 Add your personal data:
   • Run: python main.py index-data --source /path/to/your/documents
   • Import emails using the data indexing tools

4. 🚀 Start your chatbot:
   • Terminal interface: python main.py terminal
   • Web interface: python main.py web
   • Start MCP servers: python main.py start-mcp-servers

5. 🧪 Test your setup:
   • Run: python main.py status
   • Try some sample conversations

6. 📖 Read the documentation:
   • Check out README.md for detailed instructions
   • Browse examples/ for usage examples

Enjoy your personal AI assistant! 🤖""",
        title="Next Steps",
        border_style="green"
    ))


if __name__ == "__main__":
    run_setup_wizard() 