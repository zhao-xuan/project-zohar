# Project Zohar

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Project Zohar** is a privacy-focused AI assistant with local deployment, CAMEL AI integration, and multi-platform connectivity.

[中文版本](#中文版本) | [English Version](#english-version)

---

## English Version

### ✨ Key Features

- 🔒 **Privacy-First**: Local-only processing with data protection
- 🤖 **AI Agents**: Personal and public agents with CAMEL AI tools
- 💬 **Interactive Chat**: Command-line and web chat interfaces
- 🔌 **Platform Integration**: Email, Slack, Discord, Telegram support
- 📊 **Data Processing**: Multi-format file analysis with vector search
- 🌐 **Web Interface**: Modern UI with real-time chat

### 🚀 Quick Start

**Installation**:
```bash
git clone https://github.com/your-username/project-zohar.git
cd project-zohar
python scripts/setup_wizard.py
```

**Start Services**:
```bash
make start          # Start web interface (http://localhost:8000)
```

**Interactive Chat**:
```bash
make chat           # Start CLI chat session
python -m zohar.cli chat --help  # See chat options
```

### 📖 Essential Commands

**System**:
```bash
make start          # Start web interface
make stop           # Stop services
make status         # Check status
```

**Chat**:
```bash
make chat           # Interactive chat (personal agent)
make chat-public    # Chat with public agent
python -m zohar.cli chat --model llama3.2  # Specify model
```

**Setup**:
```bash
make quickstart     # Complete setup
make ollama-setup   # Install Ollama and models
```

### 🔧 Configuration

Edit `config.env`:
```env
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3.2
PRIVACY_LEVEL=high
LOCAL_ONLY=true
```

### 💬 Chat Features

**CLI Chat Commands**:
- `help` - Show available commands
- `clear` - Clear conversation history
- `history` - Show conversation history
- `save [filename]` - Save conversation
- `exit` - End session

**Chat Options**:
```bash
python -m zohar.cli chat \
  --model llama3.2 \
  --temperature 0.7 \
  --max-tokens 2048 \
  --system "You are a helpful assistant"
```

### 🛠️ Development

```bash
make dev-install    # Setup development environment
make test           # Run tests
make lint           # Code linting
make format         # Format code
```

---

## 中文版本

### ✨ 主要功能

- 🔒 **隐私优先**: 本地处理，数据保护
- 🤖 **AI 智能体**: 集成 CAMEL AI 工具的个人和公共智能体
- 💬 **交互聊天**: 命令行和 Web 聊天界面
- 🔌 **平台集成**: 支持邮箱、Slack、Discord、Telegram
- 📊 **数据处理**: 多格式文件分析和向量搜索
- 🌐 **Web 界面**: 现代化 UI，实时聊天

### 🚀 快速开始

**安装**:
```bash
git clone https://github.com/your-username/project-zohar.git
cd project-zohar
python scripts/setup_wizard.py
```

**启动服务**:
```bash
make start          # 启动 Web 界面 (http://localhost:8000)
```

**交互聊天**:
```bash
make chat           # 启动命令行聊天
python -m zohar.cli chat --help  # 查看聊天选项
```

### 📖 常用命令

**系统管理**:
```bash
make start          # 启动 Web 界面
make stop           # 停止服务
make status         # 检查状态
```

**聊天功能**:
```bash
make chat           # 交互聊天（个人智能体）
make chat-public    # 公共智能体聊天
python -m zohar.cli chat --model llama3.2  # 指定模型
```

**环境设置**:
```bash
make quickstart     # 完整设置
make ollama-setup   # 安装 Ollama 和模型
```

### 🔧 配置

编辑 `config.env`:
```env
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3.2
PRIVACY_LEVEL=high
LOCAL_ONLY=true
```

### 💬 聊天功能

**CLI 聊天命令**:
- `help` - 显示可用命令
- `clear` - 清除对话历史
- `history` - 显示对话历史
- `save [文件名]` - 保存对话
- `exit` - 结束会话

**聊天选项**:
```bash
python -m zohar.cli chat \
  --model llama3.2 \
  --temperature 0.7 \
  --max-tokens 2048 \
  --system "你是一个有用的助手"
```

### 🛠️ 开发

```bash
make dev-install    # 设置开发环境
make test           # 运行测试
make lint           # 代码检查
make format         # 格式化代码
```

---

## 📊 Requirements

- Python 3.10+
- 8GB+ RAM (recommended)
- 5GB+ free disk space
- Ollama (for local LLM)

## 🔗 Links

- [Setup Guide](docs/quick_setup_guide.md)
- [CAMEL AI Tools](docs/camel_ai_tools_guide.md)
- [Platform Integration](docs/platform_integration.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details. 