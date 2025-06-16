"""
Conversation Memory Management
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.config.settings import settings


class ConversationMemory:
    """
    Manages conversation memory and context for both personal and public bots
    """
    
    def __init__(self, bot_type: str = "personal"):
        self.bot_type = bot_type
        self.db_path = settings.database.sqlite_db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    bot_type TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_id 
                ON conversations(conversation_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_type 
                ON conversations(bot_type)
            """)
    
    async def add_exchange(
        self, 
        conversation_id: str, 
        user_message: str, 
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a conversation exchange to memory
        
        Args:
            conversation_id: Unique conversation identifier
            user_message: The user's message
            assistant_response: The assistant's response
            metadata: Optional metadata about the exchange
        """
        if metadata is None:
            metadata = {}
        
        metadata_json = json.dumps(metadata)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations 
                (conversation_id, bot_type, user_message, assistant_response, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, self.bot_type, user_message, assistant_response, metadata_json))
    
    async def get_context(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation context for a specific conversation
        
        Args:
            conversation_id: The conversation to retrieve
            limit: Maximum number of exchanges to return
            
        Returns:
            List of conversation exchanges
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_message, assistant_response, timestamp, metadata
                FROM conversations
                WHERE conversation_id = ? AND bot_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (conversation_id, self.bot_type, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "user_message": row["user_message"],
                    "assistant_response": row["assistant_response"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"])
                })
            
            # Reverse to get chronological order
            return list(reversed(results))
    
    async def get_recent_conversations(
        self, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation summaries
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of recent conversations with basic info
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT conversation_id, 
                       COUNT(*) as exchange_count,
                       MAX(timestamp) as last_activity,
                       MIN(timestamp) as started_at
                FROM conversations
                WHERE bot_type = ?
                GROUP BY conversation_id
                ORDER BY last_activity DESC
                LIMIT ?
            """, (self.bot_type, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "conversation_id": row["conversation_id"],
                    "exchange_count": row["exchange_count"],
                    "last_activity": row["last_activity"],
                    "started_at": row["started_at"]
                })
            
            return results
    
    async def search_conversations(
        self, 
        query: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search through conversation history
        
        Args:
            query: Search term
            limit: Maximum number of results
            
        Returns:
            List of matching conversation exchanges
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            search_term = f"%{query}%"
            cursor = conn.execute("""
                SELECT conversation_id, user_message, assistant_response, timestamp
                FROM conversations
                WHERE bot_type = ? 
                AND (user_message LIKE ? OR assistant_response LIKE ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.bot_type, search_term, search_term, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "conversation_id": row["conversation_id"],
                    "user_message": row["user_message"],
                    "assistant_response": row["assistant_response"],
                    "timestamp": row["timestamp"]
                })
            
            return results
    
    async def clear_conversation(self, conversation_id: str):
        """
        Clear a specific conversation from memory
        
        Args:
            conversation_id: The conversation to clear
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM conversations
                WHERE conversation_id = ? AND bot_type = ?
            """, (conversation_id, self.bot_type))
    
    async def clear_all_conversations(self):
        """Clear all conversations for this bot type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM conversations
                WHERE bot_type = ?
            """, (self.bot_type,))
    
    async def get_conversation_summary(
        self, 
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a conversation
        
        Args:
            conversation_id: The conversation to summarize
            
        Returns:
            Summary information about the conversation
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT COUNT(*) as exchange_count,
                       MIN(timestamp) as started_at,
                       MAX(timestamp) as last_activity,
                       user_message as first_message
                FROM conversations
                WHERE conversation_id = ? AND bot_type = ?
                GROUP BY conversation_id
            """, (conversation_id, self.bot_type))
            
            row = cursor.fetchone()
            if row:
                return {
                    "conversation_id": conversation_id,
                    "exchange_count": row["exchange_count"],
                    "started_at": row["started_at"],
                    "last_activity": row["last_activity"],
                    "first_message": row["first_message"]
                }
            
            return None
    
    async def cleanup_old_conversations(self, days_to_keep: int = 30):
        """
        Clean up conversations older than specified days
        
        Args:
            days_to_keep: Number of days of conversations to keep
        """
        # For public bot, keep fewer conversations for privacy
        if self.bot_type == "public":
            days_to_keep = min(days_to_keep, 7)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM conversations
                WHERE bot_type = ? 
                AND timestamp < datetime('now', '-{} days')
            """.format(days_to_keep), (self.bot_type,))
    
    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID"""
        from uuid import uuid4
        return str(uuid4()) 