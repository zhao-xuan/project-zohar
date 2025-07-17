#!/usr/bin/env python3
"""
Simple Chat History Parser Example

This is a simple example showing how to use the chat history parser
without complex dependencies.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import re

# Simple example without external dependencies
class SimpleChatAnalyzer:
    """Simple chat analyzer for demonstration"""
    
    def __init__(self, db_path="./data/simple_chat.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Setup SQLite database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                platform TEXT,
                channel TEXT,
                sender TEXT,
                content TEXT,
                timestamp TEXT,
                mentions TEXT,
                topics TEXT
            )
        ''')
        
        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT,
                name TEXT,
                count INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def extract_entities(self, content):
        """Extract entities from message content"""
        entities = {
            'mentions': re.findall(r'@(\w+)', content),
            'topics': re.findall(r'#(\w+)', content),
            'projects': re.findall(r'(?:project|proj)\s+([A-Z][a-zA-Z0-9_-]+)', content.lower()),
            'tickets': re.findall(r'(?:ticket|issue)\s*#?(\d+)', content.lower())
        }
        return entities
    
    def process_message(self, platform, channel, sender, content, timestamp=None):
        """Process a single message"""
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        message_id = str(uuid.uuid4())
        entities = self.extract_entities(content)
        
        # Store message
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (id, platform, channel, sender, content, timestamp, mentions, topics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id,
            platform,
            channel,
            sender,
            content,
            timestamp,
            json.dumps(entities['mentions']),
            json.dumps(entities['topics'])
        ))
        
        # Store entities
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                cursor.execute('''
                    INSERT OR REPLACE INTO entities (id, type, name, count)
                    VALUES (?, ?, ?, COALESCE((SELECT count FROM entities WHERE id = ?), 0) + 1)
                ''', (f"{entity_type}_{entity}", entity_type, entity, f"{entity_type}_{entity}"))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Processed message from {sender} in #{channel}")
        return message_id
    
    def analyze_slack_export(self, export_path):
        """Analyze Slack export directory"""
        export_dir = Path(export_path)
        if not export_dir.exists():
            print(f"❌ Export directory not found: {export_path}")
            return
        
        # Load users
        users = {}
        users_file = export_dir / "users.json"
        if users_file.exists():
            with open(users_file, 'r') as f:
                users_data = json.load(f)
                users = {user['id']: user['name'] for user in users_data}
        
        # Load channels
        channels = {}
        channels_file = export_dir / "channels.json"
        if channels_file.exists():
            with open(channels_file, 'r') as f:
                channels_data = json.load(f)
                channels = {ch['id']: ch['name'] for ch in channels_data}
        
        # Process messages
        processed_count = 0
        for channel_dir in export_dir.iterdir():
            if channel_dir.is_dir():
                channel_name = channels.get(channel_dir.name, channel_dir.name)
                
                for json_file in channel_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            messages = json.load(f)
                        
                        for msg in messages:
                            if msg.get('type') == 'message' and msg.get('text'):
                                sender = users.get(msg.get('user', ''), 'unknown')
                                self.process_message(
                                    platform='slack',
                                    channel=channel_name,
                                    sender=sender,
                                    content=msg['text'],
                                    timestamp=datetime.fromtimestamp(float(msg['ts'])).isoformat()
                                )
                                processed_count += 1
                    
                    except Exception as e:
                        print(f"⚠️  Error processing {json_file}: {e}")
        
        print(f"✅ Processed {processed_count} messages")
        return processed_count
    
    def get_analytics(self):
        """Get simple analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Message counts
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        cursor.execute("SELECT platform, COUNT(*) FROM messages GROUP BY platform")
        platform_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT channel, COUNT(*) FROM messages GROUP BY channel ORDER BY COUNT(*) DESC LIMIT 10")
        top_channels = cursor.fetchall()
        
        cursor.execute("SELECT sender, COUNT(*) FROM messages GROUP BY sender ORDER BY COUNT(*) DESC LIMIT 10")
        top_senders = cursor.fetchall()
        
        # Entity counts
        cursor.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")
        entity_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT name, count FROM entities ORDER BY count DESC LIMIT 10")
        top_entities = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_messages': total_messages,
            'platform_counts': platform_counts,
            'top_channels': top_channels,
            'top_senders': top_senders,
            'entity_counts': entity_counts,
            'top_entities': top_entities
        }
    
    def search_messages(self, query):
        """Simple text search"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT platform, channel, sender, content, timestamp
            FROM messages
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT 20
        ''', (f'%{query}%',))
        
        results = cursor.fetchall()
        conn.close()
        
        return results


def create_sample_data():
    """Create sample data for testing"""
    sample_dir = Path("./data/sample_slack_export")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # Create users.json
    users = [
        {"id": "U123", "name": "alice", "real_name": "Alice Smith"},
        {"id": "U456", "name": "bob", "real_name": "Bob Johnson"},
        {"id": "U789", "name": "charlie", "real_name": "Charlie Brown"}
    ]
    
    with open(sample_dir / "users.json", 'w') as f:
        json.dump(users, f, indent=2)
    
    # Create channels.json
    channels = [
        {"id": "C123", "name": "general"},
        {"id": "C456", "name": "project-alpha"}
    ]
    
    with open(sample_dir / "channels.json", 'w') as f:
        json.dump(channels, f, indent=2)
    
    # Create sample messages
    general_dir = sample_dir / "general"
    general_dir.mkdir(exist_ok=True)
    
    now = datetime.now().timestamp()
    messages = [
        {
            "type": "message",
            "user": "U123",
            "text": "Good morning team! Let's discuss project Alpha progress.",
            "ts": str(now - 3600)
        },
        {
            "type": "message",
            "user": "U456",
            "text": "Hi @alice! I've completed ticket #42 and ready for review.",
            "ts": str(now - 3400)
        },
        {
            "type": "message",
            "user": "U789",
            "text": "Great work @bob! The #deployment looks good. Project Alpha is on track.",
            "ts": str(now - 3200)
        },
        {
            "type": "message",
            "user": "U123",
            "text": "Thanks @charlie! Let's schedule the demo for Friday. #standup",
            "ts": str(now - 3000)
        }
    ]
    
    with open(general_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json", 'w') as f:
        json.dump(messages, f, indent=2)
    
    print(f"✅ Sample data created in {sample_dir}")
    return str(sample_dir)


def main():
    """Main function demonstrating the chat analyzer"""
    print("🚀 Simple Chat History Parser Example")
    print("=" * 50)
    
    # Create sample data
    sample_export = create_sample_data()
    
    # Initialize analyzer
    analyzer = SimpleChatAnalyzer("./data/simple_chat.db")
    
    # Process sample data
    print("\n📊 Processing sample Slack export...")
    analyzer.analyze_slack_export(sample_export)
    
    # Get analytics
    print("\n📈 Analytics Results:")
    analytics = analyzer.get_analytics()
    
    print(f"Total messages: {analytics['total_messages']}")
    print(f"Platform counts: {analytics['platform_counts']}")
    print(f"Entity counts: {analytics['entity_counts']}")
    
    print("\n👥 Top senders:")
    for sender, count in analytics['top_senders']:
        print(f"  {sender}: {count} messages")
    
    print("\n💬 Top channels:")
    for channel, count in analytics['top_channels']:
        print(f"  #{channel}: {count} messages")
    
    print("\n🏷️  Top entities:")
    for entity, count in analytics['top_entities']:
        print(f"  {entity}: {count} mentions")
    
    # Test search
    print("\n🔍 Search Results for 'project':")
    search_results = analyzer.search_messages("project")
    for platform, channel, sender, content, timestamp in search_results:
        print(f"  [{platform}] #{channel} - {sender}: {content[:100]}...")
    
    print("\n✅ Simple chat analysis complete!")
    print("\nNext steps:")
    print("1. Replace sample data with your actual Slack export")
    print("2. Explore the full chat_history_parser module for advanced features")
    print("3. Try: python src/services/chat_history_cli.py --help")


if __name__ == "__main__":
    main()
