#!/usr/bin/env python3
"""
Camel-AI Chat & Message Parser

Specialized parser for structured logs (chat, email) that breaks one file per message
with proper metadata extraction and attachment handling.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

# Camel-AI imports
from camel.loaders import BaseIO
from camel.toolkits import ImageAnalysisToolkit, AudioAnalysisToolkit
from camel.storages.vectordb_storages.chroma import ChromaStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Structure for chat message data"""
    message_id: str
    thread_id: str
    sender: str
    timestamp: str
    content: str
    role: str  # 'user', 'assistant', 'system'
    platform: str  # 'whatsapp', 'telegram', 'discord', etc.
    metadata: Dict[str, Any]
    attachments: List[Dict[str, Any]]

@dataclass
class EmailMessage:
    """Structure for email message data"""
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipients: List[str]
    cc: List[str]
    timestamp: str
    content: str
    metadata: Dict[str, Any]
    attachments: List[Dict[str, Any]]

class WhatsAppChatLoader(BaseIO):
    """Custom loader for WhatsApp chat exports"""
    
    def __init__(self):
        super().__init__()
        # WhatsApp timestamp patterns
        self.timestamp_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\s*[-–]\s*([^:]+?):\s*(.*)',
            r'\[(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\]\s*([^:]+?):\s*(.*)',
            r'(\d{1,2}.\d{1,2}.\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\s*[-–]\s*([^:]+?):\s*(.*)'
        ]
    
    def load(self, file_path: str) -> List[ChatMessage]:
        """Load WhatsApp chat file and extract messages"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            messages = []
            thread_id = self._generate_thread_id(file_path)
            
            # Split into lines and process
            lines = content.split('\n')
            current_message = None
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Try to match message patterns
                message_match = self._match_message_line(line)
                
                if message_match:
                    # Save previous message if exists
                    if current_message:
                        messages.append(current_message)
                    
                    # Start new message
                    current_message = ChatMessage(
                        message_id=str(uuid.uuid4()),
                        thread_id=thread_id,
                        sender=message_match['sender'],
                        timestamp=message_match['timestamp'],
                        content=message_match['content'],
                        role='user',
                        platform='whatsapp',
                        metadata={
                            'file_path': file_path,
                            'line_number': line_num + 1,
                            'raw_timestamp': message_match['raw_timestamp']
                        },
                        attachments=[]
                    )
                    
                    # Check for attachments
                    self._detect_attachments(current_message)
                    
                else:
                    # Continuation of previous message
                    if current_message:
                        current_message.content += '\n' + line
            
            # Save last message
            if current_message:
                messages.append(current_message)
            
            logger.info(f"Extracted {len(messages)} messages from {file_path}")
            return messages
            
        except Exception as e:
            logger.error(f"Error loading WhatsApp chat {file_path}: {e}")
            return []
    
    def _match_message_line(self, line: str) -> Optional[Dict[str, str]]:
        """Try to match a line against message patterns"""
        for pattern in self.timestamp_patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                return {
                    'raw_timestamp': groups[0],
                    'timestamp': self._normalize_timestamp(groups[0]),
                    'sender': groups[1].strip(),
                    'content': groups[2].strip() if len(groups) > 2 else ''
                }
        return None
    
    def _normalize_timestamp(self, raw_timestamp: str) -> str:
        """Normalize timestamp to ISO format"""
        try:
            # Handle different timestamp formats
            raw_timestamp = raw_timestamp.replace(',', '').strip()
            
            # Try different parsing patterns
            timestamp_formats = [
                '%m/%d/%Y %I:%M:%S %p',
                '%m/%d/%Y %I:%M %p',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y %H:%M',
                '%m/%d/%y %I:%M:%S %p',
                '%m/%d/%y %I:%M %p',
                '%d.%m.%Y %H:%M:%S',
                '%d.%m.%Y %H:%M'
            ]
            
            for fmt in timestamp_formats:
                try:
                    dt = datetime.strptime(raw_timestamp, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # Fallback: return raw timestamp
            return raw_timestamp
            
        except Exception as e:
            logger.error(f"Error normalizing timestamp {raw_timestamp}: {e}")
            return raw_timestamp
    
    def _generate_thread_id(self, file_path: str) -> str:
        """Generate thread ID from file path"""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
    
    def _detect_attachments(self, message: ChatMessage) -> None:
        """Detect and catalog attachments in message"""
        content_lower = message.content.lower()
        
        # Common attachment indicators
        attachment_indicators = [
            r'<media omitted>',
            r'<attached: (.+?)>',
            r'image omitted',
            r'video omitted',
            r'audio omitted',
            r'document omitted',
            r'sticker omitted',
            r'gif omitted'
        ]
        
        for pattern in attachment_indicators:
            matches = re.findall(pattern, message.content, re.IGNORECASE)
            for match in matches:
                attachment = {
                    'attachment_id': str(uuid.uuid4()),
                    'type': self._determine_attachment_type(match if isinstance(match, str) else pattern),
                    'description': match if isinstance(match, str) else 'Media file',
                    'message_id': message.message_id
                }
                message.attachments.append(attachment)
    
    def _determine_attachment_type(self, indicator: str) -> str:
        """Determine attachment type from indicator"""
        indicator_lower = indicator.lower()
        
        if any(word in indicator_lower for word in ['image', 'photo', 'jpg', 'png']):
            return 'image'
        elif any(word in indicator_lower for word in ['video', 'mp4', 'mov']):
            return 'video'
        elif any(word in indicator_lower for word in ['audio', 'voice', 'mp3', 'wav']):
            return 'audio'
        elif any(word in indicator_lower for word in ['document', 'pdf', 'doc']):
            return 'document'
        elif 'sticker' in indicator_lower:
            return 'sticker'
        elif 'gif' in indicator_lower:
            return 'gif'
        else:
            return 'unknown'

class TelegramChatLoader(BaseIO):
    """Custom loader for Telegram chat exports"""
    
    def load(self, file_path: str) -> List[ChatMessage]:
        """Load Telegram chat file (usually JSON format)"""
        try:
            if file_path.endswith('.json'):
                return self._load_json_export(file_path)
            else:
                return self._load_text_export(file_path)
        except Exception as e:
            logger.error(f"Error loading Telegram chat {file_path}: {e}")
            return []
    
    def _load_json_export(self, file_path: str) -> List[ChatMessage]:
        """Load Telegram JSON export"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            thread_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
            
            for msg_data in data.get('messages', []):
                message = ChatMessage(
                    message_id=str(msg_data.get('id', uuid.uuid4())),
                    thread_id=thread_id,
                    sender=msg_data.get('from', 'Unknown'),
                    timestamp=msg_data.get('date', datetime.now().isoformat()),
                    content=self._extract_telegram_text(msg_data),
                    role='user',
                    platform='telegram',
                    metadata={
                        'file_path': file_path,
                        'message_type': msg_data.get('type', 'message'),
                        'chat_name': data.get('name', 'Unknown Chat')
                    },
                    attachments=self._extract_telegram_attachments(msg_data)
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error loading Telegram JSON {file_path}: {e}")
            return []
    
    def _extract_telegram_text(self, msg_data: Dict[str, Any]) -> str:
        """Extract text content from Telegram message"""
        text_content = []
        
        if isinstance(msg_data.get('text'), str):
            text_content.append(msg_data['text'])
        elif isinstance(msg_data.get('text'), list):
            for item in msg_data['text']:
                if isinstance(item, str):
                    text_content.append(item)
                elif isinstance(item, dict) and 'text' in item:
                    text_content.append(item['text'])
        
        return ' '.join(text_content)
    
    def _extract_telegram_attachments(self, msg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachments from Telegram message"""
        attachments = []
        
        # Check for different media types
        media_types = ['photo', 'video', 'audio', 'document', 'sticker', 'animation']
        
        for media_type in media_types:
            if media_type in msg_data:
                attachment = {
                    'attachment_id': str(uuid.uuid4()),
                    'type': media_type,
                    'file_name': msg_data[media_type].get('file_name', f'{media_type}_file'),
                    'mime_type': msg_data[media_type].get('mime_type', 'application/octet-stream'),
                    'file_size': msg_data[media_type].get('file_size', 0)
                }
                attachments.append(attachment)
        
        return attachments

class EmailLoader(BaseIO):
    """Custom loader for email data (EML, MSG, MBOX formats)"""
    
    def load(self, file_path: str) -> List[EmailMessage]:
        """Load email file and extract messages"""
        try:
            if file_path.endswith('.eml'):
                return self._load_eml_file(file_path)
            elif file_path.endswith('.mbox'):
                return self._load_mbox_file(file_path)
            else:
                return self._load_generic_email(file_path)
        except Exception as e:
            logger.error(f"Error loading email {file_path}: {e}")
            return []
    
    def _load_eml_file(self, file_path: str) -> List[EmailMessage]:
        """Load EML email file"""
        try:
            import email
            from email.parser import Parser
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                msg = Parser().parse(f)
            
            email_msg = EmailMessage(
                message_id=msg.get('Message-ID', str(uuid.uuid4())),
                thread_id=msg.get('Thread-Topic', str(uuid.uuid4())),
                subject=msg.get('Subject', 'No Subject'),
                sender=msg.get('From', 'Unknown'),
                recipients=self._parse_email_addresses(msg.get('To', '')),
                cc=self._parse_email_addresses(msg.get('CC', '')),
                timestamp=msg.get('Date', datetime.now().isoformat()),
                content=self._extract_email_content(msg),
                metadata={
                    'file_path': file_path,
                    'headers': dict(msg.items()),
                    'content_type': msg.get_content_type()
                },
                attachments=self._extract_email_attachments(msg)
            )
            
            return [email_msg]
            
        except Exception as e:
            logger.error(f"Error loading EML file {file_path}: {e}")
            return []
    
    def _parse_email_addresses(self, addr_string: str) -> List[str]:
        """Parse email addresses from string"""
        if not addr_string:
            return []
        
        # Simple parsing - can be enhanced with email.utils.parseaddr
        addresses = [addr.strip() for addr in addr_string.split(',')]
        return [addr for addr in addresses if addr]
    
    def _extract_email_content(self, msg) -> str:
        """Extract text content from email message"""
        content_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    content_parts.append(part.get_payload(decode=True).decode('utf-8', errors='ignore'))
                elif content_type == 'text/html':
                    # Could add HTML to text conversion here
                    html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    content_parts.append(f"[HTML Content: {len(html_content)} chars]")
        else:
            content_parts.append(msg.get_payload(decode=True).decode('utf-8', errors='ignore'))
        
        return '\n'.join(content_parts)
    
    def _extract_email_attachments(self, msg) -> List[Dict[str, Any]]:
        """Extract attachments from email"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        attachment = {
                            'attachment_id': str(uuid.uuid4()),
                            'type': 'email_attachment',
                            'file_name': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)) if part.get_payload() else 0
                        }
                        attachments.append(attachment)
        
        return attachments

