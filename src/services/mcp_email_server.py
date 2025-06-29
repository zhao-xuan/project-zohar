#!/usr/bin/env python3
"""
MCP Email Management Server

A comprehensive Model Context Protocol (MCP) server that provides email management
capabilities across multiple email providers:
- Microsoft Outlook (via Microsoft Graph API)
- Gmail (via Google Gmail API)
- QQ Mail (via SMTP/IMAP)

Functions provided:
1. Get latest emails
2. Search emails by keyword
3. Send emails
4. Reply with templates
5. Forward emails
6. Move emails to folders
7. Flag emails
8. Summarize emails and extract action items
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# Core dependencies
import httpx
from pydantic import BaseModel

# Google Gmail API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Email protocols for QQ Mail
import smtplib
import imaplib
import email
from email.header import decode_header

# Microsoft Graph API (we'll use httpx for REST calls)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Configuration for email providers"""
    provider: str
    credentials: Dict[str, Any]
    settings: Dict[str, Any] = None

@dataclass
class EmailMessage:
    """Standardized email message structure"""
    id: str
    subject: str
    sender: str
    recipients: List[str]
    cc: List[str] = None
    bcc: List[str] = None
    body: str = ""
    html_body: str = ""
    attachments: List[Dict] = None
    date: datetime = None
    is_read: bool = False
    is_flagged: bool = False
    folder: str = ""
    labels: List[str] = None

@dataclass
class EmailSummary:
    """Email summary with action items"""
    summary: str
    action_items: List[str]
    key_info: Dict[str, Any]
    links: List[str]
    priority: str
    deadline: Optional[datetime] = None

class EmailProvider:
    """Base class for email providers"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.authenticated = False
    
    async def authenticate(self) -> bool:
        """Authenticate with the email provider"""
        raise NotImplementedError
    
    async def get_latest_emails(self, count: int = 10) -> List[EmailMessage]:
        """Get latest emails"""
        raise NotImplementedError
    
    async def search_emails(self, keyword: str, folders: List[str] = None) -> List[EmailMessage]:
        """Search emails by keyword"""
        raise NotImplementedError
    
    async def send_email(self, to: List[str], subject: str, body: str, 
                        cc: List[str] = None, bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send an email"""
        raise NotImplementedError
    
    async def reply_to_email(self, email_id: str, template: str, 
                           template_vars: Dict[str, str] = None) -> bool:
        """Reply to an email using a template"""
        raise NotImplementedError
    
    async def forward_email(self, email_id: str, to: List[str], 
                          comment: str = "") -> bool:
        """Forward an email"""
        raise NotImplementedError
    
    async def move_email(self, email_id: str, folder: str) -> bool:
        """Move email to a folder"""
        raise NotImplementedError
    
    async def flag_email(self, email_id: str, flagged: bool = True) -> bool:
        """Flag/unflag an email"""
        raise NotImplementedError
    
    async def summarize_email(self, email_id: str) -> EmailSummary:
        """Summarize email content and extract action items"""
        raise NotImplementedError

