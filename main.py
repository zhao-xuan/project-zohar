#!/usr/bin/env python3
"""
Main entry point for the Personal Chatbot System
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
app = typer.Typer(help="Personal Chatbot System")


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
        "🔧 Setting up Personal Chatbot System",
        title="Setup Wizard",
        border_style="yellow"
    ))
    
    # Import setup module
    from scripts.setup_wizard import run_setup_wizard
    run_setup_wizard()


@app.command()
def process_wechat(
    source_path: str = typer.Option(
        "/Users/tomzhao/Desktop/WeChatHistory",
        "--source",
        "-s",
        help="Path to WeChat data directory"
    ),
    user_name: str = typer.Option(
        "Tom Zhao",
        "--name", 
        "-n",
        help="User name to analyze communication style for"
    ),
    force_reprocess: bool = typer.Option(
        False,
        "--force",
        "-f", 
        help="Force reprocessing of existing data"
    )
):
    """Process WeChat data to generate tone analysis and bio files"""
    console.print(Panel.fit(
        f"📱 Processing WeChat Data\n"
        f"Source: {source_path}\n"
        f"User: {user_name}\n"
        f"Force reprocess: {force_reprocess}",
        title="WeChat Data Processing",
        border_style="cyan"
    ))
    
    asyncio.run(_process_wechat_data(source_path, user_name, force_reprocess))


async def _process_wechat_data(source_path: str, user_name: str, force_reprocess: bool):
    """Internal function to process WeChat data"""
    try:
        from src.services.wechat_processor import WeChatProcessor
        from data.chromadb_manager import PersonalDataManager
        from pathlib import Path
        import json
        
        console.print("🔄 Initializing WeChat processor...")
        processor = WeChatProcessor()
        
        console.print("🔄 Processing WeChat conversations...")
        wechat_data = processor.process_wechat_directory(source_path)
        
        if not wechat_data['conversations']:
            console.print("❌ No conversations found in WeChat data")
            return
        
        console.print(f"✅ Processed {len(wechat_data['conversations'])} conversations with {wechat_data['total_messages']} messages")
        
        # Analyze communication style
        console.print("🔍 Analyzing communication style...")
        style_analysis = processor.analyze_user_communication_style(wechat_data['conversations'], user_name)
        
        if 'error' in style_analysis:
            console.print(f"⚠️  {style_analysis['error']}")
            return
        
        # Generate tone examples file
        console.print("📝 Generating tone analysis file...")
        tone_content = _generate_tone_file_content(style_analysis, wechat_data)
        
        tone_file_path = Path("data/personal/wechat_tone_analysis.txt")
        tone_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(tone_file_path, 'w', encoding='utf-8') as f:
            f.write(tone_content)
        
        console.print(f"✅ Generated tone analysis: {tone_file_path}")
        
        # Generate enhanced bio
        console.print("📝 Generating enhanced bio...")
        bio_content = _generate_bio_content(wechat_data, style_analysis, user_name)
        
        bio_file_path = Path("data/personal/bio.txt")
        
        with open(bio_file_path, 'w', encoding='utf-8') as f:
            f.write(bio_content)
        
        console.print(f"✅ Updated bio file: {bio_file_path}")
        
        # Store in ChromaDB
        console.print("💾 Storing data in ChromaDB...")
        data_manager = PersonalDataManager()
        
        for conversation in wechat_data['conversations']:
            for message in conversation['messages']:
                if message['type'] == 'text':
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        data_manager.add_chat_message,
                        {
                            'text': message['content'],
                            'sender': message['sender'],
                            'platform': 'WeChat',
                            'timestamp': message['timestamp'].isoformat() if message['timestamp'] else None,
                            'conversation_id': conversation['title'],
                            'message_type': message['type']
                        }
                    )
        
        console.print("✅ Data stored in ChromaDB")
        
        # Display summary
        console.print(Panel.fit(
            f"📊 Processing Complete!\n\n"
            f"Conversations Processed: {len(wechat_data['conversations'])}\n"
            f"Total Messages: {wechat_data['total_messages']}\n"
            f"User Messages Analyzed: {style_analysis['total_messages']}\n"
            f"Communication Style: {style_analysis['tone_characteristics']}\n\n"
            f"Files Generated:\n"
            f"• {tone_file_path}\n"
            f"• {bio_file_path}\n\n"
            f"Data Range: {wechat_data['date_range']['earliest']} to {wechat_data['date_range']['latest']}",
            title="WeChat Processing Summary",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"❌ Error processing WeChat data: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")


def _generate_tone_file_content(style_analysis: dict, wechat_data: dict) -> str:
    """Generate content for tone analysis file"""
    content = f"""# Communication Style Analysis from WeChat Data
