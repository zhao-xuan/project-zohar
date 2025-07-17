#!/usr/bin/env python3
"""
Multi-Platform Chat History Parser and Storage Module

This module provides comprehensive chat history parsing and storage capabilities
for multiple platforms (Slack, Teams, Discord, etc.) as described in the
autonomous multi-agent chat analysis system design.

Features:
- Multi-platform chat data ingestion and normalization
- Knowledge graph construction for entity relationships
- Vector database storage for semantic search
- Autonomous batch processing with chunking
- Local deployment focused (no cloud dependencies)
"""

import asyncio
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
import uuid
import hashlib
from collections import defaultdict

# Third-party imports
try:
    import pandas as pd
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    print("Please install required packages: pip install pandas numpy sentence-transformers chromadb")
    DEPENDENCIES_AVAILABLE = False
    
    # Provide fallback classes for missing dependencies
    class SentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name
            
        def encode(self, text):
            # Fallback: return dummy embedding
            return [0.0] * 384
    
    class chromadb:
        @staticmethod
        def PersistentClient(path):
            return None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatPlatform(Enum):
    """Supported chat platforms"""
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WECHAT = "wechat"
    GENERIC = "generic"


@dataclass
class NormalizedMessage:
    """Unified message structure for all platforms"""
    message_id: str
    platform: ChatPlatform
    channel_id: str
    channel_name: str
    thread_id: Optional[str]
    sender_id: str
    sender_name: str
    timestamp: datetime
    content: str
    message_type: str  # 'message', 'reply', 'edit', 'delete'
    mentions: List[str] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    reactions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: datetime = field(default_factory=datetime.now)


@dataclass
class EntityRelationship:
    """Represents a relationship between entities in the knowledge graph"""
    source_entity: str
    source_type: str  # 'person', 'topic', 'project', 'channel'
    target_entity: str
    target_type: str
    relationship_type: str  # 'mentions', 'member_of', 'discusses', 'leads'
    strength: float  # 0.0 to 1.0
    context: str
    timestamp: datetime
    message_id: str


@dataclass
class ChatBatch:
    """Represents a batch of messages for processing"""
    batch_id: str
    platform: ChatPlatform
    start_time: datetime
    end_time: datetime
    messages: List[NormalizedMessage]
    total_count: int
    processed_count: int = 0
    status: str = "pending"  # pending, processing, completed, failed


