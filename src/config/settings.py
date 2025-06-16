"""
Configuration settings for the Personal Multi-Agent Chatbot System
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, Field
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    vector_db_path: str = Field(default="./data/processed/vector_db", env="VECTOR_DB_PATH")
    sqlite_db_path: str = Field(default="./data/processed/chatbot.db", env="SQLITE_DB_PATH")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")


class LLMConfig(BaseSettings):
    """LLM configuration settings"""
    model_name: str = Field(default="deepseek", env="LLM_MODEL_NAME")
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")


class EmailConfig(BaseSettings):
    """Email configuration settings"""
    # Gmail settings
    gmail_credentials_path: Optional[str] = Field(default=None, env="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: Optional[str] = Field(default=None, env="GMAIL_TOKEN_PATH")
    
    # Outlook settings
    outlook_client_id: Optional[str] = Field(default=None, env="OUTLOOK_CLIENT_ID")
    outlook_client_secret: Optional[str] = Field(default=None, env="OUTLOOK_CLIENT_SECRET")
    
    # QQ Mail settings (IMAP/SMTP)
    qq_email: Optional[str] = Field(default=None, env="QQ_EMAIL")
    qq_app_password: Optional[str] = Field(default=None, env="QQ_APP_PASSWORD")
    qq_imap_server: str = Field(default="imap.qq.com", env="QQ_IMAP_SERVER")
    qq_smtp_server: str = Field(default="smtp.qq.com", env="QQ_SMTP_SERVER")


class MCPConfig(BaseSettings):
    """MCP (Model Context Protocol) configuration"""
    email_mcp_port: int = Field(default=8080, env="EMAIL_MCP_PORT")
    browser_mcp_port: int = Field(default=8081, env="BROWSER_MCP_PORT")
    system_mcp_port: int = Field(default=8082, env="SYSTEM_MCP_PORT")
    mcp_timeout: int = Field(default=30, env="MCP_TIMEOUT")


class WebUIConfig(BaseSettings):
    """Web UI configuration"""
    host: str = Field(default="127.0.0.1", env="WEB_HOST")
    personal_bot_port: int = Field(default=5000, env="PERSONAL_BOT_PORT")
    public_bot_port: int = Field(default=5001, env="PUBLIC_BOT_PORT")
    secret_key: str = Field(default="your-secret-key-change-this", env="SECRET_KEY")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")


class SecurityConfig(BaseSettings):
    """Security configuration"""
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=[".txt", ".pdf", ".docx", ".md", ".json"],
        env="ALLOWED_FILE_TYPES"
    )
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    enable_public_bot: bool = Field(default=True, env="ENABLE_PUBLIC_BOT")


class PersonaConfig(BaseSettings):
    """Persona and tone configuration"""
    personal_tone_examples_path: str = Field(
        default="./data/personal/tone_examples.txt",
        env="TONE_EXAMPLES_PATH"
    )
    personal_bio_path: str = Field(
        default="./data/personal/bio.txt",
        env="PERSONAL_BIO_PATH"
    )
    public_bio_path: str = Field(
        default="./data/public/public_bio.txt",
        env="PUBLIC_BIO_PATH"
    )


class Settings(BaseSettings):
    """Main application settings"""
    # App metadata
    app_name: str = "Personal Multi-Agent Chatbot System"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Nested configurations
    database: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    email: EmailConfig = EmailConfig()
    mcp: MCPConfig = MCPConfig()
    web_ui: WebUIConfig = WebUIConfig()
    security: SecurityConfig = SecurityConfig()
    persona: PersonaConfig = PersonaConfig()
    
    # Data paths
    base_data_path: Path = Field(default=Path("./data"), env="BASE_DATA_PATH")
    personal_data_path: Path = Field(default=Path("./data/personal"), env="PERSONAL_DATA_PATH")
    public_data_path: Path = Field(default=Path("./data/public"), env="PUBLIC_DATA_PATH")
    processed_data_path: Path = Field(default=Path("./data/processed"), env="PROCESSED_DATA_PATH")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file_path: str = Field(default="./logs/chatbot.log", env="LOG_FILE_PATH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.base_data_path,
            self.personal_data_path,
            self.public_data_path,
            self.processed_data_path,
            Path(self.log_file_path).parent,
            Path(self.database.vector_db_path).parent,
            Path(self.database.sqlite_db_path).parent,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

# Create directories on import
settings.create_directories() 