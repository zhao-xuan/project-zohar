# MCP Email Server Documentation

## Overview

The MCP Email Server provides a comprehensive email management solution that supports multiple email providers through the Model Context Protocol (MCP). It enables seamless integration with Gmail, Microsoft Outlook, and QQ Mail for common email operations.

## Supported Providers

### 📧 Gmail (Google)
- **Protocol**: Google Gmail API
- **Authentication**: OAuth2 
- **Features**: Full API support including labels, threads, attachments

### 📧 Microsoft Outlook  
- **Protocol**: Microsoft Graph API
- **Authentication**: OAuth2
- **Features**: Complete email management with folder operations

### 📧 QQ Mail (腾讯邮箱)
- **Protocol**: SMTP/IMAP
- **Authentication**: App Password
- **Features**: Standard email operations via IMAP/SMTP

## Available Functions

### 1. Get Latest Emails
Retrieve the most recent emails from one or all providers.

```python
# Get latest 10 emails from all providers
result = await server.get_latest_emails(count=10)

# Get latest 5 emails from Gmail only
result = await server.get_latest_emails(provider="gmail", count=5)
```

### 2. Search Emails
Search emails by keyword across inbox and junk folders.

```python
# Search all providers for "meeting"
result = await server.search_emails("meeting")

# Search Gmail only, include junk folder
result = await server.search_emails("invoice", provider="gmail", include_junk=True)
```

### 3. Send Email
Send emails through any configured provider.

```python
result = await server.send_email(
    provider="gmail",
    recipients=["user@example.com"],
    subject="Test Email",
    body="Hello from MCP Email Server!",
    cc=["cc@example.com"],
    bcc=["bcc@example.com"]
)
```

### 4. Reply with Template
Reply to emails using customizable templates with variable substitution.

```python
template = "Hello {name}, thank you for your email about {subject}. I'll get back to you by {date}."
template_vars = {
    "name": "John",
    "subject": "project proposal", 
    "date": "Friday"
}

result = await server.reply_with_template(
    provider="gmail",
    email_id="email_123",
    template=template,
    template_vars=template_vars
)
```

### 5. Forward Email
Forward emails to other addresses with optional comments.

```python
result = await server.forward_email(
    provider="outlook",
    email_id="email_456",
    to_addresses=["colleague@company.com"],
    comment="Please review this and let me know your thoughts."
)
```

### 6. Move Email to Folder
Organize emails by moving them to different folders.

```python
# Move to trash
result = await server.move_email("gmail", "email_789", "trash")

# Move to custom folder
result = await server.move_email("outlook", "email_101", "Projects")
```

### 7. Flag Email
Mark emails as important/flagged for follow-up.

```python
# Flag email
result = await server.flag_email("gmail", "email_111", flagged=True)

# Unflag email  
result = await server.flag_email("gmail", "email_111", flagged=False)
```

### 8. Summarize and Extract Actions
AI-powered email summarization with action item extraction.

```python
result = await server.summarize_and_extract_actions("gmail", "email_222")

# Returns:
# {
#   "summary": "Email from John about quarterly planning meeting...",
#   "action_items": ["Schedule meeting room", "Prepare Q4 budget"],
#   "key_info": {"dates": ["2024-02-15"], "numbers": ["$50,000"]},
#   "links": ["https://calendar.company.com"],
#   "priority": "high"
# }
```

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Setup Wizard
```bash
make mcp-email-setup
# or
python scripts/setup_mcp_email.py
```

### 3. Configure Providers

#### Gmail Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth2 credentials (Desktop application)
5. Download credentials JSON file
6. Run setup wizard and provide file path

#### Outlook Setup  
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register new application in Azure AD
3. Add Microsoft Graph API permissions:
   - `Mail.ReadWrite`
   - `Mail.Send`
4. Get Client ID and Client Secret
5. Run setup wizard and provide credentials

#### QQ Mail Setup
1. Log into QQ Mail settings
2. Enable SMTP/IMAP services
3. Generate app password (not regular password)
4. Run setup wizard and provide credentials

### 4. Test Setup
```bash
# Test all providers
make mcp-email-status

# Run demo
make mcp-email-demo

# Test server functionality  
make mcp-email-test
```

## Configuration

### Environment Variables
```bash
# Gmail
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_FILE=/path/to/gmail_credentials.json
GMAIL_TOKEN_FILE=/path/to/gmail_token.json

# Outlook
OUTLOOK_ENABLED=true
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_client_secret
OUTLOOK_ACCESS_TOKEN=your_access_token

# QQ Mail
QQ_MAIL_ENABLED=true
QQ_MAIL_USERNAME=user@qq.com
QQ_MAIL_PASSWORD=app_password
```

