"""
Logging utilities for Project Zohar.

This module provides centralized logging configuration and utilities.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from config.settings import Settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(settings: Settings) -> None:
    """
    Set up logging configuration.
    
    Args:
        settings: Application settings
    """
    # Create logs directory if it doesn't exist
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Use colored formatter for console in development
    if settings.is_development:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - main log
    main_log_file = settings.logs_dir / "zohar.log"
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error log file
    error_log_file = settings.logs_dir / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Agent-specific log files
    agent_log_file = settings.logs_dir / "agents.log"
    agent_handler = logging.handlers.RotatingFileHandler(
        agent_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    agent_handler.setLevel(logging.INFO)
    agent_handler.setFormatter(file_formatter)
    
    # Add agent handler to agent loggers
    agent_logger = logging.getLogger('zohar.core.agents')
    agent_logger.addHandler(agent_handler)
    agent_logger.setLevel(logging.INFO)
    
    # Platform integration log
    platform_log_file = settings.logs_dir / "platform.log"
    platform_handler = logging.handlers.RotatingFileHandler(
        platform_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    platform_handler.setLevel(logging.INFO)
    platform_handler.setFormatter(file_formatter)
    
    platform_logger = logging.getLogger('zohar.services.platform_integration')
    platform_logger.addHandler(platform_handler)
    platform_logger.setLevel(logging.INFO)
    
    # Data processing log
    data_log_file = settings.logs_dir / "data.log"
    data_handler = logging.handlers.RotatingFileHandler(
        data_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    data_handler.setLevel(logging.INFO)
    data_handler.setFormatter(file_formatter)
    
    data_logger = logging.getLogger('zohar.services.data_processing')
    data_logger.addHandler(data_handler)
    data_logger.setLevel(logging.INFO)
    
    # Silence some noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger('zohar.logging')
    logger.info("Logging system initialized")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Log directory: {settings.logs_dir}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


class StructuredLogger:
    """
    Structured logger that adds context to log messages.
    """
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            context: Default context to include in all log messages
        """
        self.logger = get_logger(name)
        self.context = context or {}
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context."""
        context = {**self.context, **kwargs}
        
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            return f"{message} | {context_str}"
        
        return message
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, **kwargs))
    
    def exception(self, message: str, **kwargs):
        """Log exception with context."""
        self.logger.exception(self._format_message(message, **kwargs))
    
    def add_context(self, **kwargs):
        """Add context to this logger."""
        self.context.update(kwargs)
    
    def remove_context(self, *keys):
        """Remove context keys from this logger."""
        for key in keys:
            self.context.pop(key, None)
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger with additional context."""
        new_context = {**self.context, **kwargs}
        return StructuredLogger(self.logger.name, new_context)


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls.
    
    Args:
        logger: Logger to use for logging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised exception: {e}")
                raise
        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger):
    """
    Decorator to log async function calls.
    
    Args:
        logger: Logger to use for logging
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised exception: {e}")
                raise
        return wrapper
    return decorator


class LogCapture:
    """
    Context manager to capture log messages for testing.
    """
    
    def __init__(self, logger_name: str, level: int = logging.INFO):
        """
        Initialize log capture.
        
        Args:
            logger_name: Name of logger to capture
            level: Minimum log level to capture
        """
        self.logger_name = logger_name
        self.level = level
        self.handler = None
        self.records = []
    
    def __enter__(self):
        """Start capturing logs."""
        self.handler = logging.handlers.MemoryHandler(capacity=1000)
        self.handler.setLevel(self.level)
        
        logger = logging.getLogger(self.logger_name)
        logger.addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing logs."""
        if self.handler:
            logger = logging.getLogger(self.logger_name)
            logger.removeHandler(self.handler)
            self.records = self.handler.buffer
            self.handler.close()
    
    def get_records(self) -> list:
        """Get captured log records."""
        return self.records
    
    def get_messages(self) -> list:
        """Get captured log messages."""
        return [record.getMessage() for record in self.records]
    
    def has_message(self, message: str) -> bool:
        """Check if a specific message was logged."""
        return any(message in record.getMessage() for record in self.records)
    
    def has_level(self, level: int) -> bool:
        """Check if any message at the specified level was logged."""
        return any(record.levelno >= level for record in self.records)


def configure_third_party_loggers():
    """Configure third-party library loggers."""
    # Configure specific third-party loggers
    third_party_configs = {
        'camel': logging.INFO,
        'ollama': logging.WARNING,
        'chromadb': logging.WARNING,
        'sentence_transformers': logging.WARNING,
        'transformers': logging.WARNING,
        'torch': logging.WARNING,
        'tensorflow': logging.WARNING,
        'uvicorn': logging.INFO,
        'fastapi': logging.INFO,
        'sqlalchemy': logging.WARNING,
        'alembic': logging.WARNING,
        'redis': logging.WARNING,
        'celery': logging.WARNING,
    }
    
    for logger_name, level in third_party_configs.items():
        logging.getLogger(logger_name).setLevel(level)


def get_log_stats(log_file: Path) -> Dict[str, Any]:
    """
    Get statistics about a log file.
    
    Args:
        log_file: Path to log file
        
    Returns:
        Log file statistics
    """
    if not log_file.exists():
        return {"error": "Log file not found"}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        stats = {
            "total_lines": len(lines),
            "file_size": log_file.stat().st_size,
            "last_modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
            "levels": {
                "DEBUG": 0,
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "CRITICAL": 0,
            }
        }
        
        # Count log levels
        for line in lines:
            for level in stats["levels"]:
                if f" - {level} - " in line:
                    stats["levels"][level] += 1
                    break
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


def cleanup_old_logs(logs_dir: Path, days_to_keep: int = 30):
    """
    Clean up old log files.
    
    Args:
        logs_dir: Directory containing log files
        days_to_keep: Number of days to keep logs
    """
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in logs_dir.glob("*.log*"):
            if log_file.is_file():
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    logger = get_logger('zohar.logging')
                    logger.info(f"Deleted old log file: {log_file}")
                    
    except Exception as e:
        logger = get_logger('zohar.logging')
        logger.error(f"Error cleaning up old logs: {e}")


# Initialize third-party logger configuration
configure_third_party_loggers()
