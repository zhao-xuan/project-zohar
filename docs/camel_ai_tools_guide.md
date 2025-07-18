# CAMEL AI Tools Integration Guide for Project Zohar

## Overview

Project Zohar now integrates with CAMEL AI's native toolkit system, providing powerful tool calling capabilities for agents. This integration allows agents to use built-in tools for math calculations, web searches, code execution, weather data, research papers, and more.

## Architecture

The tool system consists of three main components:

1. **CamelToolManager**: Manages CAMEL AI toolkits and provides tool execution
2. **ToolEnabledAgent**: Wrapper for ChatAgent with tool support
3. **Integration with PersonalAgent**: Seamless tool integration for personal agents

## Available Toolkits

### Core Toolkits

#### 🧮 Math Toolkit
- **Tools**: `math_add`, `math_sub`, `math_mul`
- **Purpose**: Basic mathematical operations
- **Example**: Adding numbers, multiplication, subtraction

#### 🔍 Search Toolkit
- **Tools**: `search_search_wiki`, `search_search_google`, `search_search_duckduckgo`, `search_query_wolfram_alpha`, `search_tavily_search`
- **Purpose**: Web search and information retrieval
- **Example**: Finding information about topics, factual queries

#### 💻 Code Execution Toolkit
- **Tools**: `code_execution_execute_code`
- **Purpose**: Execute Python code snippets
- **Example**: Running calculations, data processing

#### 🌤️ Weather Toolkit
- **Tools**: `weather_get_weather_data`
- **Purpose**: Get weather information for cities
- **Example**: Current weather conditions, forecasts

#### 📚 ArXiv Toolkit
- **Tools**: `arxiv_search_papers`, `arxiv_download_papers`
- **Purpose**: Search and download academic papers
- **Example**: Research paper discovery, academic research

### Communication Toolkits (Optional)

#### 📧 Slack Toolkit
- **Requirement**: `SLACK_TOKEN` environment variable
- **Purpose**: Slack integration for messaging

#### 🐦 Twitter Toolkit
- **Requirement**: Twitter API credentials
- **Purpose**: Twitter integration for social media

#### 🔗 LinkedIn Toolkit
- **Requirement**: LinkedIn access token
- **Purpose**: LinkedIn integration for professional networking

## Basic Usage

### 1. Initialize Tool Manager

```python
from zohar.tools.camel_tool_manager import CamelToolManager

# Initialize tool manager
tool_manager = CamelToolManager()
await tool_manager.initialize()

# Check available tools
tools = tool_manager.get_available_tools()
print(f"Available tools: {len(tools)}")
```

### 2. Execute Tools Directly

```python
# Math operation
result = await tool_manager.execute_tool(
    tool_name="math_add",
    parameters={"a": 123, "b": 456}
)
print(f"Result: {result['result']}")  # 579

# Web search
result = await tool_manager.execute_tool(
    tool_name="search_search_wiki",
    parameters={"query": "artificial intelligence"}
)
print(f"Search result: {result['result']}")
```

### 3. Create Tool-Enabled Agent

```python
from zohar.tools.camel_tool_manager import ToolEnabledAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Create model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llama3.2",
    url="http://localhost:11434/v1"
)

# Create agent with specific toolkits
agent = ToolEnabledAgent(
    system_message="You are a helpful assistant with access to various tools.",
    model=model,
    tool_manager=tool_manager,
    enabled_toolkits=['math', 'search', 'weather']
)

# Use the agent
response = await agent.step("What is 15 * 24?")
print(response.content)
```

## Integration with PersonalAgent

The PersonalAgent automatically integrates with CAMEL AI tools:

```python
from zohar.core.agents.personal_agent import PersonalAgent

# Create personal agent
agent = PersonalAgent(user_id="user123")
await agent.start()

# Tools are automatically available
tools = agent.get_available_tools()
print(f"Agent has {len(tools)} tools available")

# Use tools through natural conversation
response = await agent.process_message("Calculate 50 + 75 for me")
print(response)  # Should use math_add tool automatically
```

## Advanced Features

### Tool Categories

Tools are organized into categories for easy filtering:

```python
# Get tools by category
math_tools = tool_manager.get_tools_by_category('math')
search_tools = tool_manager.get_tools_by_category('search')
code_tools = tool_manager.get_tools_by_category('code')
```

### Tool Search

Find tools by name or description:

```python
# Search for calculation tools
calc_tools = tool_manager.search_tools('calculate')
print([tool['name'] for tool in calc_tools])
```

### Execution Statistics

Monitor tool usage:

```python
# Get execution statistics
stats = tool_manager.get_execution_stats()
print(f"Total calls: {stats['total_calls']}")
print(f"Success rate: {stats['successful_calls']}/{stats['total_calls']}")
```

## Configuration

### Environment Variables

Set up API keys for external services:

```bash
# For weather data
export OPENWEATHER_API_KEY="your-api-key"

# For search tools (some require API keys)
export GOOGLE_API_KEY="your-google-api-key"
export TAVILY_API_KEY="your-tavily-api-key"

# For communication tools
export SLACK_TOKEN="your-slack-token"
export TWITTER_API_KEY="your-twitter-api-key"
```

### Toolkit Selection

Choose specific toolkits for different agent types:

```python
# Math specialist agent
math_agent = ToolEnabledAgent(
    system_message="You are a math expert.",
    model=model,
    tool_manager=tool_manager,
    enabled_toolkits=['math']
)

# Research assistant agent  
research_agent = ToolEnabledAgent(
    system_message="You are a research assistant.",
    model=model,
    tool_manager=tool_manager,
    enabled_toolkits=['search', 'arxiv']
)

# Code assistant agent
code_agent = ToolEnabledAgent(
    system_message="You are a coding assistant.",
    model=model,
    tool_manager=tool_manager,
    enabled_toolkits=['code_execution']
)
```

## Examples

### Example 1: Basic Math Operations

```python
import asyncio
from zohar.tools.camel_tool_manager import CamelToolManager

async def math_example():
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    
    # Addition
    result = await tool_manager.execute_tool('math_add', {'a': 100, 'b': 200})
    print(f"100 + 200 = {result['result']}")
    
    # Multiplication
    result = await tool_manager.execute_tool('math_mul', {'a': 15, 'b': 8})
    print(f"15 * 8 = {result['result']}")
    
    await tool_manager.shutdown()

asyncio.run(math_example())
```

### Example 2: Web Search

```python
async def search_example():
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    
    # Wikipedia search
    result = await tool_manager.execute_tool(
        'search_search_wiki',
        {'query': 'machine learning'}
    )
    
    if result['success']:
        print(f"Wikipedia result: {result['result'][:200]}...")
    
    await tool_manager.shutdown()

asyncio.run(search_example())
```

### Example 3: Code Execution

```python
async def code_example():
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    
    # Execute Python code
    python_code = """
import math
result = math.sqrt(144) + math.pi
print(f"Square root of 144 + π = {result}")
"""
    
    result = await tool_manager.execute_tool(
        'code_execution_execute_code',
        {'code': python_code}
    )
    
    if result['success']:
        print(f"Code execution result: {result['result']}")
    
    await tool_manager.shutdown()

asyncio.run(code_example())
```

## Error Handling

The tool system includes comprehensive error handling:

```python
result = await tool_manager.execute_tool('math_add', {'a': 10, 'b': 20})

if result['success']:
    print(f"Result: {result['result']}")
else:
    print(f"Error: {result['error']}")
```

## Best Practices

### 1. Resource Management

Always shutdown the tool manager when done:

```python
try:
    tool_manager = CamelToolManager()
    await tool_manager.initialize()
    # Use tools...
finally:
    await tool_manager.shutdown()
```

### 2. Error Checking

Check tool execution results:

```python
result = await tool_manager.execute_tool(tool_name, parameters)
if not result['success']:
    logger.error(f"Tool {tool_name} failed: {result['error']}")
```

### 3. Toolkit Selection

Choose appropriate toolkits for your use case:

```python
# For general purpose
general_toolkits = ['math', 'search', 'weather']

# For development tasks
dev_toolkits = ['code_execution', 'search']

# For research tasks
research_toolkits = ['search', 'arxiv']
```

## Troubleshooting

### Common Issues

1. **Tool not found**: Check available tools with `get_available_tools()`
2. **API key errors**: Ensure environment variables are set correctly
3. **Rate limiting**: Some search tools have rate limits
4. **Model compatibility**: Ensure your model supports tool calling

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Tool execution will show detailed debug information
```

## API Reference

### CamelToolManager

- `initialize()`: Initialize tool manager and toolkits
- `execute_tool(tool_name, parameters)`: Execute a specific tool
- `get_available_tools()`: Get list of available tools
- `get_tools_by_category(category)`: Get tools by category
- `search_tools(query)`: Search tools by name/description
- `get_execution_stats()`: Get tool usage statistics
- `shutdown()`: Clean up resources

### ToolEnabledAgent

- `step(message)`: Process message with tool support
- `get_available_tools()`: Get agent's available tools
- `add_toolkit(toolkit_name)`: Add toolkit to agent
- `remove_toolkit(toolkit_name)`: Remove toolkit from agent

## Conclusion

The CAMEL AI tools integration provides powerful capabilities for Project Zohar agents. With support for math, search, code execution, weather, and research tools, agents can now perform complex tasks and provide more valuable assistance to users.

The integration is designed to be:
- **Easy to use**: Simple API for tool execution
- **Flexible**: Choose specific toolkits for different agents
- **Robust**: Comprehensive error handling and monitoring
- **Extensible**: Easy to add new toolkits and tools

Start with the basic examples above and explore the full range of capabilities available through CAMEL AI's toolkit system. 