### Configuration File
```json
{
  "gmail": {
    "enabled": true,
    "credentials_file": "config/gmail_credentials.json",
    "token_file": "config/gmail_token.json"
  },
  "outlook": {
    "enabled": true,
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "access_token": "your_token"
  },
  "qq_mail": {
    "enabled": true,
    "username": "user@qq.com",
    "password": "app_password"
  }
}
```

## MCP Integration

### Tool Definition
The server provides MCP-compatible tool definitions:

```python
server = MCPEmailServer()
tools = server.get_mcp_tools()

# Each tool includes:
# - name: Function name
# - description: What it does  
# - parameters: JSON schema for inputs
```

### Calling Tools
```python
# Handle MCP tool calls
result = await server.handle_mcp_call("get_latest_emails", {
    "provider": "gmail",
    "count": 5
})
```

## Usage Examples

### Morning Email Routine
```python
async def morning_email_routine():
    server = MCPEmailServer()
    await server.authenticate_all()
    
    # Get latest emails
    emails = await server.get_latest_emails(count=20)
    
    # Search for urgent emails
    urgent = await server.search_emails("urgent")
    
    # Summarize important emails
    for provider, email_list in emails["data"].items():
        for email in email_list[:5]:
            summary = await server.summarize_and_extract_actions(
                provider, email["id"]
            )
            if summary["priority"] == "high":
                print(f"🚨 High priority: {summary['summary']}")
```

### Auto-Reply System
```python
async def auto_reply_system():
    server = MCPEmailServer()
    await server.authenticate_all()
    
    # Search for specific emails
    vacation_emails = await server.search_emails("vacation request")
    
    template = """
    Hello {name},
    
    Thank you for your vacation request. I have received your email and will 
    review it within 24 hours. If you need immediate assistance, please 
    contact my assistant at assistant@company.com.
    
    Best regards,
    Manager
    """
    
    for provider, emails in vacation_emails["data"].items():
        for email in emails:
            await server.reply_with_template(
                provider=provider,
                email_id=email["id"],
                template=template,
                template_vars={"name": email["sender"].split("@")[0]}
            )
```

### Email Analytics
```python
async def email_analytics():
    server = MCPEmailServer()
    await server.authenticate_all()
    
    # Get all recent emails
    emails = await server.get_latest_emails(count=100)
    
    analytics = {
        "total": 0,
        "by_provider": {},
        "high_priority": 0,
        "action_items": []
    }
    
    for provider, email_list in emails["data"].items():
        analytics["by_provider"][provider] = len(email_list)
        analytics["total"] += len(email_list)
        
        for email in email_list:
            summary = await server.summarize_and_extract_actions(
                provider, email["id"]
            )
            
            if summary["priority"] == "high":
                analytics["high_priority"] += 1
            
            analytics["action_items"].extend(summary["action_items"])
    
    print(f"📊 Email Analytics: {analytics}")
```

## Troubleshooting

### Common Issues

#### Gmail Authentication
- Ensure OAuth2 scope includes `gmail.modify`
- Check credentials file path is correct
- Verify Google Cloud project has Gmail API enabled

#### Outlook Authentication  
- Confirm Azure app has correct Graph permissions
- Check access token validity
- Ensure tenant allows the application

#### QQ Mail Connection
- Verify SMTP/IMAP is enabled in QQ Mail settings  
- Use app password, not account password
- Check firewall allows SMTP/IMAP ports

### Error Codes
- `401`: Authentication failed - check credentials
- `403`: Insufficient permissions - verify API access
- `404`: Email not found - check email ID
- `429`: Rate limiting - reduce request frequency

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

server = MCPEmailServer()
# Will show detailed logs
```

## Security Considerations

### Credential Storage
- Store credentials securely (use environment variables)
- Never commit credentials to version control
- Use app passwords where possible
- Regularly rotate access tokens

### Network Security
- Use HTTPS/TLS for all API calls
- Validate SSL certificates
- Consider using VPN for sensitive operations

### Data Privacy
- Minimize email content stored in logs
- Implement data retention policies
- Follow GDPR/privacy regulations
- Encrypt sensitive configuration files

## Performance Optimization

### Parallel Operations
```python
# Process multiple providers simultaneously
import asyncio

tasks = []
for provider in ["gmail", "outlook", "qq_mail"]:
    task = server.get_latest_emails(provider=provider, count=10)
    tasks.append(task)

results = await asyncio.gather(*tasks)
```

### Caching
- Cache authentication tokens
- Store frequently accessed emails
- Implement rate limiting
- Use connection pooling

### Batch Operations
- Group similar operations
- Use provider-specific batch APIs where available
- Implement queue for background processing

## API Reference

See the inline documentation in `src/services/mcp_email_server.py` for complete API reference with parameter details and return types.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## License

This MCP Email Server is part of the Personal Multi-Agent Chatbot System project. 