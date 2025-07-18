"""
Conversation Memory for Project Zohar.

This module manages conversation history, user preferences, and provides
persistent storage for agent interactions.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass, asdict

from config.settings import get_settings
from ..agent.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationEntry:
    """A single conversation entry."""
    id: str
    user_id: str
    user_message: str
    assistant_response: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationEntry':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class UserPreferences:
    """User preferences and settings."""
    user_id: str
    language: str = "en"
    timezone: str = "UTC"
    communication_style: str = "professional"
    response_length: str = "medium"
    topics_of_interest: List[str] = None
    privacy_level: str = "high"
    notifications_enabled: bool = True
    auto_summarization: bool = True
    data_retention_days: int = 365
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.topics_of_interest is None:
            self.topics_of_interest = []
        if self.custom_settings is None:
            self.custom_settings = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(**data)


class ConversationMemory:
    """
    Manages conversation history and user preferences.
    
    This class provides persistent storage for:
    - Conversation history between users and agents
    - User preferences and settings
    - Metadata and context information
    """
    
    def __init__(self, user_id: str, db_path: Optional[Path] = None):
        """
        Initialize conversation memory.
        
        Args:
            user_id: Unique identifier for the user
            db_path: Path to the SQLite database file
        """
        self.user_id = user_id
        self.settings = get_settings()
        
        # Database setup
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = self.settings.data_dir / "conversations.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
        # Cache for recent conversations
        self._conversation_cache: List[ConversationEntry] = []
        self._cache_limit = 100
        self._cache_loaded = False
        
        # User preferences cache
        self._user_preferences: Optional[UserPreferences] = None
        
        logger.info(f"Conversation memory initialized for user {user_id}")
    
    def _initialize_database(self):
        """Initialize the SQLite database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        assistant_response TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        context TEXT,
                        metadata TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # User preferences table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        language TEXT DEFAULT 'en',
                        timezone TEXT DEFAULT 'UTC',
                        communication_style TEXT DEFAULT 'professional',
                        response_length TEXT DEFAULT 'medium',
                        topics_of_interest TEXT,
                        privacy_level TEXT DEFAULT 'high',
                        notifications_enabled BOOLEAN DEFAULT 1,
                        auto_summarization BOOLEAN DEFAULT 1,
                        data_retention_days INTEGER DEFAULT 365,
                        custom_settings TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                    ON conversations(user_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
                    ON conversations(timestamp)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def initialize(self) -> bool:
        """
        Initialize the memory system.
        
        Returns:
            Success status
        """
        try:
            # Load user preferences
            await self._load_user_preferences()
            
            # Load recent conversations into cache
            await self._load_conversation_cache()
            
            logger.info(f"Memory system initialized for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory system: {e}")
            return False
    
    async def add_interaction(
        self,
        user_message: str,
        assistant_response: str,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new conversation interaction.
        
        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            context: Optional context information
            metadata: Optional metadata
            
        Returns:
            Conversation entry ID
        """
        try:
            import uuid
            
            entry_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            entry = ConversationEntry(
                id=entry_id,
                user_id=self.user_id,
                user_message=user_message,
                assistant_response=assistant_response,
                timestamp=timestamp,
                context=context,
                metadata=metadata
            )
            
            # Save to database
            await self._save_conversation_entry(entry)
            
            # Add to cache
            self._conversation_cache.append(entry)
            
            # Maintain cache size
            if len(self._conversation_cache) > self._cache_limit:
                self._conversation_cache = self._conversation_cache[-self._cache_limit:]
            
            logger.debug(f"Added conversation entry {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to add conversation interaction: {e}")
            raise
    
    async def get_recent_history(
        self,
        limit: int = 10,
        include_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.
        
        Args:
            limit: Maximum number of entries to return
            include_context: Whether to include context information
            
        Returns:
            List of conversation entries
        """
        try:
            if not self._cache_loaded:
                await self._load_conversation_cache()
            
            # Get recent entries from cache
            recent_entries = self._conversation_cache[-limit:]
            
            # Convert to dictionary format
            history = []
            for entry in recent_entries:
                entry_dict = {
                    "user_message": entry.user_message,
                    "assistant_response": entry.assistant_response,
                    "timestamp": entry.timestamp
                }
                
                if include_context and entry.context:
                    entry_dict["context"] = entry.context
                
                history.append(entry_dict)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get recent history: {e}")
            return []
    
    async def search_conversations(
        self,
        query: str,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ConversationEntry]:
        """
        Search conversations by content.
        
        Args:
            query: Search query
            limit: Maximum number of results
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of matching conversation entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query
                sql = """
                    SELECT id, user_id, user_message, assistant_response, 
                           timestamp, context, metadata
                    FROM conversations 
                    WHERE user_id = ? AND (
                        user_message LIKE ? OR assistant_response LIKE ?
                    )
                """
                params = [self.user_id, f"%{query}%", f"%{query}%"]
                
                # Add date filters
                if start_date:
                    sql += " AND timestamp >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    sql += " AND timestamp <= ?"
                    params.append(end_date.isoformat())
                
                sql += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # Convert to ConversationEntry objects
                results = []
                for row in rows:
                    entry = ConversationEntry(
                        id=row[0],
                        user_id=row[1],
                        user_message=row[2],
                        assistant_response=row[3],
                        timestamp=row[4],
                        context=json.loads(row[5]) if row[5] else None,
                        metadata=json.loads(row[6]) if row[6] else None
                    )
                    results.append(entry)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
    
    async def get_user_preferences(self) -> UserPreferences:
        """
        Get user preferences.
        
        Returns:
            User preferences object
        """
        if self._user_preferences is None:
            await self._load_user_preferences()
        
        return self._user_preferences
    
    async def update_user_preferences(self, preferences: Dict[str, Any]):
        """
        Update user preferences.
        
        Args:
            preferences: Dictionary of preference updates
        """
        try:
            if self._user_preferences is None:
                await self._load_user_preferences()
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(self._user_preferences, key):
                    setattr(self._user_preferences, key, value)
            
            # Save to database
            await self._save_user_preferences()
            
            logger.info(f"Updated preferences for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            raise
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total conversations
                cursor.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                    (self.user_id,)
                )
                total_conversations = cursor.fetchone()[0]
                
                # Conversations in last 30 days
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM conversations 
                    WHERE user_id = ? AND timestamp >= ?
                """, (self.user_id, thirty_days_ago))
                recent_conversations = cursor.fetchone()[0]
                
                # Average message length
                cursor.execute("""
                    SELECT AVG(LENGTH(user_message)) FROM conversations 
                    WHERE user_id = ?
                """, (self.user_id,))
                avg_message_length = cursor.fetchone()[0] or 0
                
                # Most active day
                cursor.execute("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM conversations 
                    WHERE user_id = ?
                    GROUP BY DATE(timestamp)
                    ORDER BY count DESC
                    LIMIT 1
                """, (self.user_id,))
                most_active_result = cursor.fetchone()
                most_active_day = most_active_result[0] if most_active_result else None
                
                return {
                    "total_conversations": total_conversations,
                    "recent_conversations": recent_conversations,
                    "average_message_length": round(avg_message_length, 2),
                    "most_active_day": most_active_day,
                    "memory_initialized": self._cache_loaded,
                    "cache_size": len(self._conversation_cache)
                }
                
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return {}
    
    async def cleanup_old_conversations(self, days_to_keep: Optional[int] = None):
        """
        Clean up old conversations based on retention policy.
        
        Args:
            days_to_keep: Number of days to keep (uses user preference if None)
        """
        try:
            if days_to_keep is None:
                preferences = await self.get_user_preferences()
                days_to_keep = preferences.data_retention_days
            
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count conversations to be deleted
                cursor.execute("""
                    SELECT COUNT(*) FROM conversations 
                    WHERE user_id = ? AND timestamp < ?
                """, (self.user_id, cutoff_date))
                count_to_delete = cursor.fetchone()[0]
                
                if count_to_delete > 0:
                    # Delete old conversations
                    cursor.execute("""
                        DELETE FROM conversations 
                        WHERE user_id = ? AND timestamp < ?
                    """, (self.user_id, cutoff_date))
                    
                    conn.commit()
                    
                    logger.info(f"Cleaned up {count_to_delete} old conversations for user {self.user_id}")
                    
                    # Reload cache
                    await self._load_conversation_cache()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            raise
    
    async def export_conversations(self) -> Dict[str, Any]:
        """
        Export all conversations for backup or transfer.
        
        Returns:
            Dictionary containing all conversation data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, user_id, user_message, assistant_response, 
                           timestamp, context, metadata
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY timestamp
                """, (self.user_id,))
                
                rows = cursor.fetchall()
                
                conversations = []
                for row in rows:
                    conversations.append({
                        "id": row[0],
                        "user_id": row[1],
                        "user_message": row[2],
                        "assistant_response": row[3],
                        "timestamp": row[4],
                        "context": json.loads(row[5]) if row[5] else None,
                        "metadata": json.loads(row[6]) if row[6] else None
                    })
                
                return {
                    "user_id": self.user_id,
                    "conversations": conversations,
                    "export_timestamp": datetime.now().isoformat(),
                    "total_count": len(conversations)
                }
                
        except Exception as e:
            logger.error(f"Failed to export conversations: {e}")
            return {}
    
    async def clear(self):
        """Clear all conversation history for this user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM conversations WHERE user_id = ?",
                    (self.user_id,)
                )
                
                conn.commit()
            
            # Clear cache
            self._conversation_cache.clear()
            
            logger.info(f"Cleared all conversations for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear conversations: {e}")
            raise
    
    async def close(self):
        """Close the memory system and cleanup resources."""
        try:
            # Clear cache
            self._conversation_cache.clear()
            self._cache_loaded = False
            self._user_preferences = None
            
            logger.info(f"Memory system closed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to close memory system: {e}")
    
    async def is_initialized(self) -> bool:
        """Check if the memory system is initialized."""
        return self._cache_loaded and self._user_preferences is not None
    
    # Private methods
    
    async def _save_conversation_entry(self, entry: ConversationEntry):
        """Save a conversation entry to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO conversations 
                    (id, user_id, user_message, assistant_response, timestamp, context, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.user_id,
                    entry.user_message,
                    entry.assistant_response,
                    entry.timestamp,
                    json.dumps(entry.context) if entry.context else None,
                    json.dumps(entry.metadata) if entry.metadata else None
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save conversation entry: {e}")
            raise
    
    async def _load_conversation_cache(self):
        """Load recent conversations into cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, user_id, user_message, assistant_response, 
                           timestamp, context, metadata
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (self.user_id, self._cache_limit))
                
                rows = cursor.fetchall()
                
                # Convert to ConversationEntry objects
                self._conversation_cache.clear()
                for row in reversed(rows):  # Reverse to maintain chronological order
                    entry = ConversationEntry(
                        id=row[0],
                        user_id=row[1],
                        user_message=row[2],
                        assistant_response=row[3],
                        timestamp=row[4],
                        context=json.loads(row[5]) if row[5] else None,
                        metadata=json.loads(row[6]) if row[6] else None
                    )
                    self._conversation_cache.append(entry)
            
            self._cache_loaded = True
            logger.debug(f"Loaded {len(self._conversation_cache)} conversations into cache")
            
        except Exception as e:
            logger.error(f"Failed to load conversation cache: {e}")
            raise
    
    async def _load_user_preferences(self):
        """Load user preferences from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT language, timezone, communication_style, response_length,
                           topics_of_interest, privacy_level, notifications_enabled,
                           auto_summarization, data_retention_days, custom_settings
                    FROM user_preferences 
                    WHERE user_id = ?
                """, (self.user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    self._user_preferences = UserPreferences(
                        user_id=self.user_id,
                        language=row[0],
                        timezone=row[1],
                        communication_style=row[2],
                        response_length=row[3],
                        topics_of_interest=json.loads(row[4]) if row[4] else [],
                        privacy_level=row[5],
                        notifications_enabled=bool(row[6]),
                        auto_summarization=bool(row[7]),
                        data_retention_days=row[8],
                        custom_settings=json.loads(row[9]) if row[9] else {}
                    )
                else:
                    # Create default preferences
                    self._user_preferences = UserPreferences(user_id=self.user_id)
                    await self._save_user_preferences()
            
            logger.debug(f"Loaded user preferences for {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")
            # Create default preferences on error
            self._user_preferences = UserPreferences(user_id=self.user_id)
    
    async def _save_user_preferences(self):
        """Save user preferences to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, language, timezone, communication_style, response_length,
                     topics_of_interest, privacy_level, notifications_enabled,
                     auto_summarization, data_retention_days, custom_settings, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    self._user_preferences.user_id,
                    self._user_preferences.language,
                    self._user_preferences.timezone,
                    self._user_preferences.communication_style,
                    self._user_preferences.response_length,
                    json.dumps(self._user_preferences.topics_of_interest),
                    self._user_preferences.privacy_level,
                    int(self._user_preferences.notifications_enabled),
                    int(self._user_preferences.auto_summarization),
                    self._user_preferences.data_retention_days,
                    json.dumps(self._user_preferences.custom_settings)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
            raise
