# Project Zohar Makefile
# Essential targets for development and deployment

.PHONY: help install dev-install clean setup start stop status test lint format ui-web ollama-setup logs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
VENV_DIR := .venv
SRC_DIR := src
TESTS_DIR := tests

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Help target
help: ## Show this help message
	@echo "$(BLUE)Project Zohar - Available Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Installation & Setup:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(install|setup|clean)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(test|lint|format)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Application:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(start|stop|status|ui)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Ollama & LLM:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep "ollama" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Chat & Interaction:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep "chat" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Data Processing:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep "digest" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Demos & Examples:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep "demo" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(logs|help)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

# Installation targets
install: ## Install Project Zohar
	@echo "$(GREEN)Installing Project Zohar...$(NC)"
	$(PIP) install -e .
	@echo "$(GREEN)Installation complete!$(NC)"

dev-install: ## Install for development with all dependencies
	@echo "$(GREEN)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -e ".[dev]"
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV_DIR)/bin/activate$(NC)"

clean: ## Clean up build artifacts and caches
	@echo "$(YELLOW)Cleaning up...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf $(VENV_DIR)/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.orig" -delete
	find . -type f -name "*.rej" -delete
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Setup targets
setup: ## Run interactive setup wizard (web-based)
	@echo "$(GREEN)Starting Project Zohar web setup wizard...$(NC)"
	$(PYTHON) -m zohar.cli setup wizard

setup-cli: ## Run command-line setup wizard
	@echo "$(GREEN)Starting Project Zohar CLI setup wizard...$(NC)"
	$(PYTHON) -m zohar.cli setup wizard --no-web

setup-web: ## Run web-based setup wizard
	@echo "$(GREEN)Starting Project Zohar web setup wizard...$(NC)"
	$(PYTHON) -m zohar.cli setup wizard --web

init: ## Initialize Project Zohar with default settings
	@echo "$(GREEN)Initializing Project Zohar...$(NC)"
	mkdir -p config data logs agent_workspace
	cp -n config.env.example config.env 2>/dev/null || true
	@echo "$(GREEN)Initialization complete!$(NC)"
	@echo "$(YELLOW)Edit config.env to customize settings$(NC)"

# Application targets
start: ## Start Project Zohar services
	@echo "$(GREEN)Starting Project Zohar...$(NC)"
	$(PYTHON) -m zohar.cli start

stop: ## Stop Project Zohar services
	@echo "$(YELLOW)Stopping Project Zohar...$(NC)"
	$(PYTHON) -m zohar.cli stop

status: ## Check Project Zohar status
	@echo "$(BLUE)Project Zohar Status:$(NC)"
	$(PYTHON) -m zohar.cli status

# UI targets
ui-web: ## Launch web interface
	@echo "$(GREEN)Starting web interface...$(NC)"
	$(PYTHON) -m zohar.cli ui web

ui-gradio: ## Launch Gradio interface
	@echo "$(GREEN)Starting Gradio interface...$(NC)"
	$(PYTHON) -m zohar.cli ui gradio

# Development targets
test: ## Run test suite
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTHON) -m pytest $(TESTS_DIR)/ -v

test-quick: ## Run quick tests (unit tests only)
	@echo "$(GREEN)Running quick tests...$(NC)"
	$(PYTHON) -m pytest $(TESTS_DIR)/unit/ -v

lint: ## Run code linting
	@echo "$(GREEN)Running code linting...$(NC)"
	$(PYTHON) -m flake8 $(SRC_DIR)/
	$(PYTHON) -m mypy $(SRC_DIR)/

format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	$(PYTHON) -m black $(SRC_DIR)/ $(TESTS_DIR)/
	$(PYTHON) -m isort $(SRC_DIR)/ $(TESTS_DIR)/

# Ollama targets
ollama-setup: ## Setup Ollama and download default model
	@echo "$(GREEN)Setting up Ollama...$(NC)"
	@if ! command -v ollama &> /dev/null; then \
		echo "$(RED)Ollama not found. Please install from https://ollama.ai$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Downloading default model (llama3.2)...$(NC)"
	ollama pull llama3.2
	@echo "$(GREEN)Ollama setup complete!$(NC)"

ollama-start: ## Start Ollama service
	@echo "$(GREEN)Starting Ollama service...$(NC)"
	@if ! pgrep -f ollama serve > /dev/null; then \
		ollama serve & \
		echo "$(GREEN)Ollama service started$(NC)"; \
	else \
		echo "$(YELLOW)Ollama service already running$(NC)"; \
	fi

ollama-stop: ## Stop Ollama service
	@echo "$(YELLOW)Stopping Ollama service...$(NC)"
	@pkill -f "ollama serve" || echo "$(YELLOW)Ollama service not running$(NC)"

ollama-models: ## List available Ollama models
	@echo "$(BLUE)Available Ollama models:$(NC)"
	@ollama list || echo "$(RED)Ollama not running or not installed$(NC)"

