# Personal Multi-Agent Chatbot System Makefile

.PHONY: help install setup start start-personal start-public start-web start-mcp test clean lint format check-health index-data

# Default target
help:
	@echo "🤖 Personal Multi-Agent Chatbot System"
	@echo ""
	@echo "Available targets:"
	@echo "  help          Show this help message"
	@echo "  install       Install Python dependencies"
	@echo "  setup         Run interactive setup wizard"
	@echo "  start         Start personal bot in terminal"
	@echo "  start-public  Start public bot in terminal"
	@echo "  start-web     Start web interface for both bots"
	@echo "  start-mcp     Start MCP servers"
	@echo "  test          Run all tests"
	@echo "  lint          Run code linting"
	@echo "  format        Format code with black"
	@echo "  check-health  Check system health"
	@echo "  index-data    Index personal data for RAG"
	@echo "  clean         Clean up temporary files"

# Installation and setup
install:
	@echo "📦 Installing dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt

setup: install
	@echo "🔧 Running setup wizard..."
	python main.py setup

# Start services
start:
	@echo "🔐 Starting personal bot in terminal..."
	python main.py terminal --type personal

start-public:
	@echo "🌐 Starting public bot in terminal..."
	python main.py terminal --type public

start-web:
	@echo "🌐 Starting web interface..."
	python main.py web --type both

start-mcp:
	@echo "🔗 Starting MCP servers..."
	python main.py start-mcp-servers

# Development
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

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
	python main.py status

index-data:
	@echo "📚 Indexing personal data..."
	python main.py index-data

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

ollama-setup: ollama-install
	@echo "📥 Downloading DeepSeek model..."
	ollama pull deepseek

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