#!/usr/bin/env python3
"""
Setup script for MCP Email Server

This script helps set up the email providers and their authentication:
- Gmail OAuth2 setup
- Microsoft Outlook OAuth2 setup  
- QQ Mail app password configuration
"""

import os
import json
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text

console = Console()

def print_title():
    """Print setup title"""
    title = Text("MCP Email Server Setup", style="bold blue")
    console.print(Panel(title, padding=1))

def check_dependencies():
    """Check if all required dependencies are installed"""
    console.print("\n[yellow]Checking dependencies...[/yellow]")
    
    required_packages = [
        'google-api-python-client',
        'google-auth-httplib2', 
        'google-auth-oauthlib',
        'httpx',
        'aiohttp'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            console.print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            console.print(f"❌ {package}")
    
    if missing:
        console.print(f"\n[red]Missing dependencies: {', '.join(missing)}[/red]")
        console.print("Install with: pip install " + " ".join(missing))
        return False
    
    console.print("\n[green]All dependencies installed![/green]")
    return True

def setup_gmail_oauth():
    """Setup Gmail OAuth2 credentials"""
    console.print("\n[cyan]Setting up Gmail OAuth2...[/cyan]")
    
    console.print("""
To use Gmail API, you need to:
1. Go to https://console.developers.google.com/
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth2 credentials (Desktop application)
5. Download the credentials JSON file
    """)
    
    creds_path = Prompt.ask("Enter path to Gmail credentials JSON file")
    
    if not os.path.exists(creds_path):
        console.print(f"[red]File not found: {creds_path}[/red]")
        return None
    
    # Copy to project directory
    project_dir = Path(__file__).parent.parent
    target_path = project_dir / "config" / "gmail_credentials.json"
    target_path.parent.mkdir(exist_ok=True)
    
    import shutil
    shutil.copy2(creds_path, target_path)
    
    console.print(f"[green]Gmail credentials copied to {target_path}[/green]")
    
    return {
        "enabled": True,
        "credentials_file": str(target_path),
        "token_file": str(project_dir / "config" / "gmail_token.json")
    }

def setup_outlook_oauth():
    """Setup Microsoft Outlook OAuth2"""
    console.print("\n[cyan]Setting up Microsoft Outlook OAuth2...[/cyan]")
    
    console.print("""
To use Outlook API, you need to:
1. Go to https://portal.azure.com/
2. Register a new application in Azure AD
3. Add Microsoft Graph API permissions (Mail.ReadWrite, Mail.Send)
4. Get Client ID and Client Secret
    """)
    
    if not Confirm.ask("Do you have Azure App Registration ready?"):
        console.print("[yellow]Please complete Azure setup first[/yellow]")
        return None
    
    client_id = Prompt.ask("Enter Client ID")
    client_secret = Prompt.ask("Enter Client Secret", password=True)
    
    # For production, you'd implement proper OAuth flow here
    console.print("""
[yellow]Note: This setup requires implementing OAuth2 flow.
For now, you'll need to manually obtain an access token.[/yellow]
    """)
    
    access_token = Prompt.ask("Enter access token (optional, for testing)", default="")
    
    return {
        "enabled": True,
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": access_token if access_token else None
    }

def setup_qq_mail():
    """Setup QQ Mail SMTP/IMAP"""
    console.print("\n[cyan]Setting up QQ Mail...[/cyan]")
    
    console.print("""
To use QQ Mail, you need to:
1. Enable SMTP/IMAP in QQ Mail settings
2. Generate an app password (not your regular password)
3. Use the app password for authentication
    """)
    
    if not Confirm.ask("Do you have QQ Mail app password ready?"):
        console.print("[yellow]Please enable SMTP/IMAP and get app password first[/yellow]")
        return None
    
    username = Prompt.ask("Enter QQ Mail username (e.g., user@qq.com)")
    password = Prompt.ask("Enter QQ Mail app password", password=True)
    
    return {
        "enabled": True,
        "username": username,
        "password": password
    }

def create_config_file(config: Dict[str, Any]):
    """Create configuration file"""
    project_dir = Path(__file__).parent.parent
    config_dir = project_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "mcp_email_config.json"
    
    with open(config_file, 'w') as f:
        json.dump(config, indent=2, fp=f)
    
    console.print(f"[green]Configuration saved to {config_file}[/green]")
    return config_file

def create_env_file(config: Dict[str, Any]):
    """Create .env file with configuration"""
    project_dir = Path(__file__).parent.parent
    env_file = project_dir / ".env"
    
    env_content = []
    
    # Gmail settings
    if config.get("gmail", {}).get("enabled"):
        env_content.extend([
            "GMAIL_ENABLED=true",
            f"GMAIL_CREDENTIALS_FILE={config['gmail']['credentials_file']}",
            f"GMAIL_TOKEN_FILE={config['gmail']['token_file']}"
        ])
    
    # Outlook settings
    if config.get("outlook", {}).get("enabled"):
        env_content.extend([
            "OUTLOOK_ENABLED=true",
            f"OUTLOOK_CLIENT_ID={config['outlook']['client_id']}",
            f"OUTLOOK_CLIENT_SECRET={config['outlook']['client_secret']}"
        ])
        if config['outlook'].get('access_token'):
            env_content.append(f"OUTLOOK_ACCESS_TOKEN={config['outlook']['access_token']}")
    
    # QQ Mail settings
    if config.get("qq_mail", {}).get("enabled"):
        env_content.extend([
            "QQ_MAIL_ENABLED=true",
            f"QQ_MAIL_USERNAME={config['qq_mail']['username']}",
            f"QQ_MAIL_PASSWORD={config['qq_mail']['password']}"
        ])
    
    with open(env_file, 'w') as f:
        f.write('\n'.join(env_content))
    
    console.print(f"[green]Environment file created: {env_file}[/green]")

def create_demo_script():
    """Create a demo script to test the MCP email server"""
    project_dir = Path(__file__).parent.parent
    demo_file = project_dir / "examples" / "mcp_email_demo.py"
    demo_file.parent.mkdir(exist_ok=True)
    
    demo_content = '''#!/usr/bin/env python3
"""
Demo script for MCP Email Server

This script demonstrates how to use the MCP Email Server
with different email providers.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.mcp_email_server import MCPEmailServer

async def demo_email_operations():
    """Demonstrate email operations"""
    # Initialize server
    config_path = Path(__file__).parent.parent / "config" / "mcp_email_config.json"
    server = MCPEmailServer(str(config_path) if config_path.exists() else None)
    
    print("🚀 Starting MCP Email Server Demo...")
    
    # Authenticate all providers
    auth_results = await server.authenticate_all()
    print(f"Authentication results: {auth_results}")
    
    if not any(auth_results.values()):
        print("❌ No providers authenticated successfully")
        return
    
    # Get available tools
    tools = server.get_mcp_tools()
    print(f"\\n📧 Available tools: {[tool['name'] for tool in tools]}")
    
    # Demo 1: Get latest emails
    print("\\n📥 Getting latest emails...")
    result = await server.get_latest_emails(count=5)
    if result["success"]:
        print(f"Found {result['total_emails']} emails across providers")
        for provider, emails in result["data"].items():
            print(f"  {provider}: {len(emails)} emails")
            for email in emails[:2]:  # Show first 2
                print(f"    - {email['subject']} from {email['sender']}")
    else:
        print(f"Error: {result['error']}")
    
    # Demo 2: Search emails
    print("\\n🔍 Searching for emails with 'meeting'...")
    result = await server.search_emails("meeting")
    if result["success"]:
        print(f"Found {result['total_results']} emails containing 'meeting'")
    else:
        print(f"Error: {result['error']}")
    
    # Demo 3: Send test email (commented out to avoid spam)
    print("\\n📤 Email sending capability available")
    print("(Uncomment send_email section to test)")
    """
    result = await server.send_email(
        provider="gmail",  # or "outlook", "qq_mail"
        recipients=["test@example.com"],
        subject="Test from MCP Email Server",
        body="This is a test email from the MCP Email Server!"
    )
    print(f"Send result: {result}")
    """
    
    # Demo 4: Email summarization
    if any(auth_results.values()):
        provider = list(auth_results.keys())[0]
        emails_result = await server.get_latest_emails(provider=provider, count=1)
        if emails_result["success"] and emails_result["data"].get(provider):
            email_id = emails_result["data"][provider][0]["id"]
            print(f"\\n📝 Summarizing email {email_id}...")
            
            summary_result = await server.summarize_and_extract_actions(provider, email_id)
            if summary_result["success"]:
                print(f"Summary: {summary_result['summary']}")
                print(f"Priority: {summary_result['priority']}")
                print(f"Action items: {summary_result['action_items']}")
                print(f"Links found: {summary_result['links']}")
            else:
                print(f"Summary error: {summary_result['error']}")
    
    print("\\n✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_email_operations())
'''
    
    with open(demo_file, 'w') as f:
        f.write(demo_content)
    
    # Make executable
    os.chmod(demo_file, 0o755)
    
    console.print(f"[green]Demo script created: {demo_file}[/green]")

@click.command()
@click.option('--skip-deps', is_flag=True, help='Skip dependency check')
def main(skip_deps):
    """Setup MCP Email Server with multiple providers"""
    print_title()
    
    if not skip_deps and not check_dependencies():
        sys.exit(1)
    
    # Setup configuration
    config = {
        "gmail": {"enabled": False},
        "outlook": {"enabled": False},
        "qq_mail": {"enabled": False}
    }
    
    # Setup Gmail
    if Confirm.ask("\\nSetup Gmail integration?"):
        gmail_config = setup_gmail_oauth()
        if gmail_config:
            config["gmail"] = gmail_config
    
    # Setup Outlook
    if Confirm.ask("\\nSetup Outlook integration?"):
        outlook_config = setup_outlook_oauth()
        if outlook_config:
            config["outlook"] = outlook_config
    
    # Setup QQ Mail
    if Confirm.ask("\\nSetup QQ Mail integration?"):
        qq_config = setup_qq_mail()
        if qq_config:
            config["qq_mail"] = qq_config
    
    # Check if any provider was configured
    if not any(provider["enabled"] for provider in config.values()):
        console.print("[red]No email providers configured![/red]")
        sys.exit(1)
    
    # Create configuration files
    config_file = create_config_file(config)
    create_env_file(config)
    create_demo_script()
    
    # Final instructions
    console.print("\\n[green]✅ Setup completed![/green]")
    console.print(f"""
Next steps:
1. Review configuration in {config_file}
2. Test the setup with: python examples/mcp_email_demo.py
3. Integrate with your MCP framework using src/services/mcp_email_server.py

Available MCP tools:
- get_latest_emails: Get recent emails from providers
- search_emails: Search emails by keyword
- send_email: Send emails through providers
- reply_with_template: Reply using customizable templates
- forward_email: Forward emails to other addresses
- move_email: Move emails to folders
- flag_email: Flag/unflag emails
- summarize_and_extract_actions: Get email summaries and action items
    """)

if __name__ == "__main__":
    main() 