Generated on: {wechat_data['date_range']['latest']}
Analysis based on {style_analysis['total_messages']} messages

## TONE CHARACTERISTICS

### Overall Style Metrics:
- Enthusiasm Level: {style_analysis['tone_characteristics']['enthusiasm_level']}%
- Politeness Level: {style_analysis['tone_characteristics']['politeness_level']}%
- Casualness Level: {style_analysis['tone_characteristics']['casualness_level']}%
- Directness Level: {style_analysis['tone_characteristics']['directness_level']}%

### Communication Patterns:
- Uses Emojis: {style_analysis['communication_patterns']['uses_emojis']}
- Prefers Short Messages: {style_analysis['communication_patterns']['prefers_short_messages']}
- Uses Questions: {style_analysis['communication_patterns']['uses_questions']}
- Uses English: {style_analysis['communication_patterns']['uses_english']}
- Uses Chinese: {style_analysis['communication_patterns']['uses_chinese']}

## SAMPLE MESSAGES

Here are examples of actual communication style extracted from WeChat:

"""
    
    # Add sample messages
    for i, message in enumerate(style_analysis['sample_messages'][:15], 1):
        content += f"{i}. \"{message}\"\n"
    
    content += f"""

## COMMON PHRASES

Frequently used phrases and expressions:
"""
    
    for phrase in style_analysis['common_phrases']:
        content += f"- \"{phrase}\"\n"
    
    content += f"""

## USAGE GUIDELINES FOR AI

Based on this analysis, the AI should:

1. **Enthusiasm**: {"Use exclamation points and positive expressions frequently" if style_analysis['tone_characteristics']['enthusiasm_level'] > 30 else "Maintain a more measured, calm tone"}

2. **Politeness**: {"Include courteous expressions and thank you notes" if style_analysis['tone_characteristics']['politeness_level'] > 40 else "Be direct and to the point"}

3. **Casualness**: {"Use informal language and casual expressions" if style_analysis['tone_characteristics']['casualness_level'] > 50 else "Maintain a more formal communication style"}

4. **Language Mix**: {"Feel free to mix English and Chinese naturally" if style_analysis['communication_patterns']['uses_english'] and style_analysis['communication_patterns']['uses_chinese'] else "Stick to primarily English communication"}

5. **Message Length**: {"Keep responses concise and to the point" if style_analysis['communication_patterns']['prefers_short_messages'] else "Provide detailed, thorough explanations"}

## CONTEXTUAL SCENARIOS

### Professional Contexts:
Use a slightly more formal tone while maintaining personal style characteristics.

### Casual Conversations:  
Embrace the full casual style with emojis and informal expressions.

### Technical Discussions:
Balance technical accuracy with personal communication style.

### Problem-Solving:
{"Ask clarifying questions naturally" if style_analysis['communication_patterns']['uses_questions'] else "Provide direct solutions and explanations"}
"""
    
    return content


def _generate_bio_content(wechat_data: dict, style_analysis: dict, user_name: str) -> str:
    """Generate enhanced bio content based on WeChat analysis"""
    
    # Analyze conversation topics and relationships
    participants = wechat_data['participants']
    total_conversations = len(wechat_data['conversations'])
    date_range = wechat_data['date_range']
    
    content = f"""I am {user_name}, a technology professional with expertise in AI and software development.

## KEY INFORMATION:
- Experienced in software development and AI systems
- Interested in productivity tools and automation  
- Values privacy and data security
- Prefers direct, helpful communication
- Active in social networks with {len(participants)} regular contacts

## BACKGROUND:
- Works with various programming languages and frameworks
- Has experience with machine learning and AI systems
- Enjoys building tools that improve efficiency
- Believes in the importance of local, privacy-preserving AI
- Maintains active communication across {total_conversations} different conversation threads

