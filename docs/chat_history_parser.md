# Chat History Parser Module

A comprehensive module for parsing, analyzing, and storing chat history from multiple platforms (Slack, Teams, Discord, etc.) with autonomous processing capabilities and knowledge graph construction.

## Features

### Multi-Platform Support
- **Slack**: Export files and API integration
- **Microsoft Teams**: Graph API integration
- **Discord**: Bot-based message collection
- **Extensible architecture** for adding new platforms

### Knowledge Graph Construction
- **Entity Extraction**: Automatically identify people, topics, projects, channels
- **Relationship Mapping**: Track interactions, mentions, collaborations
- **SQLite Storage**: Local database for entity relationships
- **Graph Queries**: Find connections and patterns in communication

### Vector Search
- **Semantic Search**: Find similar messages using embeddings
- **ChromaDB Integration**: Efficient vector storage and retrieval
- **Fallback Support**: Works without external dependencies

### Autonomous Processing
- **Scheduled Analysis**: Weekly, monthly, or custom intervals
- **Batch Processing**: Handle large volumes of messages efficiently
- **Error Handling**: Robust processing with retry mechanisms
- **Local Deployment**: No cloud dependencies required

## Installation

1. **Basic Setup** (works with fallback features):
```bash
# Already included in project requirements
pip install -r requirements.txt
```

2. **Full Features** (recommended):
```bash
pip install pandas numpy sentence-transformers chromadb
```

## Quick Start

### 1. Analyze Slack Export

```python
from src.services.chat_history_manager import analyze_slack_export
import asyncio

async def main():
    # Analyze last 7 days from Slack export
    results = await analyze_slack_export('./path/to/slack_export', days=7)
    print(f"Processed {results['total_messages']} messages")
    print(f"Found {results['total_entities']} entities")

asyncio.run(main())
```

### 2. Using the Manager Class

```python
from src.services.chat_history_manager import ChatHistoryManager
import asyncio

async def main():
    # Create and setup manager
    manager = ChatHistoryManager()
    await manager.setup()
    
    # Run analysis for last week
    results = await manager.analyze_last_week()
    
    # Search messages
    search_results = manager.search_messages("project update")
    
    # Get analytics
    analytics = manager.get_analytics_summary(30)
    
    # Export knowledge graph
    manager.export_knowledge_graph('./knowledge_graph.json')

asyncio.run(main())
```

### 3. Command Line Interface

```bash
# Analyze Slack export
python src/services/chat_history_cli.py analyze --slack-export ./slack_export --days 7

# Search messages
python src/services/chat_history_cli.py search --query "project update"

# Show system status
python src/services/chat_history_cli.py status

# Export knowledge graph
python src/services/chat_history_cli.py export --output ./knowledge_graph.json

# Start scheduled analysis
python src/services/chat_history_cli.py schedule --start
```

## Configuration

### Environment Variables

```bash
# Database paths
export CHAT_KNOWLEDGE_GRAPH_DB="./data/knowledge_graph.db"
export CHAT_VECTOR_STORE_DB="./data/vector_store"

# Slack configuration
export SLACK_EXPORT_PATH="./data/slack_export"
export SLACK_API_TOKEN="xoxb-your-slack-token"

# Teams configuration
export TEAMS_CLIENT_ID="your-client-id"
export TEAMS_CLIENT_SECRET="your-client-secret"
export TEAMS_TENANT_ID="your-tenant-id"

# Processing settings
export CHAT_BATCH_SIZE="1000"
export CHAT_EMBEDDING_MODEL="all-MiniLM-L6-v2"

# Scheduling
export CHAT_ENABLE_SCHEDULING="true"
export CHAT_SCHEDULE_INTERVAL="weekly"
```

### Configuration File

```python
from src.services.chat_history_config import create_default_config, save_config_to_file

# Create and customize config
config = create_default_config()
config.slack.export_path = "./data/slack_export"
config.processing.batch_size = 500
config.scheduling.enable_scheduling = True
config.scheduling.schedule_interval = "weekly"

# Save configuration
save_config_to_file(config, "./config/chat_history_config.json")
```

## Architecture

### Core Components

1. **ChatHistoryProcessor**: Main processing engine
2. **KnowledgeGraphManager**: Entity and relationship storage
3. **VectorStoreManager**: Semantic search capabilities
4. **EntityExtractor**: Extract entities from messages
5. **ChatHistoryScheduler**: Autonomous scheduling
6. **Platform Connectors**: Interface with different platforms

### Data Flow

```
Platform APIs/Exports
         ↓
    Data Ingestion
         ↓
   Message Normalization
         ↓
    Entity Extraction
         ↓
  Knowledge Graph Update
         ↓
   Vector Store Update
         ↓
    Analytics Generation
```

### Database Schema

#### Knowledge Graph (SQLite)
- **entities**: Store people, topics, projects, channels
- **relationships**: Track connections between entities

#### Vector Store (ChromaDB)
- **chat_messages**: Embedded messages for semantic search
- **metadata**: Platform, channel, sender information

## Platform Setup

### Slack

#### Option 1: Export Files
1. Go to Slack workspace settings
2. Export data for date range
3. Download and extract ZIP file
4. Set `SLACK_EXPORT_PATH` to extracted directory

#### Option 2: API Integration
1. Create Slack app at api.slack.com
2. Add bot token scopes: `channels:history`, `groups:history`, `im:history`
3. Install app to workspace
4. Set `SLACK_API_TOKEN` environment variable

