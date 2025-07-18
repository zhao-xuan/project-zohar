"""
Platform Integration Manager for Project Zohar.

This module provides comprehensive platform integration capabilities
including OAuth2 authentication, API management, and data synchronization.
"""

import asyncio
import json
import secrets
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from urllib.parse import urlencode, parse_qs
import logging
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout
except ImportError:
    aiohttp = None

try:
    import jwt
except ImportError:
    jwt = None

from config.settings import get_settings
from .logging import get_logger
from .privacy_filter import PrivacyFilter, PrivacyLevel

logger = get_logger(__name__)


class PlatformType(Enum):
    """Supported platform types."""
    EMAIL = "email"
    CHAT = "chat"
    SOCIAL = "social"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    CALENDAR = "calendar"
    NOTES = "notes"
    CUSTOM = "custom"


class AuthType(Enum):
    """Authentication types."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    CUSTOM = "custom"


class PlatformStatus(Enum):
    """Platform connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SUSPENDED = "suspended"


@dataclass
class PlatformCredentials:
    """Platform authentication credentials."""
    platform_id: str
    auth_type: AuthType
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformCredentials':
        """Create from dictionary."""
        if "expires_at" in data and data["expires_at"]:
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)


@dataclass
class PlatformConfig:
    """Platform configuration."""
    id: str
    name: str
    platform_type: PlatformType
    auth_type: AuthType
    base_url: str
    oauth_config: Optional[Dict[str, str]] = None
    api_endpoints: Optional[Dict[str, str]] = None
    rate_limits: Optional[Dict[str, int]] = None
    supported_features: Optional[List[str]] = None
    privacy_level: PrivacyLevel = PrivacyLevel.HIGH
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformConfig':
        """Create from dictionary."""
        return cls(**data)