class CamelChatParser:
    """
    Main chat parser using Camel-AI ecosystem for structured logs
    """
    
    def __init__(self, 
                 vector_storage: ChromaStorage,
                 image_toolkit: ImageAnalysisToolkit = None,
                 audio_toolkit: AudioAnalysisToolkit = None):
        """
        Initialize chat parser
        
        Args:
            vector_storage: ChromaDB storage instance
            image_toolkit: For processing image attachments
            audio_toolkit: For processing audio attachments
        """
        self.vector_storage = vector_storage
        self.image_toolkit = image_toolkit or ImageAnalysisToolkit()
        self.audio_toolkit = audio_toolkit or AudioAnalysisToolkit()
        
        # Initialize loaders
        self.loaders = {
            'whatsapp': WhatsAppChatLoader(),
            'telegram': TelegramChatLoader(),
            'email': EmailLoader()
        }
        
        # Processing stats
        self.processing_stats = {
            'total_files': 0,
            'processed_messages': 0,
            'processed_attachments': 0,
            'errors': 0
        }
    
    async def process_chat_directory(self, directory_path: str) -> Dict[str, Any]:
        """Process a directory containing chat files"""
        directory_path = Path(directory_path)
        results = {
            'messages': [],
            'attachments': [],
            'collections_created': [],
            'stats': self.processing_stats
        }
        
        try:
            # Find all chat files
            chat_files = self._discover_chat_files(directory_path)
            self.processing_stats['total_files'] = len(chat_files)
            
            # Process each file
            for file_path in chat_files:
                try:
                    platform = self._detect_platform(file_path)
                    loader = self.loaders.get(platform)
                    
                    if loader:
                        if platform == 'email':
                            messages = loader.load(str(file_path))
                            # Convert EmailMessage to ChatMessage for consistent handling
                            for email_msg in messages:
                                chat_msg = self._email_to_chat_message(email_msg)
                                results['messages'].append(chat_msg)
                        else:
                            messages = loader.load(str(file_path))
                            results['messages'].extend(messages)
                        
                        self.processing_stats['processed_messages'] += len(messages)
                        logger.info(f"Processed {len(messages)} messages from {file_path}")
                    else:
                        logger.warning(f"No loader available for platform: {platform}")
                
                except Exception as e:
                    logger.error(f"Error processing chat file {file_path}: {e}")
                    self.processing_stats['errors'] += 1
            
            # Process attachments
            await self._process_attachments(results['messages'], directory_path)
            
            # Store in vector database
            await self._store_chat_data(results['messages'])
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing chat directory: {e}")
            return {'error': str(e), 'stats': self.processing_stats}
    
    def _discover_chat_files(self, directory_path: Path) -> List[Path]:
        """Discover chat files in directory"""
        chat_patterns = [
            '**/*chat*.txt',
            '**/*messages*.txt',
            '**/*whatsapp*.txt',
            '**/*telegram*.json',
            '**/*.eml',
            '**/*.mbox'
        ]
        
        chat_files = []
        for pattern in chat_patterns:
            chat_files.extend(directory_path.glob(pattern))
        
        return list(set(chat_files))  # Remove duplicates
    
    def _detect_platform(self, file_path: Path) -> str:
        """Detect chat platform from file path and content"""
        file_name_lower = file_path.name.lower()
        
        if 'whatsapp' in file_name_lower or '_chat.txt' in file_name_lower:
            return 'whatsapp'
        elif 'telegram' in file_name_lower or file_path.suffix == '.json':
            return 'telegram'
        elif file_path.suffix in ['.eml', '.mbox', '.msg']:
            return 'email'
        else:
            # Try to detect from content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)  # Read first 1000 chars
                
                if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}.*?-.*?:', content):
                    return 'whatsapp'
                elif '"messages"' in content and '"date"' in content:
                    return 'telegram'
                else:
                    return 'unknown'
            except:
                return 'unknown'
    
    def _email_to_chat_message(self, email_msg: EmailMessage) -> ChatMessage:
        """Convert EmailMessage to ChatMessage for consistent handling"""
        return ChatMessage(
            message_id=email_msg.message_id,
            thread_id=email_msg.thread_id,
            sender=email_msg.sender,
            timestamp=email_msg.timestamp,
            content=f"Subject: {email_msg.subject}\n\n{email_msg.content}",
            role='user',
            platform='email',
            metadata={
                **email_msg.metadata,
                'subject': email_msg.subject,
                'recipients': email_msg.recipients,
                'cc': email_msg.cc
            },
            attachments=email_msg.attachments
        )
    
    async def _process_attachments(self, messages: List[ChatMessage], base_path: Path) -> None:
        """Process attachments found in messages"""
        for message in messages:
            for attachment in message.attachments:
                try:
                    # Try to find actual attachment file
                    attachment_path = self._find_attachment_file(attachment, base_path)
                    
                    if attachment_path and attachment_path.exists():
                        # Process based on attachment type
                        if attachment['type'] == 'image':
                            description = self.image_toolkit.image_to_text(str(attachment_path))
                            attachment['ai_description'] = description
                        elif attachment['type'] == 'audio':
                            transcript = self.audio_toolkit.transcribe(str(attachment_path))
                            attachment['transcript'] = transcript
                        
                        attachment['file_path'] = str(attachment_path)
                        self.processing_stats['processed_attachments'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment.get('file_name', 'unknown')}: {e}")
    
    def _find_attachment_file(self, attachment: Dict[str, Any], base_path: Path) -> Optional[Path]:
        """Try to find the actual attachment file"""
        file_name = attachment.get('file_name', '')
        if not file_name:
            return None
        
        # Search for file in base path and subdirectories
        for file_path in base_path.rglob(file_name):
            if file_path.is_file():
                return file_path
        
        return None
    
    async def _store_chat_data(self, messages: List[ChatMessage]) -> None:
        """Store chat messages in vector database"""
        try:
            # Group messages by platform for different collections
            platform_groups = {}
            for message in messages:
                platform = message.platform
                if platform not in platform_groups:
                    platform_groups[platform] = []
                platform_groups[platform].append(message)
            
            # Store each platform group in separate collection
            for platform, platform_messages in platform_groups.items():
                collection_name = f"chat_{platform}"
                
                # Create collection if it doesn't exist
                try:
                    self.vector_storage.create_collection(collection_name)
                except:
                    pass  # Collection might already exist
                
                # Prepare documents for storage
                documents = []
                metadatas = []
                
                for message in platform_messages:
                    documents.append(message.content)
                    metadatas.append({
                        'message_id': message.message_id,
                        'thread_id': message.thread_id,
                        'sender': message.sender,
                        'timestamp': message.timestamp,
                        'platform': message.platform,
                        'role': message.role,
                        'attachment_count': len(message.attachments),
                        **message.metadata
                    })
                
                # Store in vector database
                if documents:
                    self.vector_storage.add_documents(
                        collection_name=collection_name,
                        contents=documents,
                        metadatas=metadatas
                    )
                    
                    logger.info(f"Stored {len(documents)} messages in collection {collection_name}")
        
        except Exception as e:
            logger.error(f"Error storing chat data: {e}")

# Example usage
async def main():
    """Example usage of the chat parser"""
    from camel.embeddings import OpenAIEmbeddings
    
    # Initialize vector storage
    embeddings = OpenAIEmbeddings()
    vector_storage = ChromaStorage(
        path="data/chat_vector_db",
        embedding_model=embeddings
    )
    
    # Initialize chat parser
    parser = CamelChatParser(vector_storage)
    
    # Process chat directory
    results = await parser.process_chat_directory("/path/to/chat/directory")
    
    print(f"Processed {results['stats']['processed_messages']} messages")
    print(f"Processed {results['stats']['processed_attachments']} attachments")

if __name__ == "__main__":
    asyncio.run(main())