### Microsoft Teams

1. Register app in Azure AD
2. Grant permissions: `Chat.Read`, `ChannelMessage.Read.All`
3. Set environment variables:
   - `TEAMS_CLIENT_ID`
   - `TEAMS_CLIENT_SECRET`
   - `TEAMS_TENANT_ID`

### Discord

1. Create Discord application
2. Create bot and get token
3. Add bot to servers with read permissions
4. Set `DISCORD_BOT_TOKEN` environment variable

## Advanced Usage

### Custom Platform Connector

```python
from src.services.chat_history_parser import PlatformConnector, ChatPlatform

class CustomConnector(PlatformConnector):
    def __init__(self):
        super().__init__(ChatPlatform.GENERIC)
    
    async def fetch_messages(self, start_time, end_time):
        # Implement message fetching
        return messages
    
    def normalize_message(self, raw_message):
        # Convert to NormalizedMessage format
        return normalized_message

# Register with processor
processor.register_connector(ChatPlatform.GENERIC, CustomConnector())
```

### Custom Entity Patterns

```python
config.entity_extraction.custom_patterns = {
    'issue_id': r'ISSUE-(\d+)',
    'version': r'v(\d+\.\d+\.\d+)',
    'meeting': r'meeting\s+(\w+\s+\d+)'
}
```

### Scheduled Analysis

```python
from src.services.chat_history_scheduler import ChatHistoryScheduler, ScheduleInterval

scheduler = ChatHistoryScheduler()

# Add custom job
scheduler.add_job(
    job_id="weekly_report",
    name="Weekly Team Report",
    interval=ScheduleInterval.WEEKLY,
    time="09:00",
    callback=generate_weekly_report
)

# Run scheduler
await scheduler.run_scheduler()
```

## API Reference

### ChatHistoryManager

#### Methods
- `setup()`: Initialize all components
- `analyze_period(start_time, end_time)`: Analyze specific time period
- `analyze_last_days(days)`: Analyze recent days
- `search_messages(query, platform, limit)`: Semantic search
- `get_analytics_summary(days)`: Get analytics data
- `export_knowledge_graph(output_path)`: Export graph to JSON

### KnowledgeGraphManager

#### Methods
- `add_entity(entity_id, entity_type, entity_name)`: Add entity
- `add_relationship(relationship)`: Add relationship
- `get_entity_relationships(entity_id)`: Get entity connections
- `find_entities_by_type(entity_type)`: Find entities by type

### VectorStoreManager

#### Methods
- `add_message(message)`: Add message to vector store
- `search_similar_messages(query, n_results, platform)`: Semantic search
- `get_message_by_id(message_id)`: Get specific message

## Data Structures

### NormalizedMessage
```python
@dataclass
class NormalizedMessage:
    message_id: str
    platform: ChatPlatform
    channel_id: str
    channel_name: str
    sender_id: str
    sender_name: str
    timestamp: datetime
    content: str
    mentions: List[str]
    attachments: List[Dict]
    # ... other fields
```

### EntityRelationship
```python
@dataclass
class EntityRelationship:
    source_entity: str
    target_entity: str
    relationship_type: str
    strength: float
    context: str
    timestamp: datetime
    message_id: str
```

## Analytics & Insights

### Available Analytics
- **Entity Counts**: Number of people, topics, projects, channels
- **Relationship Strengths**: Connection weights between entities
- **Activity Patterns**: Message frequency and timing
- **Platform Usage**: Cross-platform communication patterns

### Example Queries
```python
# Find most active users
people = manager.find_entities_by_type('person')
# Get user relationships and sort by activity

# Find trending topics
topics = manager.find_entities_by_type('topic')
# Analyze relationship growth over time

# Project collaboration networks
projects = manager.find_entities_by_type('project')
# Map people working on each project
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Install optional dependencies: `pip install pandas numpy sentence-transformers chromadb`
   - Module will work with fallback features if dependencies missing

2. **Database Locked**
   - Close other connections to SQLite database
   - Check file permissions on database directory

3. **Memory Issues**
   - Reduce batch size in configuration
   - Process smaller date ranges
   - Use local embedding models

4. **Empty Results**
   - Verify export paths are correct
   - Check date ranges for messages
   - Ensure platform connectors are configured

### Performance Optimization

1. **Batch Processing**
   - Adjust `batch_size` in configuration
   - Process messages in smaller chunks
   - Use parallel processing for multiple platforms

2. **Memory Management**
   - Use streaming for large datasets
   - Clear processed batches from memory
   - Optimize embedding model selection

3. **Database Optimization**
   - Create indexes on frequently queried fields
   - Use database connection pooling
   - Regular database maintenance

## Contributing

### Adding New Platforms
1. Create new connector class inheriting from `PlatformConnector`
2. Implement `fetch_messages()` and `normalize_message()` methods
3. Add platform enum to `ChatPlatform`
4. Update configuration classes
5. Add tests and documentation

### Extending Entity Extraction
1. Add new patterns to `EntityExtractor`
2. Update relationship extraction logic
3. Add new entity types to knowledge graph schema
4. Update analytics calculations

## License

This module is part of the project-zohar system and follows the same licensing terms.

## Related Documentation

- [Main Project README](../../README.md)
- [MCP Email Server Guide](../../docs/mcp_email_server.md)
- [Metadata Search Guide](../../docs/metadata_search_guide.md)
- [Quick Setup Guide](../../docs/quick_setup_guide.md)