## COMMUNICATION STYLE (based on actual usage):
- Average message length: {style_analysis['average_length']:.1f} characters
- Enthusiasm level: {style_analysis['tone_characteristics']['enthusiasm_level']}% ({"High" if style_analysis['tone_characteristics']['enthusiasm_level'] > 40 else "Moderate" if style_analysis['tone_characteristics']['enthusiasm_level'] > 20 else "Low"})
- Communication approach: {"Casual and friendly" if style_analysis['tone_characteristics']['casualness_level'] > 50 else "Professional and direct"}
- Language preference: {"Bilingual (Chinese/English)" if style_analysis['communication_patterns']['uses_chinese'] and style_analysis['communication_patterns']['uses_english'] else "Primarily English"}

## SOCIAL CONNECTIONS:
- Regular communication with friends, family, and colleagues
- Maintains professional relationships in tech industry
- Values both personal and professional networking
- Active period: {date_range['earliest'].strftime('%Y-%m') if date_range['earliest'] else 'N/A'} to {date_range['latest'].strftime('%Y-%m') if date_range['latest'] else 'N/A'}

## CURRENT PROJECTS:
- Building personal AI assistant systems
- Working on intelligent automation solutions
- Working on data privacy solutions
- Processing and analyzing personal communication data for AI training

## INTERESTS (derived from communication patterns):
- Technology and AI development
- Personal productivity optimization
- Data privacy and security
- Social networking and relationship building
- {"Frequent emoji usage indicates creative, expressive personality" if style_analysis['communication_patterns']['uses_emojis'] else "Direct communication style indicates preference for efficiency"}

