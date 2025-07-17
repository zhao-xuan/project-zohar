#!/usr/bin/env python3
"""
Configuration for Chat History Parser Module

This module provides configuration settings for the multi-platform chat history
parser, including database paths, embedding models, and platform-specific settings.
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum


class ChatPlatform(Enum):
    """Supported chat platforms"""
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WECHAT = "wechat"
    GENERIC = "generic"


class DatabaseConfig(BaseModel):
    """Database configuration for chat history storage"""
    knowledge_graph_db: str = Field(
        default="./data/knowledge_graph.db",
        description="Path to SQLite database for knowledge graph"
    )
    vector_store_db: str = Field(
        default="./data/vector_store",
        description="Path to vector database for semantic search"
    )
    backup_path: str = Field(
        default="./data/backups",
        description="Path for database backups"
    )
    
    class Config:
        extra = "forbid"


class EmbeddingConfig(BaseModel):
    """Configuration for embedding models"""
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimension of the embedding vectors"
    )
    batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )
    
    class Config:
        extra = "forbid"


class SlackConfig(BaseModel):
    """Slack-specific configuration"""
    export_path: Optional[str] = Field(
        default=None,
        description="Path to Slack export directory"
    )
    api_token: Optional[str] = Field(
        default=None,
        description="Slack API token for real-time access"
    )
    workspace_name: Optional[str] = Field(
        default=None,
        description="Slack workspace name"
    )
    channels_to_include: List[str] = Field(
        default_factory=list,
        description="List of channel names to include (empty = all)"
    )
    channels_to_exclude: List[str] = Field(
        default_factory=list,
        description="List of channel names to exclude"
    )
    
    class Config:
        extra = "forbid"


class TeamsConfig(BaseModel):
    """Microsoft Teams configuration"""
    client_id: Optional[str] = Field(
        default=None,
        description="Azure AD app client ID"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Azure AD app client secret"
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD tenant ID"
    )
    teams_to_include: List[str] = Field(
        default_factory=list,
        description="List of team names to include (empty = all)"
    )
    
    class Config:
        extra = "forbid"


class DiscordConfig(BaseModel):
    """Discord configuration"""
    bot_token: Optional[str] = Field(
        default=None,
        description="Discord bot token"
    )
    guild_ids: List[str] = Field(
        default_factory=list,
        description="List of Discord guild (server) IDs"
    )
    channels_to_include: List[str] = Field(
        default_factory=list,
        description="List of channel names to include"
    )
    
    class Config:
        extra = "forbid"


class ProcessingConfig(BaseModel):
    """Configuration for message processing"""
    batch_size: int = Field(
        default=1000,
        description="Number of messages to process in each batch"
    )
    max_content_length: int = Field(
        default=10000,
        description="Maximum length of message content to process"
    )
    include_attachments: bool = Field(
        default=True,
        description="Whether to include attachment metadata"
    )
    include_reactions: bool = Field(
        default=True,
        description="Whether to include reaction data"
    )
    extract_entities: bool = Field(
        default=True,
        description="Whether to extract entities from messages"
    )
    extract_relationships: bool = Field(
        default=True,
        description="Whether to extract entity relationships"
    )
    
    class Config:
        extra = "forbid"


class EntityExtractionConfig(BaseModel):
    """Configuration for entity extraction"""
    extract_mentions: bool = Field(
        default=True,
        description="Extract user mentions"
    )
    extract_hashtags: bool = Field(
        default=True,
        description="Extract hashtags as topics"
    )
    extract_urls: bool = Field(
        default=True,
        description="Extract URLs"
    )
    extract_emails: bool = Field(
        default=True,
        description="Extract email addresses"
    )
    extract_projects: bool = Field(
        default=True,
        description="Extract project mentions"
    )
    extract_tickets: bool = Field(
        default=True,
        description="Extract ticket/issue numbers"
    )
    custom_patterns: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom regex patterns for entity extraction"
    )
    
    class Config:
        extra = "forbid"


class SchedulingConfig(BaseModel):
    """Configuration for autonomous scheduling"""
    enable_scheduling: bool = Field(
        default=False,
        description="Enable autonomous scheduled processing"
    )
    schedule_interval: str = Field(
        default="weekly",
        description="Scheduling interval: daily, weekly, monthly"
    )
    schedule_time: str = Field(
        default="02:00",
        description="Time to run scheduled jobs (HH:MM)"
    )
    lookback_days: int = Field(
        default=7,
        description="Number of days to look back for new messages"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed jobs"
    )
    
    class Config:
        extra = "forbid"


class ChatHistoryConfig(BaseModel):
    """Main configuration for chat history parser"""
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration"
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding model configuration"
    )
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Message processing configuration"
    )
    entity_extraction: EntityExtractionConfig = Field(
        default_factory=EntityExtractionConfig,
        description="Entity extraction configuration"
    )
    scheduling: SchedulingConfig = Field(
        default_factory=SchedulingConfig,
        description="Scheduling configuration"
    )
    
    # Platform-specific configurations
    slack: SlackConfig = Field(
        default_factory=SlackConfig,
        description="Slack platform configuration"
    )
    teams: TeamsConfig = Field(
        default_factory=TeamsConfig,
        description="Microsoft Teams configuration"
    )
    discord: DiscordConfig = Field(
        default_factory=DiscordConfig,
        description="Discord configuration"
    )
    
    # General settings
    debug: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    data_retention_days: int = Field(
        default=365,
        description="Number of days to retain processed data"
    )
    
    class Config:
        extra = "forbid"


def load_config_from_file(config_path: str) -> ChatHistoryConfig:
    """Load configuration from JSON file"""
    import json
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    return ChatHistoryConfig(**config_data)


def load_config_from_env() -> ChatHistoryConfig:
    """Load configuration from environment variables"""
    config_data = {}
    
    # Database configuration
    if db_path := os.getenv('CHAT_KNOWLEDGE_GRAPH_DB'):
        config_data.setdefault('database', {})['knowledge_graph_db'] = db_path
    
    if vector_path := os.getenv('CHAT_VECTOR_STORE_DB'):
        config_data.setdefault('database', {})['vector_store_db'] = vector_path
    
    # Embedding configuration
    if model_name := os.getenv('CHAT_EMBEDDING_MODEL'):
        config_data.setdefault('embedding', {})['model_name'] = model_name
    
    # Slack configuration
    if slack_export := os.getenv('SLACK_EXPORT_PATH'):
        config_data.setdefault('slack', {})['export_path'] = slack_export
    
    if slack_token := os.getenv('SLACK_API_TOKEN'):
        config_data.setdefault('slack', {})['api_token'] = slack_token
    
    # Teams configuration
    if teams_client_id := os.getenv('TEAMS_CLIENT_ID'):
        config_data.setdefault('teams', {})['client_id'] = teams_client_id
    
    if teams_client_secret := os.getenv('TEAMS_CLIENT_SECRET'):
        config_data.setdefault('teams', {})['client_secret'] = teams_client_secret
    
    if teams_tenant_id := os.getenv('TEAMS_TENANT_ID'):
        config_data.setdefault('teams', {})['tenant_id'] = teams_tenant_id
    
    # Discord configuration
    if discord_token := os.getenv('DISCORD_BOT_TOKEN'):
        config_data.setdefault('discord', {})['bot_token'] = discord_token
    
    # Processing configuration
    if batch_size := os.getenv('CHAT_BATCH_SIZE'):
        config_data.setdefault('processing', {})['batch_size'] = int(batch_size)
    
    # Scheduling configuration
    if enable_scheduling := os.getenv('CHAT_ENABLE_SCHEDULING'):
        config_data.setdefault('scheduling', {})['enable_scheduling'] = enable_scheduling.lower() == 'true'
    
    if schedule_interval := os.getenv('CHAT_SCHEDULE_INTERVAL'):
        config_data.setdefault('scheduling', {})['schedule_interval'] = schedule_interval
    
    return ChatHistoryConfig(**config_data)


def create_default_config() -> ChatHistoryConfig:
    """Create a default configuration"""
    return ChatHistoryConfig()


def save_config_to_file(config: ChatHistoryConfig, config_path: str):
    """Save configuration to JSON file"""
    import json
    
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config.dict(), f, indent=2, default=str)


# Example usage
if __name__ == "__main__":
    # Create default configuration
    config = create_default_config()
    
    # Save to file
    save_config_to_file(config, "./config/chat_history_config.json")
    
    # Load from file
    loaded_config = load_config_from_file("./config/chat_history_config.json")
    
    print("Configuration loaded successfully:")
    print(f"Database path: {loaded_config.database.knowledge_graph_db}")
    print(f"Embedding model: {loaded_config.embedding.model_name}")
    print(f"Batch size: {loaded_config.processing.batch_size}")
