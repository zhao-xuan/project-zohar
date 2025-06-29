# Personal Chatbot System

A sophisticated AI chatbot system that creates two specialized assistants: a **Personal Bot** with full access to your private data and tools, and a **Public Bot** for general interactions. Both bots use local LLM hosting and Retrieval-Augmented Generation (RAG) to provide personalized responses in your unique communication style.

## 🎯 Project Overview

This system enables you to:

- **Personal Bot**: Access all your information (emails, files, chat history) and perform actions (sending emails, running commands, checking repositories) on your behalf
- **Public Bot**: Provide a restricted version for general use that only knows basic public information about you and cannot access sensitive data or dangerous actions
- **Tone Mimicking**: Both bots respond in your personal communication style based on your chat history and examples
- **Local Privacy**: Everything runs on your Mac Studio, ensuring complete data privacy and control
- **Intelligent Processing**: Uses advanced file processing and retrieval for sophisticated responses
- **Tool Integration**: Seamless integration with email, web browsing, and system commands via MCP (Model Context Protocol)

## 🏗️ System Architecture

### Core Components

1. **Local Large Language Model (LLM)**
   - DeepSeek model hosted via Ollama
   - Complete privacy with no cloud dependencies
   - Optimized for Apple Silicon (Mac Studio)

2. **Retrieval-Augmented Generation (RAG)**
   - ChromaDB vector database for personal data storage
   - Semantic search across emails, documents, and files
   - Real-time information retrieval during conversations

3. **Advanced File Processing (CAMEL Framework)**
   - **Multimodal Processing**: Handles text, images, audio, and documents
   - **Dynamic Schema Generation**: Auto-creates optimized vector database schemas
   - **Intelligent Chunking**: Smart content segmentation for better retrieval
   - **Specialized Chat Parsing**: Extracts structured data from chat logs

4. **Model Context Protocol (MCP) Integration**
   - Email tools (Gmail, Outlook, QQ Mail)
   - Web browsing and repository checking
   - System command execution (with safety controls)
   - Extensible plugin architecture

5. **Dual Interface System**
   - Web-based chat interface
   - Terminal command-line interface
   - Real-time conversation with context memory

## 🚀 Quick Start

### Prerequisites

- macOS (Mac Studio recommended)
- Python 3.8+
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd project-zohar
```

2. **Run the setup wizard:**
```bash
python -m pip install -r requirements.txt
python main.py setup
```

The setup wizard will:
- Check system requirements
- Install Ollama and DeepSeek model
- Create configuration files
- Set up directory structure
- Guide you through persona customization

3. **Configure your environment:**
```bash
cp config.env.example .env
# Edit .env with your settings
```

4. **Index your personal data:**
```bash
# Index documents
python main.py index-data --source ~/Documents --type documents

# Index emails (after email setup)
python main.py index-data --source email --type email
```

5. **Start the system:**
```bash
# Terminal interface
python main.py terminal --type personal

# Web interface
python main.py web --type both

# Start MCP servers (in separate terminal)
python main.py start-mcp-servers
```

## 📚 Usage Examples

### Terminal Interface
```bash
# Start personal bot in terminal
python main.py terminal --type personal

# Start public bot in terminal
python main.py terminal --type public
```

### Web Interface
```bash
# Start both bots (personal on :5000, public on :5001)
python main.py web --type both

# Start only personal bot
python main.py web --type personal
```

### Data Management
```bash
# Index new documents
python main.py index-data --source /path/to/new/docs

# Reindex all data
python main.py index-data --force

# Check system status
python main.py status
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# LLM Settings
LLM_MODEL_NAME=deepseek
OLLAMA_HOST=http://localhost:11434

# Bot Configuration
PERSONAL_BOT_PORT=5000
PUBLIC_BOT_PORT=5001
ENABLE_PUBLIC_BOT=true

# Email Integration
GMAIL_CREDENTIALS_PATH=./data/credentials/gmail_credentials.json
QQ_EMAIL=your-email@qq.com

