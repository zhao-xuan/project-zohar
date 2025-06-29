"""
Terminal CLI for Personal Chatbot System
"""
import asyncio
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


async def run_terminal_interface(bot_type: str = "personal"):
    """
    Run the terminal interface for the chatbot
    
    Args:
        bot_type: Type of bot to run ('personal' or 'public')
    """
    # Display welcome message
    bot_emoji = "🔐" if bot_type == "personal" else "🌐"
    bot_name = "Personal Bot" if bot_type == "personal" else "Public Bot"
    
    console.print(Panel.fit(
        f"{bot_emoji} Welcome to {bot_name}!\n"
        f"Type your message and press Enter to chat.\n"
        f"Commands: 'help', 'clear', 'memory', 'exit'",
        title=f"{bot_name} - Terminal Interface",
        border_style="blue" if bot_type == "personal" else "green"
    ))
    
    # Initialize actual bot instances
    from src.core.orchestration.bot_manager import BotManager
    
    bot_manager = BotManager()
    console.print(f"🤖 Initializing {bot_name}...")
    
    conversation_id = generate_conversation_id()
    
    while True:
        try:
            # Get user input
            user_input = await get_user_input(bot_type)
            
            if user_input is None:  # EOF or Ctrl+C
                break
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print(f"\n{bot_emoji} Goodbye! Have a great day! 👋")
                break
            elif user_input.lower() == "help":
                show_help(bot_type)
                continue
            elif user_input.lower() == "clear":
                console.clear()
                continue
            elif user_input.lower() == "memory":
                show_memory_info(conversation_id)
                continue
            
            # Process the message with the bot
            console.print(f"\n{bot_emoji} Processing your request...")
            
            try:
                # Process with actual bot using Ollama
                response = await bot_manager.process_message(user_input, bot_type, conversation_id)
            except Exception as e:
                console.print(f"⚠️  Error with agent processing: {e}")
                console.print("🔄 Falling back to direct Ollama response...")
                # Fallback to direct Ollama integration
                response = await get_ollama_response(user_input, bot_type)
            
            # Display the response
            display_response(response, bot_type)
            
        except KeyboardInterrupt:
            console.print(f"\n\n{bot_emoji} Session interrupted. Goodbye! 👋")
            break
        except Exception as e:
            console.print(f"\n❌ An error occurred: {str(e)}")


async def get_user_input(bot_type: str) -> Optional[str]:
    """Get user input asynchronously"""
    try:
        prompt_style = "🔐 You" if bot_type == "personal" else "🌐 You"
        return Prompt.ask(f"\n{prompt_style}")
    except (EOFError, KeyboardInterrupt):
        return None


async def get_ollama_response(user_input: str, bot_type: str) -> str:
    """
    Get a direct response from Ollama as fallback when agents fail
    """
    try:
        from src.services.ollama_service import ollama_service
        
        # Check if Ollama is available
        if not await ollama_service.is_available():
            return "❌ Ollama service is not available. Please run 'make start-ollama' to start the local AI service."
        
        # Create appropriate system prompt based on bot type
        if bot_type == "personal":
            system_prompt = """You are a personal AI assistant with access to the user's data and tools. 
            You can help with:
            - Email management and searching
            - Document analysis and organization  
            - Web browsing and research
            - System tasks and file management
            - Personal assistance with full context
            
            Be helpful, personalized, and proactive in offering assistance.
            If you need to access specific data or tools, mention what you would do if fully integrated."""
        else:
            system_prompt = """You are a public-facing AI assistant with limited access to general information only.
            You can only:
            - Provide publicly available information
            - Help with general questions and guidance
            - Maintain a professional and friendly tone
            
            You cannot:
            - Access private emails or documents
            - Execute system commands
            - Share confidential information
            
            Always be helpful while staying within appropriate boundaries."""
        
        # Get response from Ollama
        response = await ollama_service.generate_response(
            prompt=user_input,
            system_prompt=system_prompt
        )
        
        return response
        
    except Exception as e:
        return f"""❌ I'm experiencing technical difficulties right now.

Error: {str(e)}

To resolve this issue:
1. Check if Ollama is running: `make ollama-status`
2. Start Ollama if needed: `make start-ollama`
3. Pull the DeepSeek model: `make ollama-pull`

You can also try your question again in a moment."""


def display_response(response: str, bot_type: str):
    """Display the bot's response in a formatted way"""
    bot_emoji = "🔐" if bot_type == "personal" else "🌐"
    bot_name = "Personal Bot" if bot_type == "personal" else "Public Bot"
    border_style = "blue" if bot_type == "personal" else "green"
    
    # Convert to markdown for better formatting
    markdown_response = Markdown(response)
    
    console.print(Panel(
        markdown_response,
        title=f"{bot_emoji} {bot_name}",
        border_style=border_style,
        padding=(1, 2)
    ))


def show_help(bot_type: str):
    """Show help information"""
    bot_emoji = "🔐" if bot_type == "personal" else "🌐"
    
    if bot_type == "personal":
        help_text = """
**Personal Bot Commands:**

• **help** - Show this help message
• **clear** - Clear the terminal screen
• **memory** - Show conversation memory info
• **exit** - Quit the application

**What I can help with:**
• 📧 Email management (search, send, organize)
• 📚 Document search and analysis
• 🌐 Web browsing and research
• 💻 System tasks and file management
• 📊 Data analysis and reporting
• 💭 Personal assistance with full context

**Example queries:**
• "Check my emails from John about the project"
• "Find the latest performance report and summarize it"
• "Help me organize my desktop files"
• "Draft an email to the team about tomorrow's meeting"
"""
    else:
        help_text = """
**Public Bot Commands:**

• **help** - Show this help message
• **clear** - Clear the terminal screen  
• **memory** - Show conversation memory info
• **exit** - Quit the application

**What I can help with:**
• General information and questions
• Public professional information
• Technology discussions
• General assistance and guidance

**Limitations:**
• Cannot access private emails or documents
• Cannot perform system actions
• Cannot share confidential information
• Limited to publicly available data only

**Example queries:**
• "What does this person do professionally?"
• "What are their areas of expertise?"
• "Can you help with general technology questions?"
"""
    
    console.print(Panel(
        Markdown(help_text),
        title=f"{bot_emoji} Help",
        border_style="yellow"
    ))


def show_memory_info(conversation_id: str):
    """Show conversation memory information"""
    # TODO: Implement actual memory display
    console.print(Panel(
        f"**Conversation ID:** {conversation_id}\n\n"
        f"**Memory Status:** Active\n"
        f"**Exchanges:** Mock data - implementation pending\n"
        f"**Context Window:** Last 10 exchanges\n\n"
        f"*Note: Full memory implementation pending*",
        title="💭 Conversation Memory",
        border_style="cyan"
    ))


def generate_conversation_id() -> str:
    """Generate a simple conversation ID"""
    import uuid
    return str(uuid.uuid4())[:8]


if __name__ == "__main__":
    import sys
    bot_type = sys.argv[1] if len(sys.argv) > 1 else "personal"
    asyncio.run(run_terminal_interface(bot_type)) 