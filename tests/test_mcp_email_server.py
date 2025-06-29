#!/usr/bin/env python3
"""
Unit tests for MCP Email Server

Tests the email provider implementations and MCP server functionality.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.mcp_email_server import (
    MCPEmailServer,
    GmailProvider,
    OutlookProvider,
    QQMailProvider,
    EmailConfig,
    EmailMessage,
    EmailSummary,
    EmailSummarizer
)

class TestEmailMessage:
    """Test EmailMessage data class"""
    
    def test_email_message_creation(self):
        """Test creating an EmailMessage"""
        email = EmailMessage(
            id="test_123",
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            body="Test body content"
        )
        
        assert email.id == "test_123"
        assert email.subject == "Test Subject"
        assert email.sender == "sender@example.com"
        assert email.recipients == ["recipient@example.com"]
        assert email.body == "Test body content"
        assert email.cc is None
        assert email.is_read is False

class TestEmailSummarizer:
    """Test EmailSummarizer functionality"""
    
    def test_extract_links(self):
        """Test link extraction from text"""
        summarizer = EmailSummarizer()
        text = "Check out https://example.com and http://test.org for more info"
        
        links = summarizer._extract_links(text)
        
        assert len(links) == 2
        assert "https://example.com" in links
        assert "http://test.org" in links
    
    def test_rule_based_summarize(self):
        """Test rule-based email summarization"""
        summarizer = EmailSummarizer()
        
        email = EmailMessage(
            id="test_456",
            subject="Urgent: Project Deadline",
            sender="boss@company.com",
            recipients=["me@company.com"],
            body="Please complete the project by Friday. This is urgent and critical for our success."
        )
        
        summary, action_items, key_info, priority = summarizer._rule_based_summarize(email)
        
        assert priority == "high"  # Should detect "urgent" and "critical"
        assert "boss@company.com" in summary
        assert "Urgent: Project Deadline" in summary
        assert len(action_items) > 0  # Should find "Please complete"

class TestMCPEmailServer:
    """Test MCP Email Server functionality"""
    
    def test_server_initialization(self):
        """Test server initialization without config"""
        server = MCPEmailServer()
        
        assert isinstance(server.providers, dict)
        assert isinstance(server.config, dict)
        assert server.summarizer is not None
    
    def test_config_loading(self):
        """Test configuration loading from environment"""
        with patch.dict(os.environ, {
            'GMAIL_ENABLED': 'true',
            'GMAIL_CREDENTIALS_FILE': 'test_creds.json',
            'OUTLOOK_ENABLED': 'false'
        }):
            server = MCPEmailServer()
            
            assert server.config['gmail']['enabled'] is True
            assert server.config['gmail']['credentials_file'] == 'test_creds.json'
            assert server.config['outlook']['enabled'] is False
    
    def test_get_mcp_tools(self):
        """Test MCP tools definition"""
        server = MCPEmailServer()
        tools = server.get_mcp_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        tool_names = [tool['name'] for tool in tools]
        expected_tools = [
            'get_latest_emails',
            'search_emails', 
            'send_email',
            'reply_with_template',
            'forward_email',
            'move_email',
            'flag_email',
            'summarize_and_extract_actions'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Check tool structure
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'parameters' in tool
    
    @pytest.mark.asyncio
    async def test_get_latest_emails_no_providers(self):
        """Test getting emails when no providers are configured"""
        server = MCPEmailServer()
        
        result = await server.get_latest_emails()
        
        assert result['success'] is True
        assert result['total_emails'] == 0
        assert isinstance(result['data'], dict)
    
    @pytest.mark.asyncio 
    async def test_handle_mcp_call_unknown_tool(self):
        """Test handling unknown MCP tool calls"""
        server = MCPEmailServer()
        
        result = await server.handle_mcp_call("unknown_tool", {})
        
        assert result['success'] is False
        assert "Unknown tool" in result['error']
    
    @pytest.mark.asyncio
    async def test_handle_mcp_call_missing_params(self):
        """Test handling MCP calls with missing parameters"""
        server = MCPEmailServer()
        
        result = await server.handle_mcp_call("search_emails", {})
        
        assert result['success'] is False
        assert "Missing required parameter" in result['error']

class TestGmailProvider:
    """Test Gmail provider implementation"""
    
    def test_gmail_provider_initialization(self):
        """Test Gmail provider initialization"""
        config = EmailConfig(
            provider="gmail",
            credentials={
                "credentials_file": "test_creds.json",
                "token_file": "test_token.json"
            }
        )
        
        provider = GmailProvider(config)
        
        assert provider.config == config
        assert provider.authenticated is False
        assert provider.service is None
    
    @pytest.mark.asyncio
    async def test_gmail_authentication_no_files(self):
        """Test Gmail authentication when credential files don't exist"""
        config = EmailConfig(
            provider="gmail",
            credentials={
                "credentials_file": "nonexistent_creds.json",
                "token_file": "nonexistent_token.json"
            }
        )
        
        provider = GmailProvider(config)
        
        # Should fail gracefully when files don't exist
        result = await provider.authenticate()
        assert result is False
        assert provider.authenticated is False

