"""
Services package for the Personal Chatbot System
"""

from .ollama_service import ollama_service

# Camel-AI file processors (commented out temporarily due to dependency issues)
# from .camel_file_processor import CamelFileProcessor, SchemaDesignerAgent, FileSummarizerAgent
# from .camel_chat_parser import CamelChatParser, WhatsAppChatLoader, TelegramChatLoader, EmailLoader
 
__all__ = [
    "ollama_service",
    # "CamelFileProcessor", 
    # "SchemaDesignerAgent", 
    # "FileSummarizerAgent",
    # "CamelChatParser",
    # "WhatsAppChatLoader",
    # "TelegramChatLoader", 
    # "EmailLoader"
] 