# Demo targets
demo-tools: ## Demo CAMEL AI tools integration
	@echo "$(GREEN)Running CAMEL AI Tools Demo...$(NC)"
	$(PYTHON) examples/camel_tools_demo.py

demo-basic: ## Demo basic CAMEL AI integration
	@echo "$(GREEN)Running Basic CAMEL AI Demo...$(NC)"
	$(PYTHON) examples/camel_ai_basic_example.py

# Chat targets
chat: ## Start interactive chat with AI
	@echo "$(GREEN)Starting interactive chat session...$(NC)"
	$(PYTHON) -m zohar.cli chat

chat-public: ## Start chat with public agent
	@echo "$(GREEN)Starting public agent chat...$(NC)"
	$(PYTHON) -m zohar.cli chat --type public

chat-help: ## Show chat command options
	@echo "$(BLUE)Chat Command Options:$(NC)"
	$(PYTHON) -m zohar.cli chat --help

# Data Digestion targets
digest-data: ## Start intelligent data digestion process
	@echo "$(GREEN)Starting data digestion...$(NC)"
	$(PYTHON) -c "import asyncio; from zohar.services.data_digestion import DigestionManager; dm = DigestionManager(); print('Session ID:', asyncio.run(dm.start_digestion('./data', max_files=50)))"

digest-status: ## Check status of latest digestion session
	@echo "$(GREEN)Checking digestion status...$(NC)"
	$(PYTHON) -c "from zohar.services.data_digestion import DigestionManager; dm = DigestionManager(); sessions = dm.list_sessions(); print('Sessions:', sessions)"

digest-demo: ## Run data digestion demo with sample data
	@echo "$(GREEN)Running data digestion demo...$(NC)"
	$(PYTHON) -c "import asyncio; from zohar.services.data_digestion import DigestionManager; dm = DigestionManager(); print('Demo session:', asyncio.run(dm.start_digestion('./examples', max_files=10)))"

# Utility targets
logs: ## Show application logs
	@echo "$(BLUE)Recent logs:$(NC)"
	@if [ -f logs/main.log ]; then \
		tail -50 logs/main.log; \
	else \
		echo "$(YELLOW)No log files found$(NC)"; \
	fi

logs-tail: ## Follow application logs in real-time
	@echo "$(BLUE)Following logs (Ctrl+C to stop):$(NC)"
	@if [ -f logs/main.log ]; then \
		tail -f logs/main.log; \
	else \
		echo "$(YELLOW)No log files found$(NC)"; \
	fi

# Quick setup target
quickstart: dev-install init ollama-setup ## Complete quickstart setup
	@echo "$(GREEN)Project Zohar quickstart complete!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "1. $(YELLOW)source $(VENV_DIR)/bin/activate$(NC) - Activate virtual environment"
	@echo "2. $(YELLOW)make setup$(NC) - Run setup wizard (optional)"
	@echo "3. $(YELLOW)make ui-web$(NC) - Start web interface"
	@echo ""
	@echo "$(GREEN)Visit http://localhost:8000 to get started!$(NC)"

# Check prerequisites
check: ## Check system prerequisites
	@echo "$(BLUE)Checking system prerequisites...$(NC)"
	@echo -n "Python 3.10+: "
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'; print('✓')" || echo "$(RED)✗ Python 3.10+ required$(NC)"
	@echo -n "Pip: "
	@command -v pip >/dev/null 2>&1 && echo "✓" || echo "$(RED)✗ pip not found$(NC)"
	@echo -n "Git: "
	@command -v git >/dev/null 2>&1 && echo "✓" || echo "$(YELLOW)⚠ git not found (optional)$(NC)"
	@echo -n "Ollama: "
	@command -v ollama >/dev/null 2>&1 && echo "✓" || echo "$(YELLOW)⚠ ollama not found (run 'make ollama-setup')$(NC)"

# Docker targets (minimal)
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t project-zohar .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run -p 8000:8000 -v $(PWD)/data:/app/data project-zohar

# Backup and restore
backup: ## Backup data and configuration
	@echo "$(GREEN)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/zohar-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ config/ logs/ || true
	@echo "$(GREEN)Backup created in backups/$(NC)"

# Development utilities
dev: ui-web ## Start development mode (alias for ui-web)

test-watch: ## Run tests in watch mode
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	$(PYTHON) -m pytest-watch $(TESTS_DIR)/

# Installation verification
verify: ## Verify installation
	@echo "$(BLUE)Verifying Project Zohar installation...$(NC)"
	@$(PYTHON) -c "import zohar; print('✓ Zohar package imported successfully')" || echo "$(RED)✗ Zohar package import failed$(NC)"
	@$(PYTHON) -c "from zohar.config.settings import get_settings; print('✓ Settings loaded successfully')" || echo "$(RED)✗ Settings loading failed$(NC)"
	@echo "$(GREEN)Installation verification complete!$(NC)" 