#!/usr/bin/env python3
"""
Test and Example Usage for Chat History Parser Module

This file demonstrates the functionality of the chat history parser
and provides examples for different use cases.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.chat_history_parser import (
    ChatHistoryProcessor, 
    ChatPlatform, 
    NormalizedMessage,
    SlackConnector,
    create_chat_processor
)
from services.chat_history_manager import ChatHistoryManager
from services.chat_history_config import create_default_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_slack_data():
    """Create sample Slack export data for testing"""
    sample_data_dir = Path("./data/sample_slack_export")
    sample_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create users.json
    users_data = [
        {
            "id": "U123456",
            "name": "alice",
            "real_name": "Alice Smith",
            "profile": {"email": "alice@company.com"}
        },
        {
            "id": "U789012",
            "name": "bob",
            "real_name": "Bob Johnson",
            "profile": {"email": "bob@company.com"}
        },
        {
            "id": "U345678",
            "name": "charlie",
            "real_name": "Charlie Brown",
            "profile": {"email": "charlie@company.com"}
        }
    ]
    
    with open(sample_data_dir / "users.json", 'w') as f:
        json.dump(users_data, f, indent=2)
    
    # Create channels.json
    channels_data = [
        {
            "id": "C123456",
            "name": "general",
            "purpose": {"value": "General discussions"}
        },
        {
            "id": "C789012",
            "name": "project-alpha",
            "purpose": {"value": "Project Alpha development"}
        }
    ]
    
    with open(sample_data_dir / "channels.json", 'w') as f:
        json.dump(channels_data, f, indent=2)
    
    # Create sample messages for general channel
    general_dir = sample_data_dir / "general"
    general_dir.mkdir(exist_ok=True)
    
    # Get current timestamp for recent messages
    base_time = datetime.now().timestamp()
    
    general_messages = [
        {
            "type": "message",
            "user": "U123456",
            "text": "Good morning everyone! Ready for the weekly standup?",
            "ts": str(base_time - 3600)  # 1 hour ago
        },
        {
            "type": "message",
            "user": "U789012",
            "text": "Hi <@U123456>! Yes, I'm ready. Project Alpha is making good progress.",
            "ts": str(base_time - 3500)  # 58 minutes ago
        },
        {
            "type": "message",
            "user": "U345678",
            "text": "Great! Can we discuss the #deployment strategy for next week?",
            "ts": str(base_time - 3400)  # 56 minutes ago
        },
        {
            "type": "message",
            "user": "U123456",
            "text": "Sure! Let's move that discussion to #project-alpha channel",
            "ts": str(base_time - 3300)  # 55 minutes ago
        }
    ]
    
    with open(general_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json", 'w') as f:
        json.dump(general_messages, f, indent=2)
    
    # Create sample messages for project-alpha channel
    project_dir = sample_data_dir / "project-alpha"
    project_dir.mkdir(exist_ok=True)
    
    project_messages = [
        {
            "type": "message",
            "user": "U789012",
            "text": "Project Alpha status update: Backend API is 80% complete. Working on ticket #123.",
            "ts": str(base_time - 3200)  # 53 minutes ago
        },
        {
            "type": "message",
            "user": "U345678",
            "text": "Frontend integration is ready. We should test the deployment on staging server.",
            "ts": str(base_time - 3100)  # 51 minutes ago
        },
        {
            "type": "message",
            "user": "U123456",
            "text": "Excellent work team! <@U789012> <@U345678> let's schedule a demo for Friday.",
            "ts": str(base_time - 3000)  # 50 minutes ago
        }
    ]
    
    with open(project_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json", 'w') as f:
        json.dump(project_messages, f, indent=2)
    
    print(f"✅ Sample Slack data created in {sample_data_dir}")
    return str(sample_data_dir)


async def test_basic_functionality():
    """Test basic functionality with sample data"""
    print("\n🧪 Testing Basic Functionality")
    print("=" * 50)
    
    # Create sample data
    sample_export_path = create_sample_slack_data()
    
    # Create processor
    processor = create_chat_processor({
        'knowledge_graph_db': './data/test_knowledge_graph.db',
        'vector_store_db': './data/test_vector_store',
        'embedding_model': 'all-MiniLM-L6-v2'
    })
    
    # Register Slack connector
    slack_connector = SlackConnector(export_path=sample_export_path)
    processor.register_connector(ChatPlatform.SLACK, slack_connector)
    
    # Run analysis
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    print(f"📊 Running analysis from {start_time} to {end_time}")
    results = await processor.run_analysis_cycle(start_time, end_time)
    
    print(f"✅ Analysis complete!")
    print(f"   Total messages: {results['total_messages']}")
    print(f"   Total entities: {results['total_entities']}")
    print(f"   Total relationships: {results['total_relationships']}")
    
    # Test analytics
    analytics = processor.get_analytics_summary(1)
    print(f"\n📈 Analytics Summary:")
    print(f"   Entity counts: {analytics['entity_counts']}")
    
    return processor


async def test_search_functionality(processor):
    """Test search functionality"""
    print("\n🔍 Testing Search Functionality")
    print("=" * 50)
    
    # Test semantic search
    search_queries = [
        "project update",
        "deployment strategy",
        "standup meeting",
        "ticket progress"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        results = processor.vector_store.search_similar_messages(query, n_results=3)
        
        if results and 'documents' in results:
            for i, doc in enumerate(results['documents']):
                metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
                print(f"   📄 Result {i+1}: {doc[:100]}...")
                print(f"       Channel: {metadata.get('channel_name', 'unknown')}")
                print(f"       Sender: {metadata.get('sender_name', 'unknown')}")
        else:
            print(f"   ❌ No results found")


async def test_knowledge_graph(processor):
    """Test knowledge graph functionality"""
    print("\n🕸️  Testing Knowledge Graph")
    print("=" * 50)
    
    # Find entities by type
    entity_types = ['person', 'topic', 'project', 'channel']
    
    for entity_type in entity_types:
        entities = processor.knowledge_graph.find_entities_by_type(entity_type)
        print(f"\n👥 {entity_type.title()} entities ({len(entities)}):")
        for entity in entities[:5]:  # Show first 5
            print(f"   • {entity['entity_name']} (ID: {entity['entity_id']})")
    
    # Test relationship queries
    people = processor.knowledge_graph.find_entities_by_type('person')
    if people:
        person = people[0]
        print(f"\n🔗 Relationships for {person['entity_name']}:")
        relationships = processor.knowledge_graph.get_entity_relationships(person['entity_id'])
        for rel in relationships[:5]:  # Show first 5
            print(f"   • {rel['relationship_type']} -> {rel['target_entity']} (strength: {rel['strength']})")


async def test_manager_interface():
    """Test the high-level manager interface"""
    print("\n🎛️  Testing Manager Interface")
    print("=" * 50)
    
    # Create manager with sample data
    config = create_default_config()
    config.slack.export_path = create_sample_slack_data()
    config.database.knowledge_graph_db = './data/test_manager_kg.db'
    config.database.vector_store_db = './data/test_manager_vs'
    
    manager = ChatHistoryManager(config)
    await manager.setup()
    
    # Test system status
    status = manager.get_system_status()
    print(f"🖥️  System Status:")
    print(f"   Setup complete: {'✅' if status['setup_complete'] else '❌'}")
    print(f"   Registered platforms: {status['registered_platforms']}")
    
    # Test analysis
    print(f"\n📊 Running analysis...")
    results = await manager.analyze_last_days(1)
    print(f"   Messages: {results['total_messages']}")
    print(f"   Entities: {results['total_entities']}")
    
    # Test export
    export_path = "./data/test_export.json"
    if manager.export_knowledge_graph(export_path):
        print(f"✅ Knowledge graph exported to {export_path}")
    
    return manager


async def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🚨 Testing Error Handling")
    print("=" * 50)
    
    # Test with non-existent export path
    try:
        processor = create_chat_processor()
        slack_connector = SlackConnector(export_path="./non_existent_path")
        processor.register_connector(ChatPlatform.SLACK, slack_connector)
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        results = await processor.run_analysis_cycle(start_time, end_time)
        
        print(f"✅ Handled non-existent path gracefully")
        print(f"   Total messages processed: {results['total_messages']}")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    # Test with invalid date range
    try:
        processor = create_chat_processor()
        
        # Future date range
        start_time = datetime.now() + timedelta(days=1)
        end_time = datetime.now() + timedelta(days=2)
        results = await processor.run_analysis_cycle(start_time, end_time)
        
        print(f"✅ Handled invalid date range gracefully")
        print(f"   Total messages processed: {results['total_messages']}")
        
    except Exception as e:
        print(f"❌ Invalid date range test failed: {e}")


async def run_all_tests():
    """Run all tests"""
    print("🧪 Chat History Parser Module Tests")
    print("=" * 60)
    
    try:
        # Test 1: Basic functionality
        processor = await test_basic_functionality()
        
        # Test 2: Search functionality
        await test_search_functionality(processor)
        
        # Test 3: Knowledge graph
        await test_knowledge_graph(processor)
        
        # Test 4: Manager interface
        await test_manager_interface()
        
        # Test 5: Error handling
        await test_error_handling()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def create_example_config():
    """Create an example configuration file"""
    print("\n⚙️  Creating Example Configuration")
    print("=" * 50)
    
    config = create_default_config()
    
    # Customize for example
    config.slack.export_path = "./data/slack_export"
    config.processing.batch_size = 500
    config.scheduling.enable_scheduling = True
    config.scheduling.schedule_interval = "weekly"
    config.scheduling.schedule_time = "02:00"
    
    # Save to file
    from services.chat_history_config import save_config_to_file
    config_path = "./config/example_chat_history_config.json"
    save_config_to_file(config, config_path)
    
    print(f"✅ Example configuration saved to {config_path}")
    
    # Show configuration
    print(f"\n📋 Configuration Summary:")
    print(f"   Slack export path: {config.slack.export_path}")
    print(f"   Batch size: {config.processing.batch_size}")
    print(f"   Scheduling: {config.scheduling.enable_scheduling}")
    print(f"   Schedule interval: {config.scheduling.schedule_interval}")
    print(f"   Knowledge graph DB: {config.database.knowledge_graph_db}")
    print(f"   Vector store DB: {config.database.vector_store_db}")


if __name__ == "__main__":
    print("🚀 Chat History Parser Module Test Suite")
    print("=" * 60)
    
    # Ensure test directories exist
    Path("./data").mkdir(exist_ok=True)
    Path("./config").mkdir(exist_ok=True)
    
    # Create example configuration
    create_example_config()
    
    # Run all tests
    asyncio.run(run_all_tests())
    
    print("\n💡 Next Steps:")
    print("1. Configure your actual Slack export path or API tokens")
    print("2. Run: python src/services/chat_history_cli.py status")
    print("3. Run: python src/services/chat_history_cli.py analyze --slack-export /path/to/export")
    print("4. Explore the knowledge graph and search functionality")