class TestOutlookProvider:
    """Test Outlook provider implementation"""
    
    def test_outlook_provider_initialization(self):
        """Test Outlook provider initialization"""
        config = EmailConfig(
            provider="outlook",
            credentials={
                "client_id": "test_client_id",
                "client_secret": "test_secret",
                "access_token": "test_token"
            }
        )
        
        provider = OutlookProvider(config)
        
        assert provider.config == config
        assert provider.authenticated is False
        assert provider.access_token == "test_token"
    
    @pytest.mark.asyncio
    async def test_outlook_authentication_no_token(self):
        """Test Outlook authentication without access token"""
        config = EmailConfig(
            provider="outlook",
            credentials={
                "client_id": "test_client_id",
                "client_secret": "test_secret"
            }
        )
        
        provider = OutlookProvider(config)
        
        result = await provider.authenticate()
        assert result is False
        assert provider.authenticated is False

class TestQQMailProvider:
    """Test QQ Mail provider implementation"""
    
    def test_qq_provider_initialization(self):
        """Test QQ Mail provider initialization"""
        config = EmailConfig(
            provider="qq_mail",
            credentials={
                "username": "test@qq.com",
                "password": "test_password"
            }
        )
        
        provider = QQMailProvider(config)
        
        assert provider.config == config
        assert provider.authenticated is False
        assert provider.username == "test@qq.com"
        assert provider.password == "test_password"
    
    def test_decode_header(self):
        """Test email header decoding"""
        config = EmailConfig(
            provider="qq_mail",
            credentials={"username": "test@qq.com", "password": "test_pass"}
        )
        
        provider = QQMailProvider(config)
        
        # Test regular string
        result = provider._decode_header("Test Subject")
        assert result == "Test Subject"
        
        # Test empty header
        result = provider._decode_header("")
        assert result == ""
        
        # Test None header
        result = provider._decode_header(None)
        assert result == ""

class TestIntegration:
    """Integration tests for the MCP email server"""
    
    @pytest.mark.asyncio
    async def test_server_workflow_no_providers(self):
        """Test complete server workflow without real providers"""
        server = MCPEmailServer()
        
        # Test authentication (should return empty dict)
        auth_results = await server.authenticate_all()
        assert isinstance(auth_results, dict)
        assert len(auth_results) == 0
        
        # Test getting latest emails
        emails_result = await server.get_latest_emails(count=5)
        assert emails_result['success'] is True
        assert emails_result['total_emails'] == 0
        
        # Test search
        search_result = await server.search_emails("test")
        assert search_result['success'] is True
        assert search_result['total_results'] == 0
    
    @pytest.mark.asyncio
    async def test_mcp_tool_calls(self):
        """Test all MCP tool calls"""
        server = MCPEmailServer()
        
        # Test get_latest_emails
        result = await server.handle_mcp_call("get_latest_emails", {"count": 5})
        assert result['success'] is True
        
        # Test search_emails
        result = await server.handle_mcp_call("search_emails", {"keyword": "test"})
        assert result['success'] is True
        
        # Test send_email (should fail due to no providers)
        result = await server.handle_mcp_call("send_email", {
            "provider": "gmail",
            "recipients": ["test@example.com"],
            "subject": "Test",
            "body": "Test body"
        })
        assert result['success'] is False
        assert "not configured" in result['error']

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 