class GmailProvider(EmailProvider):
    """Gmail API provider implementation"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.service = None
        self.credentials = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2"""
        try:
            # Load credentials from config
            creds_path = self.config.credentials.get('credentials_file')
            token_path = self.config.credentials.get('token_file')
            
            creds = None
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = Flow.from_client_secrets_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/gmail.modify']
                    )
                    # This would need to be handled in a web flow for production
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            self.authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    async def get_latest_emails(self, count: int = 10) -> List[EmailMessage]:
        """Get latest emails from Gmail"""
        try:
            # Get message IDs
            results = self.service.users().messages().list(
                userId='me', maxResults=count, q='in:inbox'
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                # Get full message
                message = self.service.users().messages().get(
                    userId='me', id=msg['id']
                ).execute()
                
                email_obj = self._parse_gmail_message(message)
                email_list.append(email_obj)
            
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to get latest emails: {e}")
            return []
    
    async def search_emails(self, keyword: str, folders: List[str] = None) -> List[EmailMessage]:
        """Search emails in Gmail"""
        try:
            # Build search query
            query = f'"{keyword}"'
            if folders:
                folder_query = ' OR '.join([f'in:{folder.lower()}' for folder in folders])
                query += f' AND ({folder_query})'
            else:
                query += ' AND (in:inbox OR in:spam)'
            
            results = self.service.users().messages().list(
                userId='me', q=query
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                message = self.service.users().messages().get(
                    userId='me', id=msg['id']
                ).execute()
                
                email_obj = self._parse_gmail_message(message)
                email_list.append(email_obj)
            
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    async def send_email(self, to: List[str], subject: str, body: str,
                        cc: List[str] = None, bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send email via Gmail"""
        try:
            message = MIMEMultipart()
            message['to'] = ', '.join(to)
            message['subject'] = subject
            
            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)
            
            message.attach(MIMEText(body, 'html' if '<' in body else 'plain'))
            
            # TODO: Handle attachments
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def reply_to_email(self, email_id: str, template: str, 
                           template_vars: Dict[str, str] = None) -> bool:
        """Reply to an email using a template"""
        try:
            # Get original message
            original = self.service.users().messages().get(
                userId='me', id=email_id
            ).execute()
            
            headers = {h['name']: h['value'] for h in original['payload']['headers']}
            
            # Create reply message
            reply = MIMEMultipart()
            reply['to'] = headers.get('From', '')
            reply['subject'] = f"Re: {headers.get('Subject', '')}"
            reply['in-reply-to'] = headers.get('Message-ID', '')
            reply['references'] = headers.get('Message-ID', '')
            
            reply.attach(MIMEText(template, 'html' if '<' in template else 'plain'))
            
            raw_reply = base64.urlsafe_b64encode(
                reply.as_bytes()
            ).decode('utf-8')
            
            self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_reply,
                    'threadId': original.get('threadId')
                }
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reply to email: {e}")
            return False
    
    async def forward_email(self, email_id: str, to: List[str], 
                          comment: str = "") -> bool:
        """Forward an email"""
        try:
            # Get original message
            original = self.service.users().messages().get(
                userId='me', id=email_id
            ).execute()
            
            headers = {h['name']: h['value'] for h in original['payload']['headers']}
            
            # Extract original body
            original_body = ""
            if 'parts' in original['payload']:
                for part in original['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        original_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                if original['payload']['mimeType'] == 'text/plain':
                    data = original['payload']['body']['data']
                    original_body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Create forward message
            forward_msg = MIMEMultipart()
            forward_msg['to'] = ', '.join(to)
            forward_msg['subject'] = f"Fwd: {headers.get('Subject', '')}"
            
            # Compose forward body
            forward_body = f"{comment}\n\n" if comment else ""
            forward_body += f"---------- Forwarded message ----------\n"
            forward_body += f"From: {headers.get('From', '')}\n"
            forward_body += f"Date: {headers.get('Date', '')}\n"
            forward_body += f"Subject: {headers.get('Subject', '')}\n"
            forward_body += f"To: {headers.get('To', '')}\n\n"
            forward_body += original_body
            
            forward_msg.attach(MIMEText(forward_body, 'plain'))
            
            raw_forward = base64.urlsafe_b64encode(
                forward_msg.as_bytes()
            ).decode('utf-8')
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_forward}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to forward email: {e}")
            return False
    
    async def move_email(self, email_id: str, folder: str) -> bool:
        """Move email to a folder"""
        try:
            # Gmail uses labels instead of folders
            # First, get current labels
            message = self.service.users().messages().get(
                userId='me', id=email_id
            ).execute()
            
            current_labels = message.get('labelIds', [])
            
            # Remove INBOX label and add folder label
            labels_to_remove = ['INBOX']
            labels_to_add = []
            
            # Convert folder name to Gmail label
            if folder.lower() == 'trash':
                labels_to_add.append('TRASH')
            elif folder.lower() == 'spam':
                labels_to_add.append('SPAM')
            elif folder.lower() == 'archive':
                labels_to_remove.append('INBOX')  # Archiving removes from inbox
            else:
                # For custom folders, you'd need to create/find the label ID
                logger.warning(f"Custom folder '{folder}' not implemented for Gmail")
                return False
            
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={
                    'addLabelIds': labels_to_add,
                    'removeLabelIds': labels_to_remove
                }
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False
    
    async def flag_email(self, email_id: str, flagged: bool = True) -> bool:
        """Flag/unflag an email"""
        try:
            if flagged:
                # Add STARRED label
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': ['STARRED']}
                ).execute()
            else:
                # Remove STARRED label
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': ['STARRED']}
                ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to flag email: {e}")
            return False
    
    def _parse_gmail_message(self, message: Dict) -> EmailMessage:
        """Parse Gmail API message format to EmailMessage"""
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            if message['payload']['mimeType'] == 'text/plain':
                data = message['payload']['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return EmailMessage(
            id=message['id'],
            subject=headers.get('Subject', ''),
            sender=headers.get('From', ''),
            recipients=[headers.get('To', '')],
            cc=[headers.get('Cc', '')] if headers.get('Cc') else [],
            body=body,
            date=datetime.fromtimestamp(int(message['internalDate']) / 1000),
            is_read='UNREAD' not in message['labelIds'],
            is_flagged='STARRED' in message['labelIds'],
            labels=message.get('labelIds', [])
        )

class OutlookProvider(EmailProvider):
    """Microsoft Outlook (Graph API) provider implementation"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.access_token = self.config.credentials.get('access_token')
        self.client = httpx.AsyncClient()
        self.graph_url = "https://graph.microsoft.com/v1.0"
    
    async def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API"""
        try:
            # For production, implement proper OAuth2 flow
            # For now, assume we have a valid access token
            self.access_token = self.config.credentials.get('access_token')
            
            if not self.access_token:
                logger.error("No access token provided for Outlook")
                return False
            
            # Test the token
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = await self.client.get(
                f"{self.graph_url}/me", headers=headers
            )
            
            if response.status_code == 200:
                self.authenticated = True
                return True
            else:
                logger.error(f"Outlook authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Outlook authentication error: {e}")
            return False
    
    async def get_latest_emails(self, count: int = 10) -> List[EmailMessage]:
        """Get latest emails from Outlook"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = await self.client.get(
                f"{self.graph_url}/me/messages?$top={count}&$orderby=receivedDateTime desc",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                emails = []
                
                for msg in data.get('value', []):
                    email_obj = self._parse_outlook_message(msg)
                    emails.append(email_obj)
                
                return emails
            else:
                logger.error(f"Failed to get latest emails: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting latest emails: {e}")
            return []
    
    async def search_emails(self, keyword: str, folders: List[str] = None) -> List[EmailMessage]:
        """Search emails in Outlook"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Build search query
            search_query = f"$search=\"{keyword}\""
            if folders:
                # For simplicity, just search in inbox and junk
                search_query += "&$filter=parentFolderId eq 'inbox' or parentFolderId eq 'junkemail'"
            
            response = await self.client.get(
                f"{self.graph_url}/me/messages?{search_query}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                emails = []
                
                for msg in data.get('value', []):
                    email_obj = self._parse_outlook_message(msg)
                    emails.append(email_obj)
                
                return emails
            else:
                logger.error(f"Failed to search emails: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    async def send_email(self, to: List[str], subject: str, body: str,
                        cc: List[str] = None, bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send email via Outlook"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if '<' in body else "Text",
                        "content": body
                    },
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in to]
                }
            }
            
            if cc:
                email_data["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in cc
                ]
            
            if bcc:
                email_data["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in bcc
                ]
            
            response = await self.client.post(
                f"{self.graph_url}/me/sendMail",
                headers=headers,
                json=email_data
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def reply_to_email(self, email_id: str, template: str, 
                           template_vars: Dict[str, str] = None) -> bool:
        """Reply to an email using a template"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            reply_data = {
                "message": {
                    "body": {
                        "contentType": "HTML" if '<' in template else "Text",
                        "content": template
                    }
                }
            }
            
            response = await self.client.post(
                f"{self.graph_url}/me/messages/{email_id}/reply",
                headers=headers,
                json=reply_data
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to reply to email: {e}")
            return False
    
    async def forward_email(self, email_id: str, to: List[str], 
                          comment: str = "") -> bool:
        """Forward an email"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            forward_data = {
                "message": {
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in to]
                },
                "comment": comment
            }
            
            response = await self.client.post(
                f"{self.graph_url}/me/messages/{email_id}/forward",
                headers=headers,
                json=forward_data
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to forward email: {e}")
            return False
    
    async def move_email(self, email_id: str, folder: str) -> bool:
        """Move email to a folder"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Map folder names to Outlook folder IDs
            folder_map = {
                'inbox': 'inbox',
                'sent': 'sentitems',
                'drafts': 'drafts',
                'trash': 'deleteditems',
                'junk': 'junkemail',
                'archive': 'archive'
            }
            
            folder_id = folder_map.get(folder.lower(), folder)
            
            move_data = {
                "destinationId": folder_id
            }
            
            response = await self.client.post(
                f"{self.graph_url}/me/messages/{email_id}/move",
                headers=headers,
                json=move_data
            )
            
            return response.status_code == 201
            
        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False
    
    async def flag_email(self, email_id: str, flagged: bool = True) -> bool:
        """Flag/unflag an email"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            flag_data = {
                "flag": {
                    "flagStatus": "flagged" if flagged else "notFlagged"
                }
            }
            
            response = await self.client.patch(
                f"{self.graph_url}/me/messages/{email_id}",
                headers=headers,
                json=flag_data
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to flag email: {e}")
            return False
    
    def _parse_outlook_message(self, message: Dict) -> EmailMessage:
        """Parse Outlook API message format to EmailMessage"""
        return EmailMessage(
            id=message['id'],
            subject=message.get('subject', ''),
            sender=message.get('from', {}).get('emailAddress', {}).get('address', ''),
            recipients=[r['emailAddress']['address'] for r in message.get('toRecipients', [])],
            cc=[r['emailAddress']['address'] for r in message.get('ccRecipients', [])],
            body=message.get('body', {}).get('content', ''),
            date=datetime.fromisoformat(message['receivedDateTime'].replace('Z', '+00:00')),
            is_read=message.get('isRead', False),
            is_flagged=message.get('flag', {}).get('flagStatus') == 'flagged'
        )

class QQMailProvider(EmailProvider):
    """QQ Mail provider using SMTP/IMAP"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.smtp_server = "smtp.qq.com"
        self.imap_server = "imap.qq.com"
        self.smtp_port = 587
        self.imap_port = 993
        self.username = self.config.credentials.get('username')
        self.password = self.config.credentials.get('password')  # App password
    
    async def authenticate(self) -> bool:
        """Test SMTP/IMAP connections"""
        try:
            # Test SMTP
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.quit()
            
            # Test IMAP
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.logout()
            
            self.authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"QQ Mail authentication failed: {e}")
            return False
    
    async def get_latest_emails(self, count: int = 10) -> List[EmailMessage]:
        """Get latest emails from QQ Mail via IMAP"""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.select('INBOX')
            
            # Search for all emails and get the latest ones
            _, message_ids = imap.search(None, 'ALL')
            message_ids = message_ids[0].split()
            
            # Get the last 'count' messages
            latest_ids = message_ids[-count:] if len(message_ids) >= count else message_ids
            
            emails = []
            for msg_id in reversed(latest_ids):  # Most recent first
                _, msg_data = imap.fetch(msg_id, '(RFC822)')
                email_obj = self._parse_imap_message(msg_data[0][1], msg_id.decode())
                emails.append(email_obj)
            
            imap.close()
            imap.logout()
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get latest emails: {e}")
            return []
    
    async def search_emails(self, keyword: str, folders: List[str] = None) -> List[EmailMessage]:
        """Search emails in QQ Mail"""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            
            emails = []
            folders_to_search = folders if folders else ['INBOX', 'Junk']
            
            for folder in folders_to_search:
                try:
                    imap.select(folder)
                    # Search for keyword in subject and body
                    _, message_ids = imap.search(None, f'(OR SUBJECT "{keyword}" BODY "{keyword}")')
                    
                    if message_ids[0]:
                        for msg_id in message_ids[0].split():
                            _, msg_data = imap.fetch(msg_id, '(RFC822)')
                            email_obj = self._parse_imap_message(msg_data[0][1], msg_id.decode())
                            email_obj.folder = folder
                            emails.append(email_obj)
                except:
                    continue  # Skip folders that don't exist
            
            imap.close()
            imap.logout()
            return emails
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    async def send_email(self, to: List[str], subject: str, body: str,
                        cc: List[str] = None, bcc: List[str] = None,
                        attachments: List[Dict] = None) -> bool:
        """Send email via QQ Mail SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            msg.attach(MIMEText(body, 'html' if '<' in body else 'plain', 'utf-8'))
            
            # TODO: Handle attachments
            
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp.starttls()
            smtp.login(self.username, self.password)
            
            recipients = to + (cc or []) + (bcc or [])
            smtp.send_message(msg, to_addrs=recipients)
            smtp.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def reply_to_email(self, email_id: str, template: str, 
                           template_vars: Dict[str, str] = None) -> bool:
        """Reply to an email using a template"""
        try:
            # Get original email first
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.select('INBOX')
            
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            original_msg = email.message_from_bytes(msg_data[0][1])
            
            imap.close()
            imap.logout()
            
            # Create reply
            reply = MIMEMultipart()
            reply['From'] = self.username
            reply['To'] = original_msg.get('From', '')
            reply['Subject'] = f"Re: {original_msg.get('Subject', '')}"
            reply['In-Reply-To'] = original_msg.get('Message-ID', '')
            reply['References'] = original_msg.get('Message-ID', '')
            
            reply.attach(MIMEText(template, 'html' if '<' in template else 'plain', 'utf-8'))
            
            # Send reply
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(reply)
            smtp.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reply to email: {e}")
            return False
    
    async def forward_email(self, email_id: str, to: List[str], 
                          comment: str = "") -> bool:
        """Forward an email"""
        try:
            # Get original email
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.select('INBOX')
            
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            original_msg = email.message_from_bytes(msg_data[0][1])
            
            imap.close()
            imap.logout()
            
            # Extract original content
            original_body = ""
            if original_msg.is_multipart():
                for part in original_msg.walk():
                    if part.get_content_type() == "text/plain":
                        original_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                original_body = original_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Create forward message
            forward_msg = MIMEMultipart()
            forward_msg['From'] = self.username
            forward_msg['To'] = ', '.join(to)
            forward_msg['Subject'] = f"Fwd: {original_msg.get('Subject', '')}"
            
            # Compose forward body
            forward_body = f"{comment}\n\n" if comment else ""
            forward_body += f"---------- Forwarded message ----------\n"
            forward_body += f"From: {original_msg.get('From', '')}\n"
            forward_body += f"Date: {original_msg.get('Date', '')}\n"
            forward_body += f"Subject: {original_msg.get('Subject', '')}\n"
            forward_body += f"To: {original_msg.get('To', '')}\n\n"
            forward_body += original_body
            
            forward_msg.attach(MIMEText(forward_body, 'plain', 'utf-8'))
            
            # Send forward
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(forward_msg, to_addrs=to)
            smtp.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to forward email: {e}")
            return False
    
    async def move_email(self, email_id: str, folder: str) -> bool:
        """Move email to a folder (IMAP folder operations)"""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.select('INBOX')
            
            # Copy to destination folder
            imap.copy(email_id, folder)
            
            # Mark original as deleted
            imap.store(email_id, '+FLAGS', '\\Deleted')
            
            # Expunge to actually move
            imap.expunge()
            
            imap.close()
            imap.logout()
            return True
            
        except Exception as e:
            logger.error(f"Failed to move email: {e}")
            return False
    
    async def flag_email(self, email_id: str, flagged: bool = True) -> bool:
        """Flag/unflag an email"""
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            imap.select('INBOX')
            
            if flagged:
                imap.store(email_id, '+FLAGS', '\\Flagged')
            else:
                imap.store(email_id, '-FLAGS', '\\Flagged')
            
            imap.close()
            imap.logout()
            return True
            
        except Exception as e:
            logger.error(f"Failed to flag email: {e}")
            return False
    
    def _parse_imap_message(self, raw_email: bytes, msg_id: str) -> EmailMessage:
        """Parse IMAP message to EmailMessage"""
        msg = email.message_from_bytes(raw_email)
        
        # Decode headers
        subject = self._decode_header(msg.get('Subject', ''))
        sender = self._decode_header(msg.get('From', ''))
        to = self._decode_header(msg.get('To', ''))
        
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return EmailMessage(
            id=msg_id,
            subject=subject,
            sender=sender,
            recipients=[to],
            body=body,
            date=datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(msg.get('Date'))))
        )
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        decoded = decode_header(header)
        result = ""
        for part, encoding in decoded:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += part
        return result

class EmailSummarizer:
    """Email content summarizer and action item extractor"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
    
    async def summarize_email(self, email: EmailMessage) -> EmailSummary:
        """Summarize email and extract action items"""
        try:
            # Extract links
            links = self._extract_links(email.body)
            
            # If we have an LLM service, use it for intelligent summarization
            if self.llm_service:
                summary, action_items, key_info, priority = await self._llm_summarize(email)
            else:
                # Fallback to rule-based summarization
                summary, action_items, key_info, priority = self._rule_based_summarize(email)
            
            return EmailSummary(
                summary=summary,
                action_items=action_items,
                key_info=key_info,
                links=links,
                priority=priority
            )
            
        except Exception as e:
            logger.error(f"Failed to summarize email: {e}")
            return EmailSummary(
                summary="Failed to generate summary",
                action_items=[],
                key_info={},
                links=[],
                priority="low"
            )
    
    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    async def _llm_summarize(self, email: EmailMessage) -> tuple:
        """Use LLM for intelligent summarization"""
        prompt = f"""
        Please analyze this email and provide:
        1. A concise summary (2-3 sentences)
        2. Action items (if any)
        3. Key information (dates, numbers, names, etc.)
        4. Priority level (high/medium/low)
        
        Email:
        Subject: {email.subject}
        From: {email.sender}
        Body: {email.body[:1000]}...
        
        Format your response as JSON with keys: summary, action_items, key_info, priority
        """
        
        try:
            # This would call your LLM service
            response = await self.llm_service.generate(prompt)
            parsed = json.loads(response)
            
            return (
                parsed.get('summary', ''),
                parsed.get('action_items', []),
                parsed.get('key_info', {}),
                parsed.get('priority', 'medium')
            )
        except:
            return self._rule_based_summarize(email)
    
    def _rule_based_summarize(self, email: EmailMessage) -> tuple:
        """Rule-based summarization fallback"""
        # Simple rule-based analysis
        body_lower = email.body.lower()
        
        # Determine priority
        priority = "low"
        if any(word in body_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
            priority = "high"
        elif any(word in body_lower for word in ['important', 'soon', 'deadline']):
            priority = "medium"
        
        # Extract action items
        action_items = []
        action_words = ['please', 'need to', 'should', 'must', 'action required']
        sentences = email.body.split('.')
        for sentence in sentences:
            if any(word in sentence.lower() for word in action_words):
                action_items.append(sentence.strip())
        
        # Basic summary
        summary = f"Email from {email.sender} regarding {email.subject}"
        if len(email.body) > 100:
            summary += f". {email.body[:100]}..."
        
        # Extract key info (dates, numbers, etc.)
        key_info = {}
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        dates = re.findall(date_pattern, email.body)
        if dates:
            key_info['dates'] = dates
            
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, email.body)
        if phones:
            key_info['phone_numbers'] = phones
        
        return summary, action_items, key_info, priority 

class MCPEmailServer:
    """
    Main MCP Email Server that implements the Model Context Protocol
    for email management across multiple providers
    """
    
    def __init__(self, config_path: str = None):
        self.providers: Dict[str, EmailProvider] = {}
        self.summarizer = EmailSummarizer()
        self.config = self._load_config(config_path)
        self._initialize_providers()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file or environment"""
        config = {
            "gmail": {
                "enabled": os.getenv("GMAIL_ENABLED", "false").lower() == "true",
                "credentials_file": os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json"),
                "token_file": os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
            },
            "outlook": {
                "enabled": os.getenv("OUTLOOK_ENABLED", "false").lower() == "true",
                "client_id": os.getenv("OUTLOOK_CLIENT_ID"),
                "client_secret": os.getenv("OUTLOOK_CLIENT_SECRET"),
                "access_token": os.getenv("OUTLOOK_ACCESS_TOKEN")
            },
            "qq_mail": {
                "enabled": os.getenv("QQ_MAIL_ENABLED", "false").lower() == "true",
                "username": os.getenv("QQ_MAIL_USERNAME"),
                "password": os.getenv("QQ_MAIL_PASSWORD")  # App password
            }
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        
        return config
    
    def _initialize_providers(self):
        """Initialize enabled email providers"""
        if self.config["gmail"]["enabled"]:
            gmail_config = EmailConfig(
                provider="gmail",
                credentials={
                    "credentials_file": self.config["gmail"]["credentials_file"],
                    "token_file": self.config["gmail"]["token_file"]
                }
            )
            self.providers["gmail"] = GmailProvider(gmail_config)
        
        if self.config["outlook"]["enabled"]:
            outlook_config = EmailConfig(
                provider="outlook",
                credentials={
                    "client_id": self.config["outlook"]["client_id"],
                    "client_secret": self.config["outlook"]["client_secret"],
                    "access_token": self.config["outlook"]["access_token"]
                }
            )
            self.providers["outlook"] = OutlookProvider(outlook_config)
        
        if self.config["qq_mail"]["enabled"]:
            qq_config = EmailConfig(
                provider="qq_mail",
                credentials={
                    "username": self.config["qq_mail"]["username"],
                    "password": self.config["qq_mail"]["password"]
                }
            )
            self.providers["qq_mail"] = QQMailProvider(qq_config)
    
    async def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate all configured providers"""
        results = {}
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.authenticate()
                logger.info(f"{name} authentication: {'success' if results[name] else 'failed'}")
            except Exception as e:
                logger.error(f"Authentication error for {name}: {e}")
                results[name] = False
        return results
    
    # MCP Tool Functions
    
    async def get_latest_emails(self, provider: str = None, count: int = 10) -> Dict:
        """
        MCP Tool: Get latest emails
        
        Args:
            provider: Email provider ('gmail', 'outlook', 'qq_mail') or None for all
            count: Number of emails to retrieve (default: 10)
        
        Returns:
            Dict with emails from specified provider(s)
        """
        try:
            results = {}
            
            if provider and provider in self.providers:
                emails = await self.providers[provider].get_latest_emails(count)
                results[provider] = [self._email_to_dict(email) for email in emails]
            else:
                # Get from all providers
                for name, prov in self.providers.items():
                    if prov.authenticated:
                        emails = await prov.get_latest_emails(count)
                        results[name] = [self._email_to_dict(email) for email in emails]
            
            return {
                "success": True,
                "data": results,
                "total_emails": sum(len(emails) for emails in results.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting latest emails: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_emails(self, keyword: str, provider: str = None, 
                          include_junk: bool = True) -> Dict:
        """
        MCP Tool: Search emails by keyword
        
        Args:
            keyword: Search keyword
            provider: Email provider or None for all
            include_junk: Whether to search in junk/spam folders
        
        Returns:
            Dict with search results
        """
        try:
            results = {}
            folders = ['inbox']
            if include_junk:
                folders.extend(['spam', 'junk'])
            
            if provider and provider in self.providers:
                emails = await self.providers[provider].search_emails(keyword, folders)
                results[provider] = [self._email_to_dict(email) for email in emails]
            else:
                for name, prov in self.providers.items():
                    if prov.authenticated:
                        emails = await prov.search_emails(keyword, folders)
                        results[name] = [self._email_to_dict(email) for email in emails]
            
            return {
                "success": True,
                "data": results,
                "keyword": keyword,
                "total_results": sum(len(emails) for emails in results.values())
            }
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_email(self, provider: str, recipients: List[str], subject: str,
                        body: str, cc: List[str] = None, bcc: List[str] = None) -> Dict:
        """
        MCP Tool: Send an email
        
        Args:
            provider: Email provider to use
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
        
        Returns:
            Dict with send status
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            success = await prov.send_email(recipients, subject, body, cc, bcc)
            
            return {
                "success": success,
                "provider": provider,
                "recipients": recipients,
                "subject": subject,
                "message": "Email sent successfully" if success else "Failed to send email"
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}
    
    async def reply_with_template(self, provider: str, email_id: str, 
                                template: str, template_vars: Dict[str, str] = None) -> Dict:
        """
        MCP Tool: Reply to an email using a template
        
        Args:
            provider: Email provider
            email_id: ID of email to reply to
            template: Reply template with variables (e.g., "Hello {name}, thanks for your email...")
            template_vars: Variables to fill in template
        
        Returns:
            Dict with reply status
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            # Fill template with variables
            filled_template = template
            if template_vars:
                for key, value in template_vars.items():
                    filled_template = filled_template.replace(f"{{{key}}}", value)
            
            success = await prov.reply_to_email(email_id, filled_template, template_vars)
            
            return {
                "success": success,
                "provider": provider,
                "email_id": email_id,
                "template_used": template,
                "message": "Reply sent successfully" if success else "Failed to send reply"
            }
            
        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            return {"success": False, "error": str(e)}
    
    async def forward_email(self, provider: str, email_id: str, 
                          to_addresses: List[str], comment: str = "") -> Dict:
        """
        MCP Tool: Forward an email to other addresses
        
        Args:
            provider: Email provider
            email_id: ID of email to forward
            to_addresses: List of recipient addresses
            comment: Optional comment to add
        
        Returns:
            Dict with forward status
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            success = await prov.forward_email(email_id, to_addresses, comment)
            
            return {
                "success": success,
                "provider": provider,
                "email_id": email_id,
                "forwarded_to": to_addresses,
                "message": "Email forwarded successfully" if success else "Failed to forward email"
            }
            
        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            return {"success": False, "error": str(e)}
    
    async def move_email(self, provider: str, email_id: str, folder: str) -> Dict:
        """
        MCP Tool: Move email to another folder
        
        Args:
            provider: Email provider
            email_id: ID of email to move
            folder: Destination folder name
        
        Returns:
            Dict with move status
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            success = await prov.move_email(email_id, folder)
            
            return {
                "success": success,
                "provider": provider,
                "email_id": email_id,
                "folder": folder,
                "message": f"Email moved to {folder}" if success else "Failed to move email"
            }
            
        except Exception as e:
            logger.error(f"Error moving email: {e}")
            return {"success": False, "error": str(e)}
    
    async def flag_email(self, provider: str, email_id: str, flagged: bool = True) -> Dict:
        """
        MCP Tool: Flag or unflag an email
        
        Args:
            provider: Email provider
            email_id: ID of email to flag
            flagged: True to flag, False to unflag
        
        Returns:
            Dict with flag status
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            success = await prov.flag_email(email_id, flagged)
            
            return {
                "success": success,
                "provider": provider,
                "email_id": email_id,
                "flagged": flagged,
                "message": f"Email {'flagged' if flagged else 'unflagged'}" if success else "Failed to update flag"
            }
            
        except Exception as e:
            logger.error(f"Error flagging email: {e}")
            return {"success": False, "error": str(e)}
    
    async def summarize_and_extract_actions(self, provider: str, email_id: str) -> Dict:
        """
        MCP Tool: Summarize email content and extract action items
        
        Args:
            provider: Email provider
            email_id: ID of email to summarize
        
        Returns:
            Dict with summary and action items
        """
        try:
            if provider not in self.providers:
                return {"success": False, "error": f"Provider {provider} not configured"}
            
            prov = self.providers[provider]
            if not prov.authenticated:
                return {"success": False, "error": f"Provider {provider} not authenticated"}
            
            # Get the email first
            # This is a simplified approach - in practice, you'd need to implement
            # get_email_by_id in each provider
            emails = await prov.get_latest_emails(50)  # Get recent emails
            target_email = None
            for email in emails:
                if email.id == email_id:
                    target_email = email
                    break
            
            if not target_email:
                return {"success": False, "error": "Email not found"}
            
            summary = await self.summarizer.summarize_email(target_email)
            
            return {
                "success": True,
                "provider": provider,
                "email_id": email_id,
                "summary": summary.summary,
                "action_items": summary.action_items,
                "key_info": summary.key_info,
                "links": summary.links,
                "priority": summary.priority,
                "deadline": summary.deadline.isoformat() if summary.deadline else None
            }
            
        except Exception as e:
            logger.error(f"Error summarizing email: {e}")
            return {"success": False, "error": str(e)}
    
    def _email_to_dict(self, email: EmailMessage) -> Dict:
        """Convert EmailMessage to dictionary for JSON serialization"""
        return {
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,
            "recipients": email.recipients,
            "cc": email.cc or [],
            "bcc": email.bcc or [],
            "body": email.body[:500] + "..." if len(email.body) > 500 else email.body,  # Truncate for overview
            "html_body": email.html_body[:500] + "..." if email.html_body and len(email.html_body) > 500 else email.html_body,
            "date": email.date.isoformat() if email.date else None,
            "is_read": email.is_read,
            "is_flagged": email.is_flagged,
            "folder": email.folder,
            "labels": email.labels or []
        }
    
    # MCP Protocol Implementation
    
    def get_mcp_tools(self) -> List[Dict]:
        """Return list of available MCP tools"""
        return [
            {
                "name": "get_latest_emails",
                "description": "Get the latest emails from specified provider(s)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()) + [None],
                            "description": "Email provider to use, or None for all providers"
                        },
                        "count": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to retrieve"
                        }
                    }
                }
            },
            {
                "name": "search_emails",
                "description": "Search emails by keyword in inbox and junk folders",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Search keyword or phrase"
                        },
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()) + [None],
                            "description": "Email provider to search, or None for all"
                        },
                        "include_junk": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to include junk/spam folders in search"
                        }
                    },
                    "required": ["keyword"]
                }
            },
            {
                "name": "send_email",
                "description": "Send an email through specified provider",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider to use for sending"
                        },
                        "recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (supports HTML)"
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CC recipients (optional)"
                        },
                        "bcc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "BCC recipients (optional)"
                        }
                    },
                    "required": ["provider", "recipients", "subject", "body"]
                }
            },
            {
                "name": "reply_with_template",
                "description": "Reply to an email using a customizable template",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider"
                        },
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to reply to"
                        },
                        "template": {
                            "type": "string",
                            "description": "Reply template with variables like {name}, {company}, etc."
                        },
                        "template_vars": {
                            "type": "object",
                            "description": "Variables to fill in the template"
                        }
                    },
                    "required": ["provider", "email_id", "template"]
                }
            },
            {
                "name": "forward_email",
                "description": "Forward an email to other addresses",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider"
                        },
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to forward"
                        },
                        "to_addresses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of addresses to forward to"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Optional comment to add to forwarded email"
                        }
                    },
                    "required": ["provider", "email_id", "to_addresses"]
                }
            },
            {
                "name": "move_email",
                "description": "Move an email to another folder",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider"
                        },
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to move"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Destination folder name"
                        }
                    },
                    "required": ["provider", "email_id", "folder"]
                }
            },
            {
                "name": "flag_email",
                "description": "Flag or unflag an email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider"
                        },
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to flag"
                        },
                        "flagged": {
                            "type": "boolean",
                            "default": True,
                            "description": "True to flag, False to unflag"
                        }
                    },
                    "required": ["provider", "email_id"]
                }
            },
            {
                "name": "summarize_and_extract_actions",
                "description": "Summarize email content and extract action items with links and key info",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": list(self.providers.keys()),
                            "description": "Email provider"
                        },
                        "email_id": {
                            "type": "string",
                            "description": "ID of the email to summarize"
                        }
                    },
                    "required": ["provider", "email_id"]
                }
            }
        ]
    
    async def handle_mcp_call(self, tool_name: str, parameters: Dict) -> Dict:
        """Handle MCP tool calls"""
        try:
            if tool_name == "get_latest_emails":
                return await self.get_latest_emails(
                    provider=parameters.get("provider"),
                    count=parameters.get("count", 10)
                )
            elif tool_name == "search_emails":
                return await self.search_emails(
                    keyword=parameters["keyword"],
                    provider=parameters.get("provider"),
                    include_junk=parameters.get("include_junk", True)
                )
            elif tool_name == "send_email":
                return await self.send_email(
                    provider=parameters["provider"],
                    recipients=parameters["recipients"],
                    subject=parameters["subject"],
                    body=parameters["body"],
                    cc=parameters.get("cc"),
                    bcc=parameters.get("bcc")
                )
            elif tool_name == "reply_with_template":
                return await self.reply_with_template(
                    provider=parameters["provider"],
                    email_id=parameters["email_id"],
                    template=parameters["template"],
                    template_vars=parameters.get("template_vars")
                )
            elif tool_name == "forward_email":
                return await self.forward_email(
                    provider=parameters["provider"],
                    email_id=parameters["email_id"],
                    to_addresses=parameters["to_addresses"],
                    comment=parameters.get("comment", "")
                )
            elif tool_name == "move_email":
                return await self.move_email(
                    provider=parameters["provider"],
                    email_id=parameters["email_id"],
                    folder=parameters["folder"]
                )
            elif tool_name == "flag_email":
                return await self.flag_email(
                    provider=parameters["provider"],
                    email_id=parameters["email_id"],
                    flagged=parameters.get("flagged", True)
                )
            elif tool_name == "summarize_and_extract_actions":
                return await self.summarize_and_extract_actions(
                    provider=parameters["provider"],
                    email_id=parameters["email_id"]
                )
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
                
        except KeyError as e:
            return {"success": False, "error": f"Missing required parameter: {e}"}
        except Exception as e:
            logger.error(f"Error handling MCP call {tool_name}: {e}")
            return {"success": False, "error": str(e)}

# Main server runner
async def main():
    """Main function to run the MCP Email Server"""
    server = MCPEmailServer()
    
    # Authenticate all providers
    auth_results = await server.authenticate_all()
    logger.info(f"Authentication results: {auth_results}")
    
    # Start the server (this would typically be integrated with your MCP framework)
    logger.info("MCP Email Server is ready!")
    logger.info(f"Available providers: {list(server.providers.keys())}")
    logger.info(f"Available tools: {[tool['name'] for tool in server.get_mcp_tools()]}")
    
    # Example usage
    if any(auth_results.values()):
        # Get latest emails example
        result = await server.get_latest_emails(count=5)
        logger.info(f"Latest emails result: {result}")

if __name__ == "__main__":
    asyncio.run(main()) 