# Security
MAX_FILE_SIZE_MB=10
RATE_LIMIT_PER_MINUTE=60
```

### Persona Customization

1. **Personal Bio** (`data/personal/bio.txt`):
   - Your background, expertise, and personal information
   - Used by the personal bot for context

2. **Public Bio** (`data/public/public_bio.txt`):
   - Public-facing information only
   - Used by the public bot

3. **Communication Style** (`data/personal/tone_examples.txt`):
   - Examples of your writing style
   - Used to train both bots to mimic your tone

## 🛠️ Email Integration

### Gmail Setup
1. Enable Gmail API in Google Cloud Console
2. Download credentials to `data/credentials/gmail_credentials.json`
3. Run first-time authentication

### QQ Mail Setup
1. Enable IMAP in QQ Mail settings
2. Generate an app password
3. Add credentials to `.env`

### Outlook Setup
1. Register app in Azure AD
2. Get client ID and secret
3. Configure OAuth2 flow

## 🔒 Security Features

### Personal Bot Security
- **Local-only access**: Never exposed to internet
- **Action confirmation**: Confirms before sending emails or running commands
- **Data encryption**: Sensitive data stored securely
- **Access logging**: All actions logged for audit

### Public Bot Security
- **Information restriction**: Only accesses public bio data
- **No tool access**: Cannot send emails or execute commands
- **Rate limiting**: Prevents abuse
- **Content filtering**: Blocks attempts to access private information

## 📁 Project Structure

```
project-zohar/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── config.env.example         # Environment configuration template
├── src/                        # Source code
│   ├── core/                   # Core chatbot logic
│   │   ├── agents/             # Personal and public agents
│   │   ├── orchestration/      # Multi-agent coordination
│   │   └── memory/            # Conversation memory
│   ├── rag/                   # Retrieval-Augmented Generation
│   │   ├── embeddings/        # Text embedding processing
│   │   ├── retrieval/         # Data retrieval logic
│   │   └── storage/           # Vector database management
│   ├── tools/                 # External tool integration
│   │   ├── mcp_servers/       # MCP server implementations
│   │   ├── email/             # Email tool integration
│   │   ├── browser/           # Web browsing tools
│   │   └── system/            # System command tools
│   ├── ui/                    # User interfaces
│   │   ├── web/               # Web-based chat interface
│   │   └── terminal/          # Command-line interface
│   └── config/                # Configuration management
├── data/                      # Data storage
│   ├── personal/              # Private data and persona
│   ├── public/                # Public information
│   ├── processed/             # Processed data and databases
│   └── credentials/           # API keys and credentials
├── scripts/                   # Setup and utility scripts
├── tests/                     # Unit and integration tests
├── docs/                      # Documentation
└── examples/                  # Usage examples
```

## 🔄 Processing Flow

1. **User Input**: Message received via web or terminal interface
2. **Intent Analysis**: System analyzes and understands the request
3. **Data Retrieval**: RAG system searches for relevant personal data using vector similarity
4. **Tool Coordination**: MCP client prepares necessary tools and services
5. **Response Processing**: System processes data and generates appropriate response
6. **Response Generation**: Final response generated in user's communication style
7. **Memory Update**: Conversation context saved for future reference

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests  
python -m pytest tests/integration/

# Test specific component
python -m pytest tests/unit/test_personal_agent.py

# Health check
python main.py status
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Ollama connection failed:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

**DeepSeek model not found:**
```bash
# Download the model
ollama pull deepseek
```

**Email authentication issues:**
- Check credentials file permissions
- Verify API keys and OAuth setup
- Review email provider security settings

**Vector database errors:**
- Check data directory permissions
- Reindex data: `python main.py index-data --force`

### Getting Help

- Check the [documentation](docs/) folder for detailed guides
- Review [examples](examples/) for common use cases
- Open an issue for bug reports or feature requests

## 🔮 Future Enhancements

- Voice interface integration
- Mobile app companion
- Calendar and task management integration
- Advanced fine-tuning for better tone mimicking
- Additional email providers and tools
- Performance optimizations for larger datasets
- Multi-language support

---

**Built with ❤️ for privacy-conscious AI enthusiasts**