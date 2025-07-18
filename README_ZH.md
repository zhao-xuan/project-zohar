# Project Zohar 🤖

> 注重隐私的本地部署AI助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Project Zohar 是一个全面的AI助手，强调数据隐私和本地部署。它能处理邮件、消息和文档，同时确保所有数据在您的本地机器或网络中保持私密和安全。

## 🌟 功能特色

### 核心能力
- **隐私优先设计**: 所有数据处理都在本地进行
- **多智能体架构**: 个人和公共智能体适用于不同场景
- **邮件与消息处理**: 自动分析和回复建议
- **文档智能**: 智能文件分析和组织
- **数字化身**: 学习您沟通风格的个性化AI助手
- **本地LLM支持**: 与Ollama配合实现完全离线操作

### 平台集成
- **邮箱**: Gmail、Outlook、IMAP/SMTP
- **消息**: Slack、Discord、Telegram
- **文件**: PDF、DOCX、TXT、MD、CSV、JSON等
- **API**: 可扩展的MCP (模型上下文协议) 服务器支持

### 用户界面
- **命令行**: 功能完整的CLI，支持丰富输出
- **Web界面**: 基于FastAPI构建的现代Web UI
- **Gradio界面**: 交互式机器学习界面
- **设置向导**: 引导式配置流程

## 🚀 快速开始

### 前置要求