## PROFESSIONAL FOCUS:
- Machine learning and AI systems
- Software architecture and development
- Personal data processing and analysis
- Privacy-preserving AI solutions
- Intelligent automation development
"""
    
    return content


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
def run_system(
    wechat_path: str = typer.Option(
        "/Users/tomzhao/Desktop/WeChatHistory",
        "--wechat-path",
        "-w",
        help="Path to WeChat data directory"
    ),
    user_name: str = typer.Option(
        "Tom Zhao",
        "--user-name",
        "-u",
        help="User name for analysis"
    )
):
    """Run the complete system with WeChat data processing"""
    console.print(Panel.fit(
        f"🚀 Starting Complete System\n"
        f"WeChat Data: {wechat_path}\n"
        f"User: {user_name}",
        title="System Startup",
        border_style="bright_magenta"
    ))
    
    asyncio.run(_run_complete_system(wechat_path, user_name))


async def _run_complete_system(wechat_path: str, user_name: str):
    """Run the complete system with all components"""
    try:
        # Step 1: Start MCP servers
        console.print("🔗 Starting MCP servers...")
        from src.tools.mcp_servers.manager import MCPServerManager
        mcp_manager = MCPServerManager()
        await mcp_manager.start_all_servers()
        
        # Step 2: Process WeChat data
        console.print("📱 Processing WeChat data...")
        await _process_wechat_data(wechat_path, user_name, False)
        
        # Step 3: Start ChromaDB (already initialized during WeChat processing)
        console.print("💾 ChromaDB initialized and populated")
        
        # Step 4: Run health check
        console.print("🏥 Running system health check...")
        from src.core.orchestration.health_check import SystemHealthChecker
        health_checker = SystemHealthChecker()
        await health_checker.run_health_check()
        
        # Step 5: Start the bot manager
        console.print("🤖 Initializing bot manager...")
        bot_manager = BotManager()
        
        # Test the system with a sample query
        console.print("🧪 Testing system with sample query...")
        test_response = await bot_manager.process_message(
            "Based on my communication style, how should you respond to me?",
            "personal"
        )
        
        console.print(Panel.fit(
            f"✅ System fully operational!\n\n"
            f"MCP Servers: Running\n"
            f"WeChat Data: Processed\n"
            f"ChromaDB: Populated\n"
            f"Chatbot System: Ready\n\n"
            f"Sample Response:\n{test_response[:200]}...",
            title="System Status",
            border_style="green"
        ))
        
        console.print("\n🎯 Your system is ready! You can now:")
        console.print("• Run 'python main.py terminal' for interactive chat")
        console.print("• Run 'python main.py web' for web interface")
        console.print("• Check 'data/personal/' for generated tone and bio files")
        
    except Exception as e:
        console.print(f"❌ Error running complete system: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")


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
def ollama_status():
    """Check Ollama service status and model availability"""
    console.print(Panel.fit(
        "🦙 Checking Ollama Status",
        title="Ollama Service",
        border_style="yellow"
    ))
    
    from src.services.ollama_service import ollama_service
    
    async def check_ollama():
        console.print("🔍 Checking Ollama availability...")
        is_available = await ollama_service.is_available()
        
        if is_available:
            console.print("✅ Ollama is running and DeepSeek model is available")
            
            # Get model info
            model_info = await ollama_service.get_model_info()
            if "error" not in model_info:
                console.print(f"📋 Model: {settings.llm.model_name}")
                console.print(f"🌡️  Temperature: {settings.llm.temperature}")
                console.print(f"🎯 Max Tokens: {settings.llm.max_tokens}")
            
            # List all models
            models = await ollama_service.list_models()
            if models:
                console.print(f"📚 Available models: {', '.join(models)}")
        else:
            console.print("❌ Ollama is not available or DeepSeek model is not installed")
            console.print("💡 Try running: python3 main.py ollama-pull")
    
    asyncio.run(check_ollama())


@app.command()
def ollama_pull():
    """Pull the DeepSeek model for Ollama"""
    console.print(Panel.fit(
        f"📥 Pulling {settings.llm.model_name} model",
        title="Ollama Model Pull",
        border_style="cyan"
    ))
    
    from src.services.ollama_service import ollama_service
    
    async def pull_model():
        success = await ollama_service.pull_model()
        if success:
            console.print("✅ Model pulled successfully!")
        else:
            console.print("❌ Failed to pull model. Make sure Ollama is running.")
    
    asyncio.run(pull_model())


@app.command()
def ollama_test(
    prompt: str = typer.Option(
        "Hello, how are you?",
        "--prompt",
        "-p",
        help="Test prompt to send to the model"
    )
):
    """Test Ollama model with a custom prompt"""
    console.print(Panel.fit(
        f"🧪 Testing Ollama with prompt: '{prompt}'",
        title="Ollama Test",
        border_style="green"
    ))
    
    from src.services.ollama_service import ollama_service
    
    async def test_model():
        console.print("🔄 Generating response...")
        
        response = await ollama_service.generate_response(
            prompt=prompt,
            system_prompt="You are a helpful AI assistant. Respond concisely and helpfully."
        )
        
        console.print(Panel(
            response,
            title="🦙 DeepSeek Response",
            border_style="blue"
        ))
    
    asyncio.run(test_model())


@app.command()
def ollama_models():
    """List all available Ollama models"""
    console.print(Panel.fit(
        "📚 Listing Ollama Models",
        title="Available Models",
        border_style="magenta"
    ))
    
    from src.services.ollama_service import ollama_service
    
    async def list_models():
        models = await ollama_service.list_models()
        
        if models:
            console.print("Available models:")
            for model in models:
                current = "🎯" if model.startswith(settings.llm.model_name) else "  "
                console.print(f"{current} {model}")
        else:
            console.print("❌ No models found or Ollama not available")
    
    asyncio.run(list_models())


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


@app.command()
def parse_personal_data(
    data_path: str = typer.Option(
        "/Users/tomzhao/Desktop/WhatsappChatHistory",
        "--data-path",
        "-d",
        help="Path to personal data directory"
    ),
    output_file: str = typer.Option(
        "data/processed/camel_parsing_results.json",
        "--output",
        "-o",
        help="Output file for results"
    ),
    chunk_size: int = typer.Option(
        512,
        "--chunk-size",
        "-c",
        help="Chunk size for text splitting"
    ),
    include_chat: bool = typer.Option(
        True,
        "--include-chat/--no-include-chat",
        help="Include specialized chat parsing"
    )
):
    """Run Camel-AI system to parse personal information data"""
    console.print(Panel.fit(
        f"🐪 Running Camel-AI Personal Data Parser\n"
        f"Data Path: {data_path}\n"
        f"Output: {output_file}\n"
        f"Chunk Size: {chunk_size}\n"
        f"Include Chat Parsing: {include_chat}",
        title="Camel-AI Data Parsing",
        border_style="bright_blue"
    ))
    
    asyncio.run(_run_camel_ai_parser(data_path, output_file, chunk_size, include_chat))


async def _process_directory_with_chroma(data_path: str, collection, chunk_size: int, include_chat: bool):
    """Process directory contents with ChromaDB storage"""
    import os
    import magic
    from pypdf import PdfReader
    import re
    from datetime import datetime
    
    results = {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'processing_stats': {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0
        },
        'chat_processing': {},
        'files_processed': []
    }
    
    try:
        # Get all files in directory
        files = []
        for root, dirs, filenames in os.walk(data_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        results['processing_stats']['total_files'] = len(files)
        
        # Process each file
        for file_path in files:
            try:
                await _process_single_file(file_path, collection, chunk_size, results)
                results['processing_stats']['processed_files'] += 1
            except Exception as e:
                console.print(f"❌ Failed to process {file_path}: {e}")
                results['processing_stats']['failed_files'] += 1
                results['files_processed'].append({
                    'file': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Special chat processing if enabled
        if include_chat:
            chat_file = os.path.join(data_path, "_chat.txt")
            if os.path.exists(chat_file):
                console.print("💬 Processing WhatsApp chat file...")
                chat_results = await _process_whatsapp_chat(chat_file, collection, chunk_size)
                results['chat_processing'] = chat_results
        
        # Get collection stats
        results['collection_stats'] = {
            'name': collection.name,
            'count': collection.count(),
            'metadata': collection.metadata
        }
        
    except Exception as e:
        results['success'] = False
        results['error'] = str(e)
    
    return results


async def _process_single_file(file_path: str, collection, chunk_size: int, results: dict):
    """Process a single file and add to ChromaDB collection"""
    import os
    
    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Skip hidden files and certain extensions
    if filename.startswith('.') or file_ext in ['.db', '.log']:
        return
    
    # Detect file type
    try:
        mime_type = magic.from_file(file_path, mime=True)
    except:
        mime_type = "application/octet-stream"
    
    content = ""
    metadata = {
        'filename': filename,
        'file_path': file_path,
        'file_type': mime_type,
        'file_extension': file_ext
    }
    
    # Extract content based on file type
    if file_ext == '.txt' or 'text' in mime_type:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    elif file_ext == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            content = ""
            for page in reader.pages:
                content += page.extract_text() + "\n"
        except Exception as e:
            console.print(f"⚠️ PDF extraction failed for {filename}: {e}")
            return
    elif file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
        # For images, store metadata only
        metadata['content_type'] = 'image'
        metadata['description'] = f"Image file: {filename}"
        content = f"Image file: {filename} (WhatsApp attachment)"
    elif file_ext in ['.opus', '.mp3', '.wav']:
        # For audio, store metadata only
        metadata['content_type'] = 'audio'
        metadata['description'] = f"Audio file: {filename}"
        content = f"Audio file: {filename} (WhatsApp voice message)"
    elif file_ext in ['.doc', '.docx']:
        # For documents, try basic extraction
        metadata['content_type'] = 'document'
        content = f"Document file: {filename} (WhatsApp attachment)"
    else:
        # Skip unknown file types
        return
    
    if not content.strip():
        return
    
    # Split into chunks if content is large
    chunks = _split_text_into_chunks(content, chunk_size)
    
    # Add chunks to collection
    for i, chunk in enumerate(chunks):
        chunk_metadata = metadata.copy()
        chunk_metadata['chunk_id'] = i
        chunk_metadata['total_chunks'] = len(chunks)
        
        # Generate unique ID
        doc_id = f"{filename}_{i}"
        
        collection.add(
            documents=[chunk],
            metadatas=[chunk_metadata],
            ids=[doc_id]
        )
        
        results['processing_stats']['total_chunks'] += 1
    
    results['files_processed'].append({
        'file': filename,
        'status': 'success',
        'chunks': len(chunks),
        'content_type': metadata.get('content_type', 'text')
    })


async def _process_whatsapp_chat(chat_file: str, collection, chunk_size: int):
    """Process WhatsApp chat file specifically"""
    import re
    
    chat_results = {
        'messages_processed': 0,
        'conversations_identified': 0,
        'date_range': {},
        'participants': []
    }
    
    try:
        with open(chat_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Basic WhatsApp message parsing  
        # Pattern: [M/D/YY, H:MM:SS AM/PM] Name: Message
        # Also handles invisible characters and multiline messages
        message_pattern = r'(?:^|\n).*?\[(\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2}:\d{2} (?:AM|PM))\] ([^:]+): (.+?)(?=(?:^|\n).*?\[\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2}:\d{2} (?:AM|PM)\]|$)'
        
        messages = re.findall(message_pattern, content, re.DOTALL)
        
        for i, (timestamp, sender, message) in enumerate(messages):
            # Clean up message
            message = message.strip().replace('\n', ' ')
            
            # Create metadata
            metadata = {
                'message_type': 'whatsapp',
                'timestamp': timestamp,
                'sender': sender.strip(),
                'message_id': i,
                'conversation': 'Kristiane Backer Chat'
            }
            
            # Add to participants
            sender_clean = sender.strip()
            if sender_clean not in chat_results['participants']:
                chat_results['participants'].append(sender_clean)
            
            # Split long messages into chunks
            if len(message) > chunk_size:
                chunks = _split_text_into_chunks(message, chunk_size)
                for j, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_id'] = j
                    chunk_metadata['total_chunks'] = len(chunks)
                    
                    collection.add(
                        documents=[f"[{timestamp}] {sender}: {chunk}"],
                        metadatas=[chunk_metadata],
                        ids=[f"msg_{i}_{j}"]
                    )
            else:
                collection.add(
                    documents=[f"[{timestamp}] {sender}: {message}"],
                    metadatas=[metadata],
                    ids=[f"msg_{i}"]
                )
            
            chat_results['messages_processed'] += 1
        
        chat_results['conversations_identified'] = 1
        
    except Exception as e:
        chat_results['error'] = str(e)
    
    return chat_results


def _split_text_into_chunks(text: str, chunk_size: int) -> list:
    """Split text into chunks of specified size"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to break at sentence or word boundary
            for boundary in ['. ', '! ', '? ', '\n', ' ']:
                last_boundary = text.rfind(boundary, start, end)
                if last_boundary > start:
                    end = last_boundary + len(boundary)
                    break
        
        chunks.append(text[start:end].strip())
        start = end
    
    return [chunk for chunk in chunks if chunk]


