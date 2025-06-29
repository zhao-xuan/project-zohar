# Personal Chatbot System Makefile

.PHONY: help install setup start start-personal start-public start-web start-mcp test clean lint format check-health index-data

# Default target
help:
	@echo "🤖 Personal Chatbot System"
	@echo ""
	@echo "🚀 Setup & Installation:"
	@echo "  install        Install Python dependencies"
	@echo "  setup          Run interactive setup wizard"
	@echo "  quickstart     Complete setup and indexing"
	@echo ""
	@echo "🤖 Bot Services:"
	@echo "  start          Start personal bot in terminal"
	@echo "  start-public   Start public bot in terminal"
	@echo "  start-web      Start web interface for both bots"
	@echo "  start-mcp      Start MCP servers"
	@echo ""
	@echo "📧 MCP Email Server:"
	@echo "  mcp-email-setup    Setup MCP email server with providers"
	@echo "  mcp-email-test     Test MCP email server functionality"
	@echo "  mcp-email-demo     Run email management demo"
	@echo "  mcp-email-status   Check email provider authentication"
	@echo ""
	@echo "🦙 Ollama (Local AI):"
	@echo "  start-ollama   Start Ollama service"
	@echo "  stop-ollama    Stop Ollama service"
	@echo "  ollama-status  Check Ollama status and model availability"
	@echo "  ollama-pull    Pull DeepSeek model"
	@echo "  ollama-test    Test Ollama with sample prompt"
	@echo "  ollama-models  List all available models"
	@echo "  ollama-setup   Complete Ollama setup (start + pull)"
	@echo ""
	@echo "🔧 Development:"
	@echo "  test           Run all tests"
	@echo "  lint           Run code linting"
	@echo "  format         Format code with black"
	@echo "  check-health   Check system health"
	@echo "  index-data     Index personal data for RAG"
	@echo "  clean          Clean up temporary files"

# Installation and setup
install:
	@echo "📦 Installing dependencies..."
	python3 -m pip install --upgrade pip
	pip3 install -r requirements.txt

setup: install
	@echo "🔧 Running setup wizard..."
	python3 main.py setup

# Start services
start:
	@echo "🔐 Starting personal bot in terminal..."
	python3 main.py terminal --type personal

start-public:
	@echo "🌐 Starting public bot in terminal..."
	python3 main.py terminal --type public

start-web:
	@echo "🌐 Starting web interface..."
	python3 main.py web --type both

start-mcp:
	@echo "🔗 Starting MCP servers..."
	python3 main.py start-mcp-servers

# MCP Email Server
mcp-email-setup:
	@echo "📧 Setting up MCP Email Server..."
	python3 scripts/setup_mcp_email.py

mcp-email-test:
	@echo "🧪 Testing MCP Email Server..."
	python3 -c "import asyncio; from src.services.mcp_email_server import main; asyncio.run(main())"

mcp-email-demo:
	@echo "🎬 Running MCP Email Demo..."
	python3 examples/mcp_email_demo.py

mcp-email-status:
	@echo "📊 Checking email provider status..."
	python3 -c "import asyncio; import sys; sys.path.insert(0, 'src'); from services.mcp_email_server import MCPEmailServer; server = MCPEmailServer(); print(asyncio.run(server.authenticate_all()))"

# Ollama management
start-ollama:
	@echo "🦙 Starting Ollama service..."
	@if ! command -v ollama > /dev/null 2>&1; then \
		echo "❌ Ollama not found. Please install Ollama first."; \
		echo "💡 Visit: https://ollama.ai/download"; \
		exit 1; \
	fi
	@if ! pgrep -f ollama > /dev/null; then \
		echo "🚀 Starting Ollama daemon..."; \
		ollama serve & \
		sleep 3; \
	else \
		echo "✅ Ollama is already running"; \
	fi

stop-ollama:
	@echo "🛑 Stopping Ollama service..."
	@pkill -f "ollama serve" || echo "⚠️  Ollama was not running"

ollama-status:
	@echo "📊 Checking Ollama status..."
	python3 main.py ollama-status

ollama-pull:
	@echo "📥 Pulling DeepSeek model..."
	python3 main.py ollama-pull

ollama-test:
	@echo "🧪 Testing Ollama with DeepSeek..."
	python3 main.py ollama-test

ollama-models:
	@echo "📚 Listing available models..."
	python3 main.py ollama-models

ollama-setup: start-ollama ollama-pull
	@echo "✅ Ollama setup complete!"

# Development
test:
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ -v

lint:
	@echo "🔍 Running linting..."
	flake8 src/ tests/ main.py
	mypy src/ main.py

format:
	@echo "🎨 Formatting code..."
	black src/ tests/ main.py
	isort src/ tests/ main.py

# Maintenance
check-health:
	@echo "📊 Checking system health..."
	python3 main.py status

index-data:
	@echo "📚 Indexing personal data..."
	python3 main.py index-data

clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete

# Development environment
dev-setup: install
	@echo "🛠️  Setting up development environment..."
	pip install -e .
	pre-commit install

# Quick start for new users
quickstart: setup index-data
	@echo "🚀 Quick start completed!"
	@echo "Run 'make start' to begin using your personal assistant"

# Production deployment helpers
ollama-install:
	@echo "🤖 Installing Ollama..."
	curl -fsSL https://ollama.ai/install.sh | sh

# Backup and restore
backup-data:
	@echo "💾 Backing up data..."
	tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ .env

restore-data:
	@echo "📁 Restore data from backup..."
	@echo "Usage: make restore-data BACKUP=backup-YYYYMMDD-HHMMSS.tar.gz"
	@if [ -z "$(BACKUP)" ]; then echo "Please specify BACKUP file"; exit 1; fi
	tar -xzf $(BACKUP)

# Docker support (optional)
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t personal-chatbot .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 5000:5000 -p 5001:5001 -v $(PWD)/data:/app/data personal-chatbot

# Documentation
docs:
	@echo "📖 Building documentation..."
	@echo "Documentation available in README.md and docs/ folder"

# System requirements check
check-requirements:
	@echo "📋 Checking system requirements..."
	@python -c "import sys; print(f'Python: {sys.version}')"
	@which git > /dev/null && echo "✅ Git: installed" || echo "❌ Git: missing"
	@which ollama > /dev/null && echo "✅ Ollama: installed" || echo "❌ Ollama: missing" 