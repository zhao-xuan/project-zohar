"""
Project Zohar: A privacy-focused AI assistant with local deployment capabilities.

This package provides a comprehensive AI assistant system that emphasizes data privacy
and local deployment. It includes email/message processing, multi-agent orchestration,
data processing capabilities, and integration with various platforms and tools.
"""

__version__ = "0.1.0"
__author__ = "Project Zohar Team"
__email__ = "team@projectzohar.com"
__description__ = "A privacy-focused AI assistant with local deployment capabilities"

from .module.bot.personal_agent import PersonalAgent
from .module.bot.public_agent import PublicAgent
from .module.bot.bot_manager import BotManager
from .module.agent.platform_manager import PlatformManager
# Settings is now imported from root config

__all__ = [
    "PersonalAgent",
    "PublicAgent", 
    "BotManager",
    "PlatformManager",
    "__version__",
]