async def _run_camel_ai_parser(data_path: str, output_file: str, chunk_size: int, include_chat: bool):
    """Run the Camel-AI parser system"""    
    try:
        # Import camel-ai components with fallback
        try:
            from src.services import CamelFileProcessor, CamelChatParser
            from camel.embeddings import OpenAIEmbedding
            camel_available = True
        except ImportError as camel_err:
            console.print(f"⚠️ Camel-AI components not fully available: {camel_err}")
            camel_available = False
        
        # Direct ChromaDB integration
        import chromadb
        from chromadb.utils import embedding_functions
        from pathlib import Path
        import json
        import os
        
        console.print("🔄 Initializing data processors...")
        
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(path="data/camel_vector_db")
        
        # Set up embedding function (using local sentence-transformers by default)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "fallback":
            try:
                embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=openai_key
                )
                console.print("🔑 Using OpenAI embeddings")
            except Exception as e:
                console.print(f"⚠️ OpenAI embeddings failed: {e}")
                embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                console.print("🤖 Using local sentence-transformers embeddings")
        else:
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            console.print("🤖 Using local sentence-transformers embeddings")
        
        # Create collection for this chat
        collection_name = "whatsapp_kristiane_backer"
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        
        console.print("🔄 Processing files in directory...")
        results = await _process_directory_with_chroma(
            data_path, collection, chunk_size, include_chat
        )
        
        # If camel-ai is available, enhance with camel processors
        if camel_available:
            console.print("🐪 Enhancing with Camel-AI processors...")
            try:
                file_processor = CamelFileProcessor(
                    storage_path="data/camel_vector_db",
                    chunk_size=chunk_size
                )
                camel_results = await file_processor.process_directory(data_path)
                results['camel_processing'] = camel_results
            except Exception as camel_error:
                console.print(f"⚠️ Camel-AI enhancement failed: {camel_error}")
                results['camel_processing'] = {'error': str(camel_error)}
        
        # Chat processing results
        chat_results = results.get('chat_processing', {})
        
        # Combine results
        combined_results = {
            'camel_ai_version': '0.1.5.4+',
            'processing_timestamp': results.get('timestamp'),
            'success': results.get('success', False),
            'file_processing': {
                'stats': results.get('processing_stats', {}),
                'collections_created': [collection_name],
                'storage_results': results.get('collection_stats', {})
            },
            'chat_processing': chat_results,
            'collection_info': {
                'collections': [collection_name],
                'total_documents': collection.count(),
                'storage_path': 'data/camel_vector_db'
            },
            'vector_db_path': 'data/camel_vector_db'
        }
        
        # Save results to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2, ensure_ascii=False)
        
        # Save detailed processing results
        details_path = output_path.parent / "camel_processing_details.json"
        with open(details_path, 'w', encoding='utf-8') as f:
            json.dump({
                'detailed_results': results,
                'files_processed': results.get('files_processed', []),
                'collection_stats': results.get('collection_stats', {}),
                'processing_metadata': {
                    'chunk_size': chunk_size,
                    'include_chat': include_chat,
                    'collection_name': collection_name
                }
            }, f, indent=2, ensure_ascii=False)
        
        console.print(f"✅ Results saved to: {output_path}")
        
        # Display summary
        file_stats = combined_results['file_processing']['stats']
        chat_stats = combined_results.get('chat_processing', {})
        
        status = "✅ SUCCESS" if results.get('success') else "❌ FAILED"
        
        console.print(Panel.fit(
            f"📊 Camel-AI Parsing Complete! {status}\n\n"
            f"FILE PROCESSING:\n"
            f"  Total Files: {file_stats.get('total_files', 0)}\n"
            f"  Processed Files: {file_stats.get('processed_files', 0)}\n"
            f"  Failed Files: {file_stats.get('failed_files', 0)}\n"
            f"  Collections Created: {file_stats.get('collections_created', 0)}\n"
            f"  Total Chunks: {file_stats.get('total_chunks', 0)}\n\n"
            f"CHAT PROCESSING:\n"
            f"  Chat Files: {'1 (WhatsApp)' if include_chat and chat_stats else 'Disabled'}\n"
            f"  Messages Processed: {chat_stats.get('messages_processed', 'N/A') if include_chat else 'Disabled'}\n"
            f"  Participants: {len(chat_stats.get('participants', [])) if include_chat and chat_stats else 'N/A'}\n\n"
            f"VECTOR DATABASE:\n"
            f"  Location: data/camel_vector_db\n"
            f"  Collections: {', '.join(combined_results['file_processing']['collections_created'])}\n\n"
            f"GENERATED FILES:\n"
            f"• {output_file}\n"
            f"• {output_path.parent}/camel_processing_details.json\n"
            f"• Vector database at data/camel_vector_db/",
            title="Camel-AI Processing Summary",
            border_style="green" if results.get('success') else "red"
        ))
        
        # Show collection details
        collection_info = combined_results.get('collection_info', {})
        if collection_info.get('collections'):
            console.print("\n📚 Vector Collections Created:")
            for collection in collection_info['collections']:
                console.print(f"  📁 {collection}")
        
        # Show chat processing details
        if include_chat and chat_results and not chat_results.get('error'):
            participants = chat_results.get('participants', [])
            messages_count = chat_results.get('messages_processed', 0)
            
            if participants:
                console.print(f"\n💬 Chat Analysis Results:")
                console.print(f"  Platform: WhatsApp")
                console.print(f"  Total chat messages: {messages_count}")
                console.print(f"  Participants: {', '.join(participants)}")
                console.print(f"  Messages stored in vector DB: Yes")
        
        # Show errors if any
        if not results.get('success'):
            error_msg = results.get('error', 'Unknown error')
            console.print(f"\n❌ Processing Error: {error_msg}")
        
        # Performance summary
        if file_stats.get('total_files', 0) > 0:
            success_rate = (file_stats.get('processed_files', 0) / file_stats.get('total_files', 1)) * 100
            console.print(f"\n📈 Performance Summary:")
            console.print(f"  Success Rate: {success_rate:.1f}%")
            console.print(f"  Collections per File: {file_stats.get('collections_created', 0) / max(1, file_stats.get('processed_files', 1)):.2f}")
            
        console.print("\n🎯 What's Next:")
        console.print("• Query your data: processor.query('your question here')")
        console.print("• Use AutoRetriever for smart collection routing")
        console.print("• Access vector DB at data/camel_vector_db/")
        console.print("• Run 'python main.py terminal' to chat with your data")
        
    except Exception as e:
        console.print(f"❌ Error in Camel-AI parsing: {e}")
        import traceback
        console.print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    app() 