class PlatformConnector:
    """Base class for platform-specific connectors"""
    
    def __init__(self, platform: ChatPlatform):
        self.platform = platform
        
    async def fetch_messages(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch raw messages from the platform"""
        raise NotImplementedError
        
    def normalize_message(self, raw_message: Dict[str, Any]) -> NormalizedMessage:
        """Convert platform-specific message to normalized format"""
        raise NotImplementedError


class SlackConnector(PlatformConnector):
    """Slack-specific connector"""
    
    def __init__(self, export_path: Optional[str] = None, api_token: Optional[str] = None):
        super().__init__(ChatPlatform.SLACK)
        self.export_path = export_path
        self.api_token = api_token
        
    async def fetch_messages(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch messages from Slack export or API"""
        messages = []
        
        if self.export_path:
            messages = await self._fetch_from_export(start_time, end_time)
        elif self.api_token:
            messages = await self._fetch_from_api(start_time, end_time)
        else:
            logger.error("No Slack export path or API token provided")
            
        return messages
    
    async def _fetch_from_export(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch messages from Slack export JSON files"""
        messages = []
        export_path = Path(self.export_path)
        
        if not export_path.exists():
            logger.error(f"Slack export path does not exist: {export_path}")
            return messages
            
        # Load channel metadata
        channels_file = export_path / "channels.json"
        channels = {}
        if channels_file.exists():
            with open(channels_file, 'r', encoding='utf-8') as f:
                channels_data = json.load(f)
                channels = {ch['id']: ch for ch in channels_data}
        
        # Load user metadata
        users_file = export_path / "users.json"
        users = {}
        if users_file.exists():
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                users = {user['id']: user for user in users_data}
        
        # Process each channel directory
        for channel_dir in export_path.iterdir():
            if channel_dir.is_dir():
                channel_info = channels.get(channel_dir.name, {})
                
                for json_file in channel_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            daily_messages = json.load(f)
                            
                        for msg in daily_messages:
                            msg_time = datetime.fromtimestamp(float(msg.get('ts', 0)), tz=timezone.utc)
                            
                            if start_time <= msg_time <= end_time:
                                # Enhance message with metadata
                                msg['channel_id'] = channel_dir.name
                                msg['channel_name'] = channel_info.get('name', channel_dir.name)
                                msg['user_info'] = users.get(msg.get('user', ''), {})
                                messages.append(msg)
                                
                    except (json.JSONDecodeError, IOError) as e:
                        logger.error(f"Error reading {json_file}: {e}")
                        
        return messages
    
    async def _fetch_from_api(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch messages from Slack API (placeholder for future implementation)"""
        logger.warning("Slack API integration not implemented yet")
        return []
    
    def normalize_message(self, raw_message: Dict[str, Any]) -> NormalizedMessage:
        """Convert Slack message to normalized format"""
        user_info = raw_message.get('user_info', {})
        
        # Extract mentions
        mentions = []
        content = raw_message.get('text', '')
        mention_pattern = r'<@([A-Z0-9]+)>'
        mentions = re.findall(mention_pattern, content)
        
        # Clean up content (remove Slack formatting)
        clean_content = re.sub(r'<@[A-Z0-9]+>', lambda m: f"@{user_info.get('name', 'unknown')}", content)
        clean_content = re.sub(r'<#[A-Z0-9]+\|([^>]+)>', r'#\1', clean_content)
        clean_content = re.sub(r'<([^>]+)>', r'\1', clean_content)
        
        return NormalizedMessage(
            message_id=raw_message.get('ts', str(uuid.uuid4())),
            platform=ChatPlatform.SLACK,
            channel_id=raw_message.get('channel_id', ''),
            channel_name=raw_message.get('channel_name', ''),
            thread_id=raw_message.get('thread_ts'),
            sender_id=raw_message.get('user', ''),
            sender_name=user_info.get('name', 'unknown'),
            timestamp=datetime.fromtimestamp(float(raw_message.get('ts', 0)), tz=timezone.utc),
            content=clean_content,
            message_type=raw_message.get('subtype', 'message'),
            mentions=mentions,
            attachments=raw_message.get('attachments', []),
            reactions=raw_message.get('reactions', []),
            metadata=raw_message
        )


class TeamsConnector(PlatformConnector):
    """Microsoft Teams connector"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        super().__init__(ChatPlatform.TEAMS)
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def fetch_messages(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetch messages from Microsoft Graph API (placeholder)"""
        logger.warning("Teams API integration not implemented yet")
        return []
    
    def normalize_message(self, raw_message: Dict[str, Any]) -> NormalizedMessage:
        """Convert Teams message to normalized format"""
        # Placeholder implementation
        return NormalizedMessage(
            message_id=raw_message.get('id', str(uuid.uuid4())),
            platform=ChatPlatform.TEAMS,
            channel_id=raw_message.get('channelId', ''),
            channel_name=raw_message.get('channelName', ''),
            thread_id=raw_message.get('replyToId'),
            sender_id=raw_message.get('from', {}).get('user', {}).get('id', ''),
            sender_name=raw_message.get('from', {}).get('user', {}).get('displayName', ''),
            timestamp=datetime.fromisoformat(raw_message.get('createdDateTime', datetime.now().isoformat())),
            content=raw_message.get('body', {}).get('content', ''),
            message_type='message',
            mentions=[],
            attachments=raw_message.get('attachments', []),
            reactions=[],
            metadata=raw_message
        )


class KnowledgeGraphManager:
    """Manages the knowledge graph for entity relationships"""
    
    def __init__(self, db_path: str = "./data/knowledge_graph.db"):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Initialize SQLite database for knowledge graph"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Relationships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                relationship_id TEXT PRIMARY KEY,
                source_entity TEXT NOT NULL,
                target_entity TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL NOT NULL,
                context TEXT,
                message_id TEXT,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_entity) REFERENCES entities (entity_id),
                FOREIGN KEY (target_entity) REFERENCES entities (entity_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON entities (entity_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationship_type ON relationships (relationship_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_entity ON relationships (source_entity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_entity ON relationships (target_entity)')
        
        conn.commit()
        conn.close()
    
    def add_entity(self, entity_id: str, entity_type: str, entity_name: str, metadata: Dict[str, Any] = None):
        """Add or update an entity in the knowledge graph"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO entities (entity_id, entity_type, entity_name, metadata, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (entity_id, entity_type, entity_name, json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
    
    def add_relationship(self, relationship: EntityRelationship):
        """Add a relationship to the knowledge graph"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        relationship_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT OR REPLACE INTO relationships 
            (relationship_id, source_entity, target_entity, relationship_type, strength, context, message_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            relationship_id,
            relationship.source_entity,
            relationship.target_entity,
            relationship.relationship_type,
            relationship.strength,
            relationship.context,
            relationship.message_id,
            relationship.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific entity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM relationships 
            WHERE source_entity = ? OR target_entity = ?
            ORDER BY strength DESC
        ''', (entity_id, entity_id))
        
        relationships = []
        for row in cursor.fetchall():
            relationships.append({
                'relationship_id': row[0],
                'source_entity': row[1],
                'target_entity': row[2],
                'relationship_type': row[3],
                'strength': row[4],
                'context': row[5],
                'message_id': row[6],
                'timestamp': row[7]
            })
        
        conn.close()
        return relationships
    
    def find_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Find all entities of a specific type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM entities WHERE entity_type = ?
            ORDER BY entity_name
        ''', (entity_type,))
        
        entities = []
        for row in cursor.fetchall():
            entities.append({
                'entity_id': row[0],
                'entity_type': row[1],
                'entity_name': row[2],
                'metadata': json.loads(row[3] or '{}'),
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        conn.close()
        return entities


class VectorStoreManager:
    """Manages vector storage for semantic search"""
    
    def __init__(self, db_path: str = "./data/vector_store", embedding_model: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Vector store dependencies not available. Using fallback storage.")
            self.embedding_model = SentenceTransformer(embedding_model)
            self.client = None
            self.collection = None
            self.fallback_storage = {}
            return
            
        self.embedding_model = SentenceTransformer(embedding_model)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="chat_messages",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_message(self, message: NormalizedMessage):
        """Add a message to the vector store"""
        if not DEPENDENCIES_AVAILABLE:
            # Fallback: store in simple dictionary
            self.fallback_storage[message.message_id] = {
                'content': message.content,
                'metadata': {
                    "platform": message.platform.value,
                    "channel_id": message.channel_id,
                    "channel_name": message.channel_name,
                    "sender_id": message.sender_id,
                    "sender_name": message.sender_name,
                    "timestamp": message.timestamp.isoformat(),
                    "message_type": message.message_type,
                    "mentions": json.dumps(message.mentions),
                    "has_attachments": len(message.attachments) > 0
                }
            }
            return
        
        # Create embedding
        embedding = self.embedding_model.encode(message.content).tolist()
        
        # Prepare metadata
        metadata = {
            "platform": message.platform.value,
            "channel_id": message.channel_id,
            "channel_name": message.channel_name,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "timestamp": message.timestamp.isoformat(),
            "message_type": message.message_type,
            "mentions": json.dumps(message.mentions),
            "has_attachments": len(message.attachments) > 0
        }
        
        # Add to collection
        self.collection.add(
            embeddings=[embedding],
            documents=[message.content],
            metadatas=[metadata],
            ids=[message.message_id]
        )
    
    def search_similar_messages(self, query: str, n_results: int = 10, platform: Optional[ChatPlatform] = None) -> List[Dict[str, Any]]:
        """Search for similar messages using semantic search"""
        if not DEPENDENCIES_AVAILABLE:
            # Fallback: simple text search
            results = []
            for msg_id, msg_data in self.fallback_storage.items():
                if query.lower() in msg_data['content'].lower():
                    if platform is None or msg_data['metadata']['platform'] == platform.value:
                        results.append({
                            'id': msg_id,
                            'document': msg_data['content'],
                            'metadata': msg_data['metadata'],
                            'distance': 0.5  # dummy distance
                        })
            return {'ids': [r['id'] for r in results[:n_results]], 
                    'documents': [r['document'] for r in results[:n_results]],
                    'metadatas': [r['metadata'] for r in results[:n_results]]}
        
        query_embedding = self.embedding_model.encode(query).tolist()
        
        where_clause = None
        if platform:
            where_clause = {"platform": platform.value}
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
        
        return results
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID"""
        if not DEPENDENCIES_AVAILABLE:
            return self.fallback_storage.get(message_id)
        
        try:
            results = self.collection.get(ids=[message_id])
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
        return None


class EntityExtractor:
    """Extracts entities and relationships from chat messages"""
    
    def __init__(self):
        # Common patterns for entity extraction
        self.patterns = {
            'mention': r'@(\w+)',
            'hashtag': r'#(\w+)',
            'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'project': r'(?:project|proj)\s+([A-Z][a-zA-Z0-9_-]+)',
            'ticket': r'(?:ticket|issue|bug)\s*#?(\d+)',
            'deadline': r'(?:deadline|due|by)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        }
    
    def extract_entities(self, message: NormalizedMessage) -> List[Tuple[str, str, str]]:
        """Extract entities from a message. Returns list of (entity_id, entity_type, entity_name)"""
        entities = []
        content = message.content.lower()
        
        # Extract mentions
        for match in re.finditer(self.patterns['mention'], message.content):
            entity_name = match.group(1)
            entity_id = f"person_{entity_name}"
            entities.append((entity_id, 'person', entity_name))
        
        # Extract hashtags as topics
        for match in re.finditer(self.patterns['hashtag'], message.content):
            entity_name = match.group(1)
            entity_id = f"topic_{entity_name}"
            entities.append((entity_id, 'topic', entity_name))
        
        # Extract project names
        for match in re.finditer(self.patterns['project'], content):
            entity_name = match.group(1)
            entity_id = f"project_{entity_name}"
            entities.append((entity_id, 'project', entity_name))
        
        # Extract ticket numbers
        for match in re.finditer(self.patterns['ticket'], content):
            entity_name = match.group(1)
            entity_id = f"ticket_{entity_name}"
            entities.append((entity_id, 'ticket', entity_name))
        
        # Add channel as entity
        channel_id = f"channel_{message.channel_id}"
        entities.append((channel_id, 'channel', message.channel_name))
        
        # Add sender as entity
        sender_id = f"person_{message.sender_id}"
        entities.append((sender_id, 'person', message.sender_name))
        
        return entities
    
    def extract_relationships(self, message: NormalizedMessage, entities: List[Tuple[str, str, str]]) -> List[EntityRelationship]:
        """Extract relationships between entities"""
        relationships = []
        
        # Create person-to-channel membership
        sender_id = f"person_{message.sender_id}"
        channel_id = f"channel_{message.channel_id}"
        
        relationships.append(EntityRelationship(
            source_entity=sender_id,
            source_type='person',
            target_entity=channel_id,
            target_type='channel',
            relationship_type='member_of',
            strength=1.0,
            context=f"Active in {message.channel_name}",
            timestamp=message.timestamp,
            message_id=message.message_id
        ))
        
        # Create person-to-topic relationships
        for entity_id, entity_type, entity_name in entities:
            if entity_type == 'topic' and entity_id != sender_id:
                relationships.append(EntityRelationship(
                    source_entity=sender_id,
                    source_type='person',
                    target_entity=entity_id,
                    target_type='topic',
                    relationship_type='discusses',
                    strength=0.7,
                    context=f"Discussed {entity_name} in {message.channel_name}",
                    timestamp=message.timestamp,
                    message_id=message.message_id
                ))
        
        # Create person-to-project relationships
        for entity_id, entity_type, entity_name in entities:
            if entity_type == 'project' and entity_id != sender_id:
                relationships.append(EntityRelationship(
                    source_entity=sender_id,
                    source_type='person',
                    target_entity=entity_id,
                    target_type='project',
                    relationship_type='works_on',
                    strength=0.8,
                    context=f"Mentioned {entity_name} in {message.channel_name}",
                    timestamp=message.timestamp,
                    message_id=message.message_id
                ))
        
        # Create mention relationships
        for mention in message.mentions:
            mention_id = f"person_{mention}"
            relationships.append(EntityRelationship(
                source_entity=sender_id,
                source_type='person',
                target_entity=mention_id,
                target_type='person',
                relationship_type='mentions',
                strength=0.6,
                context=f"Mentioned in {message.channel_name}",
                timestamp=message.timestamp,
                message_id=message.message_id
            ))
        
        return relationships


class ChatHistoryProcessor:
    """Main processor for chat history analysis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.knowledge_graph = KnowledgeGraphManager(
            self.config.get('knowledge_graph_db', './data/knowledge_graph.db')
        )
        self.vector_store = VectorStoreManager(
            self.config.get('vector_store_db', './data/vector_store'),
            self.config.get('embedding_model', 'all-MiniLM-L6-v2')
        )
        self.entity_extractor = EntityExtractor()
        self.connectors = {}
        
    def register_connector(self, platform: ChatPlatform, connector: PlatformConnector):
        """Register a platform connector"""
        self.connectors[platform] = connector
    
    async def process_batch(self, batch: ChatBatch) -> Dict[str, Any]:
        """Process a batch of messages"""
        logger.info(f"Processing batch {batch.batch_id} with {len(batch.messages)} messages")
        
        batch.status = "processing"
        processed_messages = 0
        entity_count = 0
        relationship_count = 0
        
        for message in batch.messages:
            try:
                # Extract entities
                entities = self.entity_extractor.extract_entities(message)
                
                # Add entities to knowledge graph
                for entity_id, entity_type, entity_name in entities:
                    self.knowledge_graph.add_entity(entity_id, entity_type, entity_name)
                    entity_count += 1
                
                # Extract and add relationships
                relationships = self.entity_extractor.extract_relationships(message, entities)
                for relationship in relationships:
                    self.knowledge_graph.add_relationship(relationship)
                    relationship_count += 1
                
                # Add to vector store
                self.vector_store.add_message(message)
                
                processed_messages += 1
                
            except Exception as e:
                logger.error(f"Error processing message {message.message_id}: {e}")
                continue
        
        batch.processed_count = processed_messages
        batch.status = "completed"
        
        return {
            'batch_id': batch.batch_id,
            'processed_messages': processed_messages,
            'total_messages': len(batch.messages),
            'entities_added': entity_count,
            'relationships_added': relationship_count,
            'status': batch.status
        }
    
    async def ingest_platform_data(self, platform: ChatPlatform, start_time: datetime, end_time: datetime, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Ingest data from a specific platform"""
        if platform not in self.connectors:
            raise ValueError(f"No connector registered for platform {platform}")
        
        connector = self.connectors[platform]
        
        # Fetch raw messages
        logger.info(f"Fetching messages from {platform.value} ({start_time} to {end_time})")
        raw_messages = await connector.fetch_messages(start_time, end_time)
        
        # Normalize messages
        normalized_messages = []
        for raw_message in raw_messages:
            try:
                normalized = connector.normalize_message(raw_message)
                normalized_messages.append(normalized)
            except Exception as e:
                logger.error(f"Error normalizing message: {e}")
                continue
        
        # Create batches
        batches = []
        for i in range(0, len(normalized_messages), chunk_size):
            chunk = normalized_messages[i:i + chunk_size]
            batch = ChatBatch(
                batch_id=str(uuid.uuid4()),
                platform=platform,
                start_time=start_time,
                end_time=end_time,
                messages=chunk,
                total_count=len(chunk)
            )
            batches.append(batch)
        
        # Process batches
        results = []
        for batch in batches:
            result = await self.process_batch(batch)
            results.append(result)
        
        return results
    
    async def run_analysis_cycle(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Run a complete analysis cycle for all registered platforms"""
        logger.info(f"Starting analysis cycle ({start_time} to {end_time})")
        
        cycle_results = {
            'cycle_id': str(uuid.uuid4()),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'platforms': {},
            'total_messages': 0,
            'total_entities': 0,
            'total_relationships': 0,
            'status': 'running'
        }
        
        # Process each platform
        for platform in self.connectors.keys():
            try:
                platform_results = await self.ingest_platform_data(platform, start_time, end_time)
                
                platform_summary = {
                    'batches': len(platform_results),
                    'messages': sum(r['processed_messages'] for r in platform_results),
                    'entities': sum(r['entities_added'] for r in platform_results),
                    'relationships': sum(r['relationships_added'] for r in platform_results),
                    'results': platform_results
                }
                
                cycle_results['platforms'][platform.value] = platform_summary
                cycle_results['total_messages'] += platform_summary['messages']
                cycle_results['total_entities'] += platform_summary['entities']
                cycle_results['total_relationships'] += platform_summary['relationships']
                
            except Exception as e:
                logger.error(f"Error processing platform {platform.value}: {e}")
                cycle_results['platforms'][platform.value] = {'error': str(e)}
        
        cycle_results['status'] = 'completed'
        logger.info(f"Analysis cycle completed: {cycle_results['total_messages']} messages processed")
        
        return cycle_results
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Generate analytics summary for the last N days"""
        end_time = datetime.now()
        
        # Use timedelta instead of pandas.Timedelta for better compatibility
        from datetime import timedelta
        start_time = end_time - timedelta(days=days)
        
        # Get entities by type
        entity_stats = {}
        for entity_type in ['person', 'topic', 'project', 'channel']:
            entities = self.knowledge_graph.find_entities_by_type(entity_type)
            entity_stats[entity_type] = len(entities)
        
        # TODO: Add more sophisticated analytics
        # - Most active users
        # - Trending topics
        # - Channel activity
        # - Relationship strengths
        
        return {
            'period': f"{days} days",
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'entity_counts': entity_stats,
            'total_entities': sum(entity_stats.values())
        }


# Example usage and factory functions
def create_slack_connector(export_path: str = None, api_token: str = None) -> SlackConnector:
    """Factory function to create Slack connector"""
    return SlackConnector(export_path, api_token)


def create_teams_connector(client_id: str = None, client_secret: str = None) -> TeamsConnector:
    """Factory function to create Teams connector"""
    return TeamsConnector(client_id, client_secret)


def create_chat_processor(config: Dict[str, Any] = None) -> ChatHistoryProcessor:
    """Factory function to create chat history processor"""
    return ChatHistoryProcessor(config)


# Main function for testing
async def main():
    """Example usage of the chat history processor"""
    # Create processor
    processor = create_chat_processor({
        'knowledge_graph_db': './data/test_knowledge_graph.db',
        'vector_store_db': './data/test_vector_store',
        'embedding_model': 'all-MiniLM-L6-v2'
    })
    
    # Register Slack connector with example export path
    slack_connector = create_slack_connector(export_path="./data/slack_export")
    processor.register_connector(ChatPlatform.SLACK, slack_connector)
    
    # Run analysis cycle for last 7 days
    end_time = datetime.now()
    from datetime import timedelta
    start_time = end_time - timedelta(days=7)
    
    try:
        results = await processor.run_analysis_cycle(start_time, end_time)
        print(f"Analysis completed: {json.dumps(results, indent=2)}")
        
        # Get analytics summary
        analytics = processor.get_analytics_summary(days=7)
        print(f"Analytics summary: {json.dumps(analytics, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())