- Python 3.9 或更高版本
- [Ollama](https://ollama.ai/) (用于本地LLM支持)
- Git

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/project-zohar.git
cd project-zohar

# 快速设置 (创建虚拟环境，安装依赖，并初始化)
make quickstart

# 或手动安装
python3 -m venv .venv
source .venv/bin/activate  # Windows系统使用: .venv\Scripts\activate
pip install -e .
```

### 2. 初始化 Project Zohar

```bash
# 使用默认设置初始化
make init

# 或运行交互式设置向导
make setup
```

### 3. 设置 Ollama (本地LLM)

```bash
# 安装Ollama (如果尚未安装)
curl -fsSL https://ollama.ai/install.sh | sh

# 下载并设置模型
make ollama-setup
```

### 4. 启动应用

```bash
# 启动所有服务
make start

# 或直接启动Web界面
make ui-web
```

访问 `http://localhost:8000` 以使用Web界面。

## 📖 使用指南

### 命令行界面

Project Zohar 提供全面的CLI用于所有操作:

```bash
# 显示帮助
zohar --help

# 初始化系统
zohar setup init

# 启动智能体
zohar agent start --type personal
zohar agent start --type public

# 分析数据
zohar data analyze /path/to/your/documents

# 检查状态
zohar setup status
```

### Web界面

Web界面提供直观的方式与Project Zohar交互:

1. **设置向导**: 首次配置
2. **聊天界面**: 与AI智能体交互
3. **数据管理**: 上传和分析文档
4. **平台连接**: 连接邮箱和消息账户
5. **设置**: 配置模型、隐私设置和偏好

### 配置

Project Zohar 使用分层配置系统:

1. **环境变量**: `.env` 文件
2. **配置文件**: YAML/JSON 配置文件
3. **命令行参数**: 覆盖任何设置
4. **交互向导**: 引导式设置流程

#### 基本配置

在项目根目录创建 `.env` 文件:

```env
# LLM 配置
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama2:7b
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API密钥 (可选，用于外部服务)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# 平台凭证
GMAIL_CREDENTIALS_PATH=/path/to/gmail/credentials.json
SLACK_BOT_TOKEN=xoxb-your-slack-token

# 隐私设置
LOCAL_ONLY=true
ANONYMIZE_DATA=true
DATA_RETENTION_DAYS=365

# Web界面
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

## 🏗️ 架构

Project Zohar 遵循模块化、基于插件的架构:

```
├── 核心组件
│   ├── 智能体 (个人和公共)
│   ├── 内存管理
│   ├── LLM集成
│   └── 任务编排
├── 服务层
│   ├── 数据处理
│   ├── 平台集成
│   ├── MCP服务
│   └── 向量存储
├── 工具与集成
│   ├── MCP服务器
│   ├── 浏览器工具
│   ├── 邮件工具
│   └── 系统工具
└── 用户界面
    ├── CLI
    ├── Web UI
    ├── Gradio界面
    └── 设置向导
```

### 智能体类型

#### 个人智能体
- 有权访问私人用户数据
- 处理邮件、消息和文档
- 维护对话历史
- 提供个性化回复

#### 公共智能体
- 无权访问私人数据
- 处理常规查询
- 仅有临时会话上下文
- 适用于面向公众的交互

## 📚 数据处理

Project Zohar 自动分析和处理各种类型的数据:

### 支持的文件类型

- **文档**: PDF、DOCX、TXT、MD、RTF
- **电子表格**: XLSX、CSV、TSV
- **代码**: PY、JS、TS、CPP、JAVA、GO、RS
- **数据**: JSON、XML、YAML、SQL
- **图片**: JPG、PNG (带OCR)
- **压缩包**: ZIP、TAR、GZ

### 处理流程

1. **文件发现**: 扫描目录并识别文件类型
2. **内容提取**: 提取文本和元数据
3. **分析**: 生成摘要和洞察
4. **索引**: 创建向量嵌入以进行语义搜索
5. **存储**: 存储在本地向量数据库中

### 隐私功能

- **本地处理**: 所有分析在您的机器上进行
- **数据匿名化**: 移除敏感信息
- **选择性共享**: 控制智能体可访问的数据
- **加密**: 加密存储的数据和备份

## 🔌 平台集成

### 邮件集成

```bash
# 连接Gmail账户
zohar platform connect gmail

# 处理邮件
zohar data process --source email --platform gmail
```

支持的邮箱平台:
- Gmail (OAuth2)
- Outlook (OAuth2)
- IMAP/SMTP (任何提供商)

### 消息集成

```bash
# 连接Slack
zohar platform connect slack

# 连接Discord
zohar platform connect discord
```

支持的消息平台:
- Slack (Bot API)
- Discord (Bot API)  
- Telegram (Bot API)

### MCP服务器集成

Project Zohar 支持模型上下文协议(MCP)进行工具集成:

```python
# 示例: 自定义MCP服务器
from zohar.tools.mcp_servers import MCPServer

class CustomTool(MCPServer):
    def __init__(self):
        super().__init__("custom_tool")
    
    async def execute(self, action: str, **kwargs):
        # 您的自定义逻辑
        return {"result": "success"}
```

## 🎛️ 高级配置

### 模型配置

```yaml
# ~/.zohar/config.yaml
models:
  default: "llama2:7b"
  embedding: "all-MiniLM-L6-v2"
  
  # 模型特定设置
  llama2:
    temperature: 0.7
    max_tokens: 4096
    context_window: 4096
  
  # 自定义模型端点
  custom_model:
    type: "openai_compatible"
    base_url: "http://localhost:8080/v1"
    api_key: "your_key"
```

### 隐私设置

```yaml
privacy:
  local_only: true
  anonymize_data: true
  data_retention_days: 365
  
  # 匿名化规则
  anonymization:
    - pattern: '\b\d{3}-\d{2}-\d{4}\b'  # 社会保险号
      replacement: '[SSN]'
    - pattern: '\b\w+@\w+\.\w+\b'       # 邮箱地址
      replacement: '[EMAIL]'
```

### 智能体自定义

```yaml
agents:
  personal:
    memory_size: 1000
    context_window: 10
    tools:
      - email_processor
      - file_analyzer
      - web_search
  
  public:
    memory_size: 100
    context_window: 5
    tools:
      - web_search
      - calculator
      - weather
```

## 🛠️ 开发

### 设置开发环境

```bash
# 克隆并设置开发环境
git clone https://github.com/your-org/project-zohar.git
cd project-zohar

# 安装开发依赖
make dev-install

# 运行测试
make test

# 格式化代码
make format

# 运行代码检查
make lint
```

### 项目结构

```
project-zohar/
├── src/zohar/              # 主包
│   ├── core/               # 核心组件
│   │   ├── agents/         # 智能体实现
│   │   ├── memory/         # 内存管理
│   │   ├── orchestration/  # 任务编排
│   │   └── llm/           # LLM集成
│   ├── services/          # 服务层
│   │   ├── data_processing/
│   │   ├── platform_integration/
│   │   └── mcp_services/
│   ├── tools/             # 工具和集成
│   ├── ui/                # 用户界面
│   ├── config/            # 配置
│   └── utils/             # 工具
├── tests/                 # 测试套件
├── docs/                  # 文档
├── scripts/               # 脚本和工具
└── config/                # 配置模板
```

### 添加新功能

1. **创建功能分支**: `git checkout -b feature/your-feature`
2. **实现功能**: 在适当的模块中添加代码
3. **添加测试**: 编写单元和集成测试
4. **更新文档**: 更新README和文档
5. **提交PR**: 创建拉取请求以供审查

### 测试

```bash
# 运行所有测试
make test

# 运行特定类型的测试
make test-unit
make test-integration
make test-e2e

# 运行覆盖率测试
pytest --cov=zohar --cov-report=html
```

## 📦 部署

### 本地部署

```bash
# 构建发行版
make build

# 本地安装
pip install dist/project_zohar-*.whl
```

### Docker部署

```bash
# 构建Docker镜像
make docker-build

# 运行容器
make docker-run

# 访问 http://localhost:8000
```

### 生产部署

生产部署时请考虑:

1. **安全性**: 使用适当的身份验证和HTTPS
2. **性能**: 配置适当的模型大小
3. **备份**: 定期数据备份
4. **监控**: 设置日志记录和监控
5. **更新**: 计划定期更新

## 🤝 贡献

我们欢迎贡献！请查看我们的[贡献指南](CONTRIBUTING.md)了解详情。

### 快速贡献步骤

1. Fork 仓库
2. 创建功能分支
3. 进行更改
4. 添加测试和文档
5. 提交拉取请求

### 开发原则

- **隐私优先**: 始终优先考虑用户隐私
- **本地处理**: 优先本地而非云处理
- **模块化**: 保持组件松耦合
- **测试**: 维持高测试覆盖率
- **文档**: 记录所有公共API

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Camel AI](https://www.camel-ai.org/) - 多智能体框架
- [Ollama](https://ollama.ai/) - 本地LLM部署
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架

## 📞 支持

- **文档**: [docs.projectzohar.com](https://docs.projectzohar.com)
- **问题**: [GitHub Issues](https://github.com/your-org/project-zohar/issues)
- **讨论**: [GitHub Discussions](https://github.com/your-org/project-zohar/discussions)
- **邮箱**: support@projectzohar.com

## 🗺️ 路线图

### 当前版本 (v0.1.0)
- ✅ 基础智能体框架
- ✅ 本地LLM集成
- ✅ 文件处理流程
- ✅ Web界面
- ✅ 邮件集成

### 即将推出的功能
- 🔄 增强的多智能体协作
- 🔄 移动应用支持
- 🔄 高级隐私控制
- 🔄 插件市场
- 🔄 企业功能

### 未来版本
- 📱 移动应用
- 🌐 联邦支持
- 🔒 高级加密
- 🤖 自定义模型训练
- 🔌 广泛的API生态系统

---

由 Project Zohar 团队用 ❤️ 制作 