class PlatformAdapter:
    """Base platform adapter for API interactions."""
    
    def __init__(
        self,
        config: PlatformConfig,
        credentials: PlatformCredentials,
        privacy_filter: PrivacyFilter
    ):
        """
        Initialize platform adapter.
        
        Args:
            config: Platform configuration
            credentials: Platform credentials
            privacy_filter: Privacy filter instance
        """
        self.config = config
        self.credentials = credentials
        self.privacy_filter = privacy_filter
        self.status = PlatformStatus.DISCONNECTED
        self.session: Optional[ClientSession] = None
        self.last_error = None
        self.request_count = 0
        self.rate_limit_reset = None
        
        logger.info(f"Platform adapter initialized for {config.name}")
    
    async def connect(self) -> bool:
        """
        Connect to the platform.
        
        Returns:
            Success status
        """
        try:
            self.status = PlatformStatus.CONNECTING
            
            # Create HTTP session
            timeout = ClientTimeout(total=30)
            self.session = ClientSession(timeout=timeout)
            
            # Authenticate
            if not await self._authenticate():
                self.status = PlatformStatus.ERROR
                return False
            
            # Test connection
            if not await self._test_connection():
                self.status = PlatformStatus.ERROR
                return False
            
            self.status = PlatformStatus.CONNECTED
            logger.info(f"Successfully connected to platform {self.config.name}")
            return True
            
        except Exception as e:
            self.status = PlatformStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Failed to connect to platform {self.config.name}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the platform."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            self.status = PlatformStatus.DISCONNECTED
            logger.info(f"Disconnected from platform {self.config.name}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from platform {self.config.name}: {e}")
    
    async def get_messages(
        self,
        limit: int = 50,
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from the platform.
        
        Args:
            limit: Maximum number of messages
            since: Get messages since this timestamp
            filters: Additional filters
            
        Returns:
            List of messages
        """
        try:
            if self.status != PlatformStatus.CONNECTED:
                raise RuntimeError(f"Platform {self.config.name} is not connected")
            
            messages = await self._fetch_messages(limit, since, filters)
            
            # Apply privacy filtering
            filtered_messages = []
            for message in messages:
                filtered_message = await self._apply_privacy_filter(message)
                filtered_messages.append(filtered_message)
            
            return filtered_messages
            
        except Exception as e:
            logger.error(f"Failed to get messages from platform {self.config.name}: {e}")
            return []
    
    async def send_message(
        self,
        content: str,
        recipient: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message via the platform.
        
        Args:
            content: Message content
            recipient: Message recipient
            message_type: Type of message
            metadata: Additional metadata
            
        Returns:
            Send result
        """
        try:
            if self.status != PlatformStatus.CONNECTED:
                raise RuntimeError(f"Platform {self.config.name} is not connected")
            
            # Apply privacy filtering to content
            safe_content, detected_pii = self.privacy_filter.anonymize_text(content)
            
            result = await self._send_message(safe_content, recipient, message_type, metadata)
            
            return {
                "success": True,
                "message_id": result.get("id"),
                "platform": self.config.name,
                "privacy_filtered": len(detected_pii) > 0,
                "detected_pii": detected_pii
            }
            
        except Exception as e:
            logger.error(f"Failed to send message via platform {self.config.name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get user information from the platform.
        
        Returns:
            User information
        """
        try:
            if self.status != PlatformStatus.CONNECTED:
                raise RuntimeError(f"Platform {self.config.name} is not connected")
            
            user_info = await self._fetch_user_info()
            
            # Apply privacy filtering
            filtered_info = self.privacy_filter.filter_data(user_info)
            
            return filtered_info
            
        except Exception as e:
            logger.error(f"Failed to get user info from platform {self.config.name}: {e}")
            return {}
    
    async def sync_data(self, data_types: List[str]) -> Dict[str, Any]:
        """
        Sync data from the platform.
        
        Args:
            data_types: Types of data to sync
            
        Returns:
            Sync results
        """
        try:
            if self.status != PlatformStatus.CONNECTED:
                raise RuntimeError(f"Platform {self.config.name} is not connected")
            
            results = {}
            
            for data_type in data_types:
                try:
                    data = await self._sync_data_type(data_type)
                    results[data_type] = {
                        "success": True,
                        "count": len(data) if isinstance(data, list) else 1,
                        "data": data
                    }
                except Exception as e:
                    results[data_type] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync data from platform {self.config.name}: {e}")
            return {}
    
    # Private methods (to be implemented by specific platform adapters)
    
    async def _authenticate(self) -> bool:
        """Authenticate with the platform."""
        if self.credentials.auth_type == AuthType.OAUTH2:
            return await self._oauth2_authenticate()
        elif self.credentials.auth_type == AuthType.API_KEY:
            return await self._api_key_authenticate()
        elif self.credentials.auth_type == AuthType.BASIC:
            return await self._basic_authenticate()
        elif self.credentials.auth_type == AuthType.BEARER:
            return await self._bearer_authenticate()
        else:
            return await self._custom_authenticate()
    
    async def _oauth2_authenticate(self) -> bool:
        """OAuth2 authentication."""
        try:
            # Check if access token is valid
            if self.credentials.access_token and self.credentials.expires_at:
                if datetime.now() < self.credentials.expires_at:
                    return True
            
            # Try to refresh token
            if self.credentials.refresh_token:
                return await self._refresh_oauth2_token()
            
            # Need to re-authenticate
            return False
            
        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            return False
    
    async def _api_key_authenticate(self) -> bool:
        """API key authentication."""
        return self.credentials.api_key is not None
    
    async def _basic_authenticate(self) -> bool:
        """Basic authentication."""
        return (self.credentials.username is not None and 
                self.credentials.password is not None)
    
    async def _bearer_authenticate(self) -> bool:
        """Bearer token authentication."""
        return self.credentials.access_token is not None
    
    async def _custom_authenticate(self) -> bool:
        """Custom authentication."""
        # To be implemented by specific platform adapters
        return True
    
    async def _refresh_oauth2_token(self) -> bool:
        """Refresh OAuth2 access token."""
        try:
            if not self.config.oauth_config or not self.credentials.refresh_token:
                return False
            
            token_url = self.config.oauth_config.get("token_url")
            if not token_url:
                return False
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret
            }
            
            async with self.session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    self.credentials.access_token = token_data.get("access_token")
                    if "refresh_token" in token_data:
                        self.credentials.refresh_token = token_data["refresh_token"]
                    
                    expires_in = token_data.get("expires_in", 3600)
                    self.credentials.expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to refresh OAuth2 token: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test platform connection."""
        # To be implemented by specific platform adapters
        return True
    
    async def _fetch_messages(
        self,
        limit: int,
        since: Optional[datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch messages from platform."""
        # To be implemented by specific platform adapters
        return []
    
    async def _send_message(
        self,
        content: str,
        recipient: str,
        message_type: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send message to platform."""
        # To be implemented by specific platform adapters
        return {}
    
    async def _fetch_user_info(self) -> Dict[str, Any]:
        """Fetch user information from platform."""
        # To be implemented by specific platform adapters
        return {}
    
    async def _sync_data_type(self, data_type: str) -> List[Dict[str, Any]]:
        """Sync specific data type from platform."""
        # To be implemented by specific platform adapters
        return []
    
    async def _apply_privacy_filter(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Apply privacy filtering to message."""
        filtered_message = message.copy()
        
        # Filter content
        if "content" in filtered_message:
            safe_content, _ = self.privacy_filter.anonymize_text(filtered_message["content"])
            filtered_message["content"] = safe_content
        
        # Filter other text fields
        for field in ["subject", "title", "description"]:
            if field in filtered_message:
                safe_text, _ = self.privacy_filter.anonymize_text(filtered_message[field])
                filtered_message[field] = safe_text
        
        return filtered_message
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to platform."""
        try:
            # Add authentication headers
            if headers is None:
                headers = {}
            
            if self.credentials.auth_type == AuthType.OAUTH2:
                headers["Authorization"] = f"Bearer {self.credentials.access_token}"
            elif self.credentials.auth_type == AuthType.API_KEY:
                headers["X-API-Key"] = self.credentials.api_key
            elif self.credentials.auth_type == AuthType.BEARER:
                headers["Authorization"] = f"Bearer {self.credentials.access_token}"
            
            # Make request
            async with self.session.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params
            ) as response:
                self.request_count += 1
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(method, url, headers, data, params)
                
                # Handle authentication errors
                if response.status == 401:
                    if self.credentials.auth_type == AuthType.OAUTH2:
                        if await self._refresh_oauth2_token():
                            return await self._make_request(method, url, headers, data, params)
                    
                    raise RuntimeError("Authentication failed")
                
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise


class PlatformManager:
    """
    Platform integration manager for handling multiple platforms.
    
    This class provides:
    - Platform registration and management
    - OAuth2 authentication flows
    - Unified API for platform interactions
    - Data synchronization
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize platform manager.
        
        Args:
            config_path: Path to platform configuration file
        """
        self.settings = get_settings()
        self.config_path = config_path or self.settings.config_dir / "platforms.json"
        self.credentials_path = self.settings.config_dir / "platform_credentials.json"
        
        # Platform management
        self.platforms: Dict[str, PlatformConfig] = {}
        self.credentials: Dict[str, PlatformCredentials] = {}
        self.adapters: Dict[str, PlatformAdapter] = {}
        
        # Privacy filter
        self.privacy_filter = PrivacyFilter()
        
        # OAuth2 state management
        self.oauth_states: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            "platforms_registered": 0,
            "platforms_connected": 0,
            "messages_processed": 0,
            "sync_operations": 0,
            "errors": 0
        }
        
        logger.info("Platform manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the platform manager.
        
        Returns:
            Success status
        """
        try:
            # Load configurations
            await self._load_platform_configs()
            await self._load_credentials()
            
            # Initialize adapters
            await self._initialize_adapters()
            
            logger.info("Platform manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize platform manager: {e}")
            return False
    
    async def register_platform(self, config: PlatformConfig) -> bool:
        """
        Register a new platform.
        
        Args:
            config: Platform configuration
            
        Returns:
            Success status
        """
        try:
            self.platforms[config.id] = config
            self.stats["platforms_registered"] += 1
            
            # Create adapter if credentials exist
            if config.id in self.credentials:
                await self._create_adapter(config.id)
            
            logger.info(f"Registered platform: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register platform {config.name}: {e}")
            return False
    
    async def connect_platform(self, platform_id: str) -> bool:
        """
        Connect to a platform.
        
        Args:
            platform_id: Platform ID
            
        Returns:
            Success status
        """
        try:
            if platform_id not in self.adapters:
                await self._create_adapter(platform_id)
            
            adapter = self.adapters[platform_id]
            
            if await adapter.connect():
                self.stats["platforms_connected"] += 1
                logger.info(f"Connected to platform: {platform_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to platform {platform_id}: {e}")
            return False
    
    async def disconnect_platform(self, platform_id: str) -> bool:
        """
        Disconnect from a platform.
        
        Args:
            platform_id: Platform ID
            
        Returns:
            Success status
        """
        try:
            if platform_id in self.adapters:
                adapter = self.adapters[platform_id]
                await adapter.disconnect()
                self.stats["platforms_connected"] -= 1
                logger.info(f"Disconnected from platform: {platform_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to disconnect from platform {platform_id}: {e}")
            return False
    
    async def get_messages(
        self,
        platform_ids: Optional[List[str]] = None,
        limit: int = 50,
        since: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get messages from platforms.
        
        Args:
            platform_ids: List of platform IDs (all if None)
            limit: Maximum number of messages per platform
            since: Get messages since this timestamp
            filters: Additional filters
            
        Returns:
            Dictionary of platform messages
        """
        try:
            if platform_ids is None:
                platform_ids = list(self.adapters.keys())
            
            messages = {}
            
            for platform_id in platform_ids:
                if platform_id in self.adapters:
                    adapter = self.adapters[platform_id]
                    platform_messages = await adapter.get_messages(limit, since, filters)
                    messages[platform_id] = platform_messages
                    self.stats["messages_processed"] += len(platform_messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return {}
    
    async def send_message(
        self,
        platform_id: str,
        content: str,
        recipient: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message via a platform.
        
        Args:
            platform_id: Platform ID
            content: Message content
            recipient: Message recipient
            message_type: Type of message
            metadata: Additional metadata
            
        Returns:
            Send result
        """
        try:
            if platform_id not in self.adapters:
                raise ValueError(f"Platform {platform_id} not found")
            
            adapter = self.adapters[platform_id]
            result = await adapter.send_message(content, recipient, message_type, metadata)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send message via platform {platform_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_platform_data(
        self,
        platform_id: str,
        data_types: List[str]
    ) -> Dict[str, Any]:
        """
        Sync data from a platform.
        
        Args:
            platform_id: Platform ID
            data_types: Types of data to sync
            
        Returns:
            Sync results
        """
        try:
            if platform_id not in self.adapters:
                raise ValueError(f"Platform {platform_id} not found")
            
            adapter = self.adapters[platform_id]
            results = await adapter.sync_data(data_types)
            
            self.stats["sync_operations"] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync data from platform {platform_id}: {e}")
            return {"error": str(e)}
    
    async def get_platform_status(self, platform_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get platform status.
        
        Args:
            platform_id: Platform ID (all if None)
            
        Returns:
            Platform status information
        """
        try:
            if platform_id:
                if platform_id not in self.adapters:
                    return {"error": f"Platform {platform_id} not found"}
                
                adapter = self.adapters[platform_id]
                return {
                    "platform_id": platform_id,
                    "name": self.platforms[platform_id].name,
                    "status": adapter.status.value,
                    "last_error": adapter.last_error,
                    "request_count": adapter.request_count
                }
            else:
                status = {}
                for platform_id, adapter in self.adapters.items():
                    status[platform_id] = {
                        "name": self.platforms[platform_id].name,
                        "status": adapter.status.value,
                        "last_error": adapter.last_error,
                        "request_count": adapter.request_count
                    }
                return status
                
        except Exception as e:
            logger.error(f"Failed to get platform status: {e}")
            return {"error": str(e)}
    
    async def start_oauth2_flow(self, platform_id: str) -> Dict[str, Any]:
        """
        Start OAuth2 authentication flow.
        
        Args:
            platform_id: Platform ID
            
        Returns:
            OAuth2 flow information
        """
        try:
            if platform_id not in self.platforms:
                raise ValueError(f"Platform {platform_id} not found")
            
            platform = self.platforms[platform_id]
            
            if not platform.oauth_config:
                raise ValueError(f"OAuth2 not configured for platform {platform_id}")
            
            # Generate state parameter
            state = secrets.token_urlsafe(32)
            
            # Store OAuth2 state
            self.oauth_states[state] = {
                "platform_id": platform_id,
                "timestamp": datetime.now(),
                "code_verifier": secrets.token_urlsafe(32)
            }
            
            # Build authorization URL
            auth_url = platform.oauth_config["auth_url"]
            
            params = {
                "client_id": platform.oauth_config["client_id"],
                "redirect_uri": platform.oauth_config["redirect_uri"],
                "response_type": "code",
                "state": state,
                "scope": " ".join(platform.oauth_config.get("scopes", []))
            }
            
            # Add PKCE if supported
            if platform.oauth_config.get("use_pkce", False):
                code_challenge = self._create_code_challenge(
                    self.oauth_states[state]["code_verifier"]
                )
                params["code_challenge"] = code_challenge
                params["code_challenge_method"] = "S256"
            
            authorization_url = f"{auth_url}?{urlencode(params)}"
            
            return {
                "authorization_url": authorization_url,
                "state": state,
                "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start OAuth2 flow for platform {platform_id}: {e}")
            return {"error": str(e)}
    
    async def complete_oauth2_flow(
        self,
        state: str,
        code: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete OAuth2 authentication flow.
        
        Args:
            state: OAuth2 state parameter
            code: Authorization code
            error: OAuth2 error (if any)
            
        Returns:
            Completion result
        """
        try:
            if error:
                raise ValueError(f"OAuth2 error: {error}")
            
            if state not in self.oauth_states:
                raise ValueError("Invalid or expired OAuth2 state")
            
            oauth_state = self.oauth_states[state]
            platform_id = oauth_state["platform_id"]
            
            # Check state expiry
            if datetime.now() - oauth_state["timestamp"] > timedelta(minutes=10):
                del self.oauth_states[state]
                raise ValueError("OAuth2 state expired")
            
            platform = self.platforms[platform_id]
            
            # Exchange code for tokens
            token_data = await self._exchange_oauth2_code(platform, code, oauth_state)
            
            # Store credentials
            credentials = PlatformCredentials(
                platform_id=platform_id,
                auth_type=AuthType.OAUTH2,
                client_id=platform.oauth_config["client_id"],
                client_secret=platform.oauth_config["client_secret"],
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600)),
                scopes=token_data.get("scope", "").split()
            )
            
            self.credentials[platform_id] = credentials
            
            # Save credentials
            await self._save_credentials()
            
            # Create adapter
            await self._create_adapter(platform_id)
            
            # Clean up state
            del self.oauth_states[state]
            
            return {
                "success": True,
                "platform_id": platform_id,
                "access_token": token_data["access_token"],
                "expires_at": credentials.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to complete OAuth2 flow: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Shutdown the platform manager."""
        try:
            # Disconnect all platforms
            for platform_id in list(self.adapters.keys()):
                await self.disconnect_platform(platform_id)
            
            logger.info("Platform manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during platform manager shutdown: {e}")
    
    # Private methods
    
    async def _load_platform_configs(self):
        """Load platform configurations from file."""
        try:
            if not self.config_path.exists():
                await self._create_default_config()
                return
            
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            for platform_data in config_data.get("platforms", []):
                platform = PlatformConfig.from_dict(platform_data)
                self.platforms[platform.id] = platform
            
            logger.info(f"Loaded {len(self.platforms)} platform configurations")
            
        except Exception as e:
            logger.error(f"Failed to load platform configurations: {e}")
    
    async def _load_credentials(self):
        """Load platform credentials from file."""
        try:
            if not self.credentials_path.exists():
                return
            
            with open(self.credentials_path, 'r') as f:
                credentials_data = json.load(f)
            
            for platform_id, cred_data in credentials_data.items():
                credentials = PlatformCredentials.from_dict(cred_data)
                self.credentials[platform_id] = credentials
            
            logger.info(f"Loaded credentials for {len(self.credentials)} platforms")
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
    
    async def _save_credentials(self):
        """Save platform credentials to file."""
        try:
            credentials_data = {}
            for platform_id, credentials in self.credentials.items():
                credentials_data[platform_id] = credentials.to_dict()
            
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.credentials_path, 'w') as f:
                json.dump(credentials_data, f, indent=2)
            
            logger.debug("Saved platform credentials")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    async def _create_default_config(self):
        """Create default platform configuration."""
        default_config = {
            "version": "1.0.0",
            "platforms": [
                {
                    "id": "gmail",
                    "name": "Gmail",
                    "platform_type": "email",
                    "auth_type": "oauth2",
                    "base_url": "https://gmail.googleapis.com",
                    "oauth_config": {
                        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                        "token_url": "https://oauth2.googleapis.com/token",
                        "client_id": "",
                        "client_secret": "",
                        "redirect_uri": "http://localhost:8080/auth/callback",
                        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
                    },
                    "enabled": False
                },
                {
                    "id": "slack",
                    "name": "Slack",
                    "platform_type": "chat",
                    "auth_type": "oauth2",
                    "base_url": "https://slack.com/api",
                    "oauth_config": {
                        "auth_url": "https://slack.com/oauth/v2/authorize",
                        "token_url": "https://slack.com/api/oauth.v2.access",
                        "client_id": "",
                        "client_secret": "",
                        "redirect_uri": "http://localhost:8080/auth/callback",
                        "scopes": ["channels:read", "channels:history", "chat:write"]
                    },
                    "enabled": False
                }
            ]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info("Created default platform configuration")
    
    async def _initialize_adapters(self):
        """Initialize platform adapters."""
        for platform_id in self.platforms:
            if platform_id in self.credentials:
                await self._create_adapter(platform_id)
    
    async def _create_adapter(self, platform_id: str):
        """Create platform adapter."""
        try:
            if platform_id not in self.platforms:
                raise ValueError(f"Platform {platform_id} not found")
            
            if platform_id not in self.credentials:
                raise ValueError(f"No credentials for platform {platform_id}")
            
            platform = self.platforms[platform_id]
            credentials = self.credentials[platform_id]
            
            adapter = PlatformAdapter(platform, credentials, self.privacy_filter)
            self.adapters[platform_id] = adapter
            
            logger.info(f"Created adapter for platform {platform_id}")
            
        except Exception as e:
            logger.error(f"Failed to create adapter for platform {platform_id}: {e}")
    
    async def _exchange_oauth2_code(
        self,
        platform: PlatformConfig,
        code: str,
        oauth_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exchange OAuth2 authorization code for tokens."""
        try:
            token_url = platform.oauth_config["token_url"]
            
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": platform.oauth_config["redirect_uri"],
                "client_id": platform.oauth_config["client_id"],
                "client_secret": platform.oauth_config["client_secret"]
            }
            
            # Add PKCE if used
            if platform.oauth_config.get("use_pkce", False):
                data["code_verifier"] = oauth_state["code_verifier"]
            
            timeout = ClientTimeout(total=30)
            async with ClientSession(timeout=timeout) as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_data = await response.text()
                        raise RuntimeError(f"Token exchange failed: {error_data}")
                        
        except Exception as e:
            logger.error(f"Failed to exchange OAuth2 code: {e}")
            raise
    
    def _create_code_challenge(self, code_verifier: str) -> str:
        """Create PKCE code challenge."""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')
    
    async def save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                "version": "1.0.0",
                "platforms": [platform.to_dict() for platform in self.platforms.values()]
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Saved platform configuration")
            
        except Exception as e:
            logger.error(f"Failed to save platform configuration: {e}")
    
    async def discover_platforms(self) -> List[Dict[str, Any]]:
        """
        Discover available platforms.
        
        Returns:
            List of discoverable platforms
        """
        # This would typically scan for installed apps, check common OAuth providers, etc.
        # For now, return a list of well-known platforms
        
        discoverable_platforms = [
            {
                "id": "gmail",
                "name": "Gmail",
                "platform_type": "email",
                "description": "Google Gmail email service",
                "auth_type": "oauth2",
                "setup_required": True
            },
            {
                "id": "outlook",
                "name": "Outlook",
                "platform_type": "email",
                "description": "Microsoft Outlook email service",
                "auth_type": "oauth2",
                "setup_required": True
            },
            {
                "id": "slack",
                "name": "Slack",
                "platform_type": "chat",
                "description": "Slack team communication",
                "auth_type": "oauth2",
                "setup_required": True
            },
            {
                "id": "discord",
                "name": "Discord",
                "platform_type": "chat",
                "description": "Discord voice and text chat",
                "auth_type": "oauth2",
                "setup_required": True
            },
            {
                "id": "telegram",
                "name": "Telegram",
                "platform_type": "chat",
                "description": "Telegram messaging app",
                "auth_type": "api_key",
                "setup_required": True
            }
        ]
        
        return discoverable_platforms
