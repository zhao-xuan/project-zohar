# Multi-Agent Framework for Project Zohar

## Overview

The Multi-Agent Framework is a sophisticated system that enables DeepSeek models (which don't support function calling) to collaborate with tool-supporting models (like Llama) to provide comprehensive AI assistance. This framework creates a well-structured, scalable architecture where different agents can specialize in different capabilities and work together seamlessly.

## Architecture

### Core Components

1. **Message Bus** - Handles inter-agent communication
2. **Agent Registry** - Manages agent profiles and capabilities
3. **Coordinator Agent** - Orchestrates task delegation and result synthesis
4. **Tool Executor Agent** - Handles tool execution for models that support function calling
5. **Base Agent** - Common functionality for all agents

### Agent Types

#### Coordinator Agent
- **Role**: Orchestrates the multi-agent system
- **Model**: DeepSeek (reasoning and synthesis)
- **Capabilities**: Reasoning, Memory, Privacy
- **Responsibilities**:
  - Analyzes user queries to determine required capabilities
  - Delegates tasks to appropriate agents
  - Synthesizes results from multiple agents
  - Manages conversation flow

#### Tool Executor Agent
- **Role**: Executes tools and provides results
- **Model**: Llama 3.2 (tool-supporting model)
- **Capabilities**: Tool Calling, Code Execution, Math, Search, Weather
- **Responsibilities**:
  - Receives tool execution requests
  - Executes CAMEL AI tools
  - Returns tool results to requesting agents
  - Manages tool execution lifecycle

## Key Features

### 🔄 Model Collaboration
- DeepSeek models handle reasoning and synthesis
- Tool-supporting models handle function calling
- Seamless delegation and result passing

### 📨 Message-Based Communication
- Asynchronous message passing between agents
- Structured message types for different operations
- Priority and status tracking

### 🛠️ Tool Integration
- CAMEL AI toolkits integration
- Dynamic tool discovery and registration
- Tool execution statistics and monitoring

### 📊 Performance Monitoring
- Real-time performance metrics
- Agent health monitoring
- Conversation tracking and analytics

### 🔒 Error Handling
- Graceful error recovery
- Timeout management
- Fallback mechanisms

## Usage

### Basic Usage

```python
from zohar.core.multi_agent import (
    initialize_multi_agent_system,
    start_multi_agent_system,
    process_query,
    stop_multi_agent_system
)

# Initialize and start the system
await initialize_multi_agent_system()
await start_multi_agent_system()

# Process a query
response = await process_query("user123", "What is 25 * 13?")

# Stop the system
await stop_multi_agent_system()
```

### CLI Usage

```bash
# Test the multi-agent system
python -m zohar.cli multi-agent --query "Calculate 15 * 8"

# With context
python -m zohar.cli multi-agent --query "Search for Python tutorials" --context '{"session_type": "learning"}'
```

### Demo Script

```bash
# Run the comprehensive demo
python examples/multi_agent_demo.py
```

## Message Types

### UserQuery
- Represents a user's input query
- Contains user ID and optional context

### AgentRequest
- Request for assistance from another agent
- Specifies required capabilities and tools

### AgentResponse
- Response from an agent
- Includes results, confidence, and tools used

### ToolRequest
- Request to execute a specific tool
- Contains tool name and parameters

### ToolResult
- Result from tool execution
- Includes success status and execution time

## Agent Capabilities

### Reasoning
- Logical analysis and problem-solving
- Query understanding and task decomposition

### Tool Calling
- Function calling and tool execution
- Parameter extraction and validation

### Memory
- Conversation history management
- Context preservation across interactions

### Privacy
- Data filtering and anonymization
- Secure information handling

### Search
- Web search and information retrieval
- Knowledge base queries

### Code Execution
- Python code execution
- Script generation and testing

### Math
- Mathematical calculations
- Formula evaluation

### Weather
- Weather information retrieval
- Location-based data

## Configuration

### Environment Variables

```bash
# Default model for coordinator (DeepSeek)
LLM_MODEL_NAME=deepseek-r1:7b

# Tool-supporting model for tool execution
TOOL_MODEL_NAME=llama3.2:latest

# Message bus configuration
MESSAGE_BUS_MAX_HISTORY=1000
MESSAGE_BUS_TIMEOUT=30.0
```

### Agent Configuration

```python
# Create a custom agent
from zohar.core.multi_agent import AgentProfile, AgentRole, AgentCapability

profile = AgentProfile(
    agent_id="custom_agent_001",
    name="Custom Agent",
    model_name="llama3.2:latest",
    role=AgentRole.TOOL_EXECUTOR,
    capabilities=[AgentCapability.MATH, AgentCapability.CODE_EXECUTION],
    description="Custom agent for specific tasks"
)
```

## Performance Monitoring

### System Metrics

- Total queries processed
- Success rate
- Average response time
- System uptime

### Agent Metrics

- Individual agent performance
- Tool execution statistics
- Message processing rates
- Error rates

### Conversation Analytics

- Conversation flow tracking
- Context management efficiency
- Agent collaboration patterns

## Error Handling

### Timeout Management
- Configurable timeouts for tool execution
- Graceful degradation for slow operations

### Error Recovery
- Automatic retry mechanisms
- Fallback to alternative agents
- Error reporting and logging

### System Resilience
- Agent health monitoring
- Automatic restart capabilities
- Message queue management

## Extending the Framework

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement required methods
3. Register the agent with the system

```python
from zohar.core.multi_agent import BaseAgent, AgentRole, AgentCapability

class CustomAgent(BaseAgent):
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            name="Custom Agent",
            model_name="custom-model",
            role=AgentRole.CUSTOM,
            capabilities=[AgentCapability.CUSTOM],
            description="Custom agent implementation",
            **kwargs
        )
    
    async def _handle_user_query(self, message):
        # Implement custom query handling
        pass
```

### Adding New Tools

1. Create tool functions compatible with CAMEL AI
2. Register tools with the tool manager
3. Update agent capabilities

### Adding New Message Types

1. Define new message class inheriting from `Message`
2. Add to `MessageType` enum
3. Update message factory

## Best Practices

### Agent Design
- Keep agents focused on specific capabilities
- Implement proper error handling
- Use appropriate timeouts for operations

### Message Handling
- Validate message content
- Implement proper response formatting
- Handle edge cases gracefully

### Performance
- Monitor resource usage
- Implement caching where appropriate
- Use async operations for I/O-bound tasks

### Security
- Validate all inputs
- Implement proper access controls
- Log security-relevant events

## Troubleshooting

### Common Issues

1. **Agent not responding**
   - Check agent health status
   - Verify message bus connectivity
   - Review agent logs

2. **Tool execution failures**
   - Verify tool availability
   - Check parameter validation
   - Review tool execution logs

3. **Performance issues**
   - Monitor system resources
   - Check agent load balancing
   - Review timeout configurations

### Debugging

```python
# Get detailed system status
manager = get_multi_agent_manager()
status = manager.get_system_status()
print(json.dumps(status, indent=2))

# Get agent-specific status
agent_status = manager.get_agent_status("agent_id")
print(json.dumps(agent_status, indent=2))

# Get message history
history = manager.get_message_history(limit=10)
for msg in history:
    print(f"{msg.timestamp}: {msg.message_type} - {msg.content[:100]}")
```

## Future Enhancements

### Planned Features
- Dynamic agent scaling
- Advanced load balancing
- Machine learning-based task routing
- Enhanced conversation memory
- Multi-modal agent support

### Integration Opportunities
- External API integrations
- Database connectivity
- Real-time streaming
- WebSocket support
- REST API endpoints

## Contributing

When contributing to the multi-agent framework:

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Ensure backward compatibility
5. Follow error handling patterns

## License

This multi-agent framework is part of Project Zohar and follows the same licensing terms. 