"""
WeChat Data Processor for extracting messages from HTML conversation files
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class WeChatProcessor:
    """
    Processes WeChat conversation HTML files to extract messages and metadata
    """
    
    def __init__(self):
        self.message_patterns = {
            'timestamp': r'(\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}:\d{2} [AP]M)',
            'sender_name': r'<span class="dspname.*?">(.*?)</span>',
            'message_content': r'<span class=".*?msg-text.*?">(.*?)</span>'
        }
    
    def process_wechat_directory(self, wechat_path: str) -> Dict[str, Any]:
        """
        Process entire WeChat export directory
        
        Args:
            wechat_path: Path to WeChat export directory
            
        Returns:
            Dictionary containing processed conversations and analysis
        """
        logger.info(f"Processing WeChat directory: {wechat_path}")
        
        wechat_dir = Path(wechat_path)
        if not wechat_dir.exists():
            raise FileNotFoundError(f"WeChat directory not found: {wechat_path}")
        
        results = {
            'conversations': [],
            'total_messages': 0,
            'participants': set(),
            'date_range': {'earliest': None, 'latest': None},
            'message_types': {'text': 0, 'media': 0, 'system': 0}
        }
        
        # Process HTML files in subdirectories  
        html_files = []
        for subdir in wechat_dir.iterdir():
            if subdir.is_dir():
                html_files.extend(list(subdir.glob("*.html")))
        
        logger.info(f"Found {len(html_files)} conversation files")
        
        for html_file in html_files:
            try:
                conversation = self.process_conversation_file(html_file)
                if conversation and conversation['messages']:
                    results['conversations'].append(conversation)
                    results['total_messages'] += len(conversation['messages'])
                    results['participants'].update(conversation['participants'])
                    
                    # Update date range
                    for msg in conversation['messages']:
                        msg_date = msg.get('timestamp')
                        if msg_date:
                            if not results['date_range']['earliest'] or msg_date < results['date_range']['earliest']:
                                results['date_range']['earliest'] = msg_date
                            if not results['date_range']['latest'] or msg_date > results['date_range']['latest']:
                                results['date_range']['latest'] = msg_date
                    
                    # Count message types
                    for msg in conversation['messages']:
                        msg_type = msg.get('type', 'text')
                        if msg_type in results['message_types']:
                            results['message_types'][msg_type] += 1
                        else:
                            results['message_types']['text'] += 1
                            
            except Exception as e:
                logger.error(f"Error processing {html_file}: {e}")
                continue
        
        results['participants'] = list(results['participants'])
        logger.info(f"Processed {len(results['conversations'])} conversations with {results['total_messages']} total messages")
        
        return results
    
    def process_conversation_file(self, html_file: Path) -> Optional[Dict[str, Any]]:
        """
        Process a single WeChat conversation HTML file
        
        Args:
            html_file: Path to HTML conversation file
            
        Returns:
            Dictionary containing conversation data
        """
        try:
            # Try different encodings for Chinese content
            content = None
            for encoding in ['utf-8', 'gbk', 'gb2312']:
                try:
                    with open(html_file, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                    break
                except:
                    continue
            
            if not content:
                logger.error(f"Could not read file {html_file} with any encoding")
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract conversation metadata
            conversation_title = self._extract_conversation_title(soup, html_file.stem)
            participants = self._extract_participants_from_messages(soup)
            
            # Extract messages using the correct HTML structure
            messages = self._extract_messages_from_wechat_html(soup)
            
            if not messages:
                logger.warning(f"No messages found in {html_file}")
                return None
            
            return {
                'file_name': html_file.name,
                'title': conversation_title,
                'participants': participants,
                'messages': messages,
                'message_count': len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error processing conversation file {html_file}: {e}")
            return None
    
    def _extract_messages_from_wechat_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract messages from WeChat HTML using the correct structure"""
        messages = []
        
        # Find all message containers: div.msg
        message_divs = soup.find_all('div', class_='msg')
        logger.debug(f"Found {len(message_divs)} message divs")
        
        for msg_div in message_divs:
            try:
                message_data = self._parse_wechat_message_div(msg_div)
                if message_data:
                    messages.append(message_data)
            except Exception as e:
                logger.debug(f"Error parsing message div: {e}")
                continue
        
        # Sort messages by timestamp
        messages.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        return messages
    
    def _parse_wechat_message_div(self, msg_div) -> Optional[Dict[str, Any]]:
        """Parse a single WeChat message div"""
        try:
            # Extract timestamp and sender from nt-box
            nt_box = msg_div.find('div', class_='nt-box')
            if not nt_box:
                return None
            
            nt_text = nt_box.get_text(strip=True)
            
            # Extract sender name from span.dspname
            dspname_span = nt_box.find('span', class_='dspname')
            if not dspname_span:
                return None
            
            sender = dspname_span.get_text(strip=True)
            sender = self._clean_participant_name(sender)
            
            # Extract timestamp using regex
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}:\d{2} [AP]M)', nt_text)
            timestamp = None
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %I:%M:%S %p')
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S %p')
                    except ValueError:
                        pass
            
            # Extract message content from span.msg-text
            content_span = msg_div.find('span', class_='msg-text')
            if not content_span:
                return None
            
            content = content_span.get_text(strip=True)
            content = self._clean_message_content(content)
            
            if not content:
                return None
            
            # Determine message type
            msg_type = self._determine_message_type(content, msg_div)
            
            return {
                'timestamp': timestamp,
                'sender': sender,
                'content': content,
                'type': msg_type,
                'msg_id': msg_div.get('msgid', ''),
                'direction': 'right' if 'right' in msg_div.get('class', []) else 'left'
            }
            
        except Exception as e:
            logger.debug(f"Error parsing message div: {e}")
            return None
    
    def _clean_message_content(self, content: str) -> str:
        """Clean message content"""
        # Remove HTML entities and normalize whitespace
        content = content.replace('&nbsp;', ' ')
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    def _extract_participants_from_messages(self, soup: BeautifulSoup) -> List[str]:
        """Extract participant names from actual messages"""
        participants = set()
        
        # Find all dspname spans
        dspname_spans = soup.find_all('span', class_='dspname')
        
        for span in dspname_spans:
            name = span.get_text(strip=True)
            cleaned_name = self._clean_participant_name(name)
            if cleaned_name:
                participants.add(cleaned_name)
        
        return list(participants)
    
    def _extract_conversation_title(self, soup: BeautifulSoup, filename: str) -> str:
        """Extract conversation title from HTML or filename"""
        # Try to find title in HTML
        title_elem = soup.find('title')
        if title_elem and title_elem.text.strip():
            return title_elem.text.strip()
        
        # Fall back to filename (remove extension and clean up)
        return filename.replace('.html', '').replace('_', ' ')
    
    def _clean_participant_name(self, name: str) -> str:
        """Clean participant name by removing emojis and extra characters"""
        if not name:
            return ""
        
        # Remove common prefixes and HTML entities
        name = name.replace('&nbsp;', ' ')
        
        prefixes = ['朋友 · ', '家人 · ', '🌈 · ', '🐨 · ', '🏙️ · ']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Clean the name but keep Chinese characters
        cleaned = re.sub(r'[^\u4e00-\u9fff\w\s-]', '', name)
        return cleaned.strip()
    
    def _determine_message_type(self, content: str, container) -> str:
        """Determine the type of message"""
        # Check for media indicators
        media_indicators = ['[图片]', '[语音]', '[视频]', '[文件]', '[链接]', 'image', 'audio', 'video', 'file']
        if any(indicator in content.lower() for indicator in media_indicators):
            return 'media'
        
        # Check for system messages
        system_indicators = ['加入了群聊', '退出了群聊', '邀请', '撤回了一条消息', 'joined', 'left', 'invited']
        if any(indicator in content for indicator in system_indicators):
            return 'system'
        
        return 'text'
    
    def analyze_user_communication_style(self, conversations: List[Dict[str, Any]], user_name: str = "Tom Zhao") -> Dict[str, Any]:
        """
        Analyze user's communication style from conversations
        
        Args:
            conversations: List of conversation data
            user_name: Name of the user to analyze
            
        Returns:
            Dictionary containing communication style analysis
        """
        user_messages = []
        
        # Collect all messages from the user (look for AlphaXuan or the actual name)
        user_identifiers = [user_name, "AlphaXuan", "Tom", "赵"]
        
        for conv in conversations:
            for msg in conv['messages']:
                if msg['type'] == 'text' and self._is_user_message(msg['sender'], user_identifiers):
                    user_messages.append(msg['content'])
        
        if not user_messages:
            return {'error': f'No user messages found for analysis. Looking for: {user_identifiers}'}
        
        analysis = {
            'total_messages': len(user_messages),
            'average_length': sum(len(msg) for msg in user_messages) / len(user_messages),
            'tone_characteristics': self._analyze_tone(user_messages),
            'common_phrases': self._extract_common_phrases(user_messages),
            'communication_patterns': self._analyze_patterns(user_messages),
            'sample_messages': user_messages[:20]  # First 20 messages as samples
        }
        
        return analysis
    
    def _is_user_message(self, sender: str, user_identifiers: List[str]) -> bool:
        """Check if a message is from the specified user"""
        sender_lower = sender.lower()
        for identifier in user_identifiers:
            if identifier.lower() in sender_lower:
                return True
        return False
    
    def _analyze_tone(self, messages: List[str]) -> Dict[str, Any]:
        """Analyze tone characteristics of messages"""
        characteristics = {
            'enthusiasm_level': 0,
            'politeness_level': 0,
            'casualness_level': 0,
            'directness_level': 0
        }
        
        total_messages = len(messages)
        
        for msg in messages:
            msg_lower = msg.lower()
            
            # Enthusiasm indicators
            if '!' in msg or '！' in msg or '哈哈' in msg or '😊' in msg or '[' in msg:
                characteristics['enthusiasm_level'] += 1
            
            # Politeness indicators
            if any(word in msg_lower for word in ['谢谢', 'thank', '请', 'please', '麻烦', '不好意思', '好的']):
                characteristics['politeness_level'] += 1
            
            # Casualness indicators
            if any(word in msg_lower for word in ['哈哈', '嗯', '啊', '呢', '吧', 'haha', 'yeah', 'ok', '好滴']):
                characteristics['casualness_level'] += 1
            
            # Directness indicators (short, imperative messages)
            if len(msg) < 20 and not any(word in msg_lower for word in ['please', '请', '能否', 'could']):
                characteristics['directness_level'] += 1
        
        # Convert to percentages
        for key in characteristics:
            characteristics[key] = round((characteristics[key] / total_messages) * 100, 2)
        
        return characteristics
    
    def _extract_common_phrases(self, messages: List[str]) -> List[str]:
        """Extract commonly used phrases"""
        # Simple phrase extraction - count 2-4 word sequences
        from collections import Counter
        
        phrases = []
        for msg in messages:
            words = msg.split()
            # Extract 2-word phrases
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i+2])
                if len(phrase) > 3:  # Skip very short phrases
                    phrases.append(phrase.lower())
        
        # Return top 10 most common phrases
        phrase_counts = Counter(phrases)
        return [phrase for phrase, count in phrase_counts.most_common(10) if count > 1]
    
    def _analyze_patterns(self, messages: List[str]) -> Dict[str, Any]:
        """Analyze communication patterns"""
        patterns = {
            'uses_emojis': False,
            'prefers_short_messages': False,
            'uses_questions': False,
            'uses_english': False,
            'uses_chinese': False
        }
        
        emoji_count = 0
        short_msg_count = 0
        question_count = 0
        english_count = 0
        chinese_count = 0
        
        for msg in messages:
            # Check for emojis and emoticons (including WeChat style)
            if re.search(r'[😀-🿿]|[🀀-🏿]|[🐀-🟿]|[🤀-🧿]|\[[A-Z][a-z]+\]', msg):
                emoji_count += 1
            
            # Check message length
            if len(msg) < 30:
                short_msg_count += 1
            
            # Check for questions
            if '?' in msg or '？' in msg or any(word in msg for word in ['什么', '怎么', '为什么', 'what', 'how', 'why']):
                question_count += 1
            
            # Check for English
            if re.search(r'[a-zA-Z]+', msg):
                english_count += 1
            
            # Check for Chinese
            if re.search(r'[\u4e00-\u9fff]', msg):
                chinese_count += 1
        
        total = len(messages)
        patterns['uses_emojis'] = emoji_count > total * 0.1
        patterns['prefers_short_messages'] = short_msg_count > total * 0.6
        patterns['uses_questions'] = question_count > total * 0.2
        patterns['uses_english'] = english_count > total * 0.3
        patterns['uses_chinese'] = chinese_count > total * 0.3
        
        return patterns 