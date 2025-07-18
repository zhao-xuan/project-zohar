"""
Web Application for Project Zohar.

This module provides the web interface using FastAPI, including
chat interface, settings, and API endpoints.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

try:
    from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    FastAPI = None
    HTTPException = None
    uvicorn = None

from zohar.config.settings import get_settings
from zohar.utils.logging import get_logger
from zohar.core.agents.personal_agent import PersonalAgent
from zohar.core.agents.public_agent import PublicAgent
from zohar.core.orchestration.bot_manager import BotManager
from zohar.services.platform_integration.platform_manager import PlatformManager
from zohar.services.mcp_services.mcp_manager import MCPManager
from zohar.services.data_processing.processor import DataProcessor

logger = get_logger(__name__)

# Pydantic models for API
class ChatMessage(BaseModel):
    content: str
    user_id: str
    agent_type: str = "personal"
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None

class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]

class FileUpload(BaseModel):
    filename: str
    content: bytes
    content_type: str

class SystemStatus(BaseModel):
    status: str
    agents: Dict[str, Any]
    platforms: Dict[str, Any]
    mcp_services: Dict[str, Any]
    statistics: Dict[str, Any]


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket client."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user: {user_id}")
    
    def disconnect(self, user_id: str):
        """Disconnect a WebSocket client."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_personal_message(self, message: str, user_id: str):
        """Send message to specific user."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to user {user_id}: {e}")
                self.disconnect(user_id)


class ZoharWebApp:
    """Main web application class."""
    
    def __init__(self):
        """Initialize the web application."""
        if FastAPI is None:
            raise ImportError("FastAPI is required for web interface")
        
        self.settings = get_settings()
        self.app = FastAPI(
            title="Project Zohar",
            description="Privacy-focused AI Assistant",
            version="1.0.0"
        )
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize components
        self.bot_manager: Optional[BotManager] = None
        self.platform_manager: Optional[PlatformManager] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.data_processor: Optional[DataProcessor] = None
        
        # WebSocket connection manager
        self.connection_manager = ConnectionManager()
        
        # Security
        self.security = HTTPBearer()
        
        # Templates and static files
        self.templates_dir = Path(__file__).parent / "templates"
        self.static_dir = Path(__file__).parent / "static"
        
        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup templates
        self.templates = Jinja2Templates(directory=str(self.templates_dir))
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
        
        # Setup templates first (before routes that reference them)
        self.create_templates()
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Web application initialized")
    
    async def initialize(self) -> bool:
        """Initialize the web application components."""
        try:
            # Initialize bot manager (optional for basic web functionality)
            try:
                self.bot_manager = BotManager()
                if await self.bot_manager.initialize():
                    logger.info("Bot manager initialized successfully")
                else:
                    logger.warning("Bot manager initialization failed, continuing without it")
                    self.bot_manager = None
            except Exception as e:
                logger.warning(f"Bot manager initialization failed: {e}")
                self.bot_manager = None
            
            # Initialize platform manager (optional)
            try:
                self.platform_manager = PlatformManager()
                if await self.platform_manager.initialize():
                    logger.info("Platform manager initialized successfully")
                else:
                    logger.warning("Platform manager initialization failed, continuing without it")
                    self.platform_manager = None
            except Exception as e:
                logger.warning(f"Platform manager initialization failed: {e}")
                self.platform_manager = None
            
            # Initialize MCP manager (optional)
            try:
                self.mcp_manager = MCPManager()
                if await self.mcp_manager.initialize():
                    logger.info("MCP manager initialized successfully")
                else:
                    logger.warning("MCP manager initialization failed, continuing without it")
                    self.mcp_manager = None
            except Exception as e:
                logger.warning(f"MCP manager initialization failed: {e}")
                self.mcp_manager = None
            
            # Initialize data processor (optional)
            try:
                self.data_processor = DataProcessor("default_user")
                if await self.data_processor.initialize():
                    logger.info("Data processor initialized successfully")
                else:
                    logger.warning("Data processor initialization failed, continuing without it")
                    self.data_processor = None
            except Exception as e:
                logger.warning(f"Data processor initialization failed: {e}")
                self.data_processor = None
            
            logger.info("Web application components initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize web application: {e}")
            return True  # Continue anyway for basic web functionality
    
    def _setup_routes(self):
        """Setup all API routes."""
        
        # Main page
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Main chat interface."""
            # Return the inline HTML template for now
            return HTMLResponse(content=self.index_html)
        
        # Setup wizard page
        @self.app.get("/setup", response_class=HTMLResponse)
        async def setup_wizard():
            """Setup wizard interface."""
            return HTMLResponse(content=self.setup_wizard_html)
        
        # Chat API
        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat(message: ChatMessage):
            """Chat with AI agent."""
            try:
                if not self.bot_manager:
                    raise HTTPException(status_code=500, detail="Bot manager not initialized")
                
                # Get appropriate agent
                if message.agent_type == "personal":
                    agent = await self.bot_manager.get_personal_agent(message.user_id)
                else:
                    agent = await self.bot_manager.get_public_agent()
                
                # Process message
                response = await agent.process_message(message.content, message.context)
                
                # Send response via WebSocket if connected
                await self.connection_manager.send_personal_message(
                    json.dumps({
                        "type": "chat_response",
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    }),
                    message.user_id
                )
                
                return ChatResponse(
                    response=response,
                    agent_type=message.agent_type,
                    timestamp=datetime.now().isoformat(),
                    context=message.context
                )
                
            except Exception as e:
                logger.error(f"Chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System status
        @self.app.get("/api/status", response_model=SystemStatus)
        async def get_status():
            """Get system status."""
            try:
                status = {
                    "status": "running",
                    "agents": {},
                    "platforms": {},
                    "mcp_services": {},
                    "statistics": {}
                }
                
                if self.bot_manager:
                    status["agents"] = await self.bot_manager.get_all_agents()
                
                if self.platform_manager:
                    status["platforms"] = await self.platform_manager.get_platform_status()
                
                if self.mcp_manager:
                    status["mcp_services"] = await self.mcp_manager.get_service_status()
                
                if self.data_processor:
                    status["statistics"] = self.data_processor.get_processing_stats()
                
                return SystemStatus(**status)
                
            except Exception as e:
                logger.error(f"Status error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Settings
        @self.app.get("/api/settings")
        async def get_settings():
            """Get application settings."""
            try:
                return {
                    "llm_model": self.settings.default_model,
                    "embedding_model": self.settings.embedding_model,
                    "local_only": self.settings.local_only,
                    "max_tokens": self.settings.max_tokens,
                    "temperature": self.settings.temperature,
                    "debug": self.settings.debug,
                    "log_level": self.settings.log_level
                }
            except Exception as e:
                logger.error(f"Settings error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/settings")
        async def update_settings(settings: SettingsUpdate):
            """Update application settings."""
            try:
                # Update settings (in a real app, this would persist to config)
                logger.info(f"Settings updated: {settings.settings}")
                return {"success": True, "message": "Settings updated successfully"}
            except Exception as e:
                logger.error(f"Settings update error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # File upload
        @self.app.post("/api/upload")
        async def upload_file(file_data: FileUpload):
            """Upload and process file."""
            try:
                # Initialize data processor if not available
                if not self.data_processor:
                    try:
                        self.data_processor = DataProcessor("default_user")
                        await self.data_processor.initialize()
                        logger.info("Data processor initialized for file upload")
                    except Exception as init_error:
                        logger.error(f"Failed to initialize data processor: {init_error}")
                        return {"success": False, "error": "File processing not available"}
                
                # Save temporary file
                temp_path = Path(f"/tmp/{file_data.filename}")
                with open(temp_path, "wb") as f:
                    f.write(file_data.content)
                
                # Process file
                result = await self.data_processor.process_file(temp_path)
                
                # Cleanup
                temp_path.unlink()
                
                return {"success": True, "result": result}
                
            except Exception as e:
                logger.error(f"File upload error: {e}")
                return {"success": False, "error": str(e)}
        
        # Platform management
        @self.app.get("/api/platforms")
        async def get_platforms():
            """Get available platforms."""
            try:
                if not self.platform_manager:
                    raise HTTPException(status_code=500, detail="Platform manager not initialized")
                
                platforms = await self.platform_manager.discover_platforms()
                return {"platforms": platforms}
                
            except Exception as e:
                logger.error(f"Platforms error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/platforms/{platform_id}/connect")
        async def connect_platform(platform_id: str):
            """Connect to a platform."""
            try:
                if not self.platform_manager:
                    raise HTTPException(status_code=500, detail="Platform manager not initialized")
                
                success = await self.platform_manager.connect_platform(platform_id)
                
                if success:
                    return {"success": True, "message": f"Connected to {platform_id}"}
                else:
                    return {"success": False, "message": f"Failed to connect to {platform_id}"}
                    
            except Exception as e:
                logger.error(f"Platform connection error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # MCP services
        @self.app.get("/api/mcp/tools")
        async def get_mcp_tools():
            """Get available MCP tools."""
            try:
                if not self.mcp_manager:
                    raise HTTPException(status_code=500, detail="MCP manager not initialized")
                
                tools = await self.mcp_manager.list_tools()
                return {"tools": [tool.to_dict() for tool in tools]}
                
            except Exception as e:
                logger.error(f"MCP tools error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/mcp/tools/{tool_name}/call")
        async def call_mcp_tool(tool_name: str, parameters: Dict[str, Any]):
            """Call an MCP tool."""
            try:
                if not self.mcp_manager:
                    raise HTTPException(status_code=500, detail="MCP manager not initialized")
                
                result = await self.mcp_manager.call_tool(tool_name, parameters)
                return {"success": True, "result": result}
                
            except Exception as e:
                logger.error(f"MCP tool call error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket endpoint
        @self.app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str):
            """WebSocket endpoint for real-time communication."""
            await self.connection_manager.connect(websocket, user_id)
            try:
                while True:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    if message_data["type"] == "chat":
                        # Handle chat message
                        if self.bot_manager:
                            agent = await self.bot_manager.get_personal_agent(user_id)
                            response = await agent.process_message(
                                message_data["content"],
                                message_data.get("context")
                            )
                            
                            await websocket.send_text(json.dumps({
                                "type": "chat_response",
                                "response": response,
                                "timestamp": datetime.now().isoformat()
                            }))
                    
                    elif message_data["type"] == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
            except WebSocketDisconnect:
                self.connection_manager.disconnect(user_id)
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
                self.connection_manager.disconnect(user_id)
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # Favicon (prevent 404 errors)
        @self.app.get("/favicon.ico")
        async def favicon():
            """Return a simple favicon response."""
            return JSONResponse(content={"status": "no favicon"}, status_code=204)
        
        # Setup wizard API endpoints
        @self.app.get("/api/setup/requirements")
        async def get_setup_requirements():
            """Get system requirements for setup wizard."""
            try:
                requirements = await self.check_system_requirements()
                return {"success": True, "requirements": requirements}
            except Exception as e:
                logger.error(f"Setup requirements error: {e}")
                return {"success": False, "error": str(e)}
        
        @self.app.post("/api/setup/install")
        async def setup_install(config: Dict[str, Any]):
            """Install and configure Project Zohar."""
            try:
                result = await self.install_project_zohar(config)
                return {"success": result["success"], "error": result.get("error")}
            except Exception as e:
                logger.error(f"Setup installation error: {e}")
                return {"success": False, "error": str(e)}
        
        @self.app.post("/api/setup/finish")
        async def setup_finish(config: Dict[str, Any]):
            """Finish setup and save configuration."""
            try:
                result = await self.finish_setup(config)
                return {"success": result["success"], "error": result.get("error")}
            except Exception as e:
                logger.error(f"Setup finish error: {e}")
                return {"success": False, "error": str(e)}
        
        # Admin endpoints
        @self.app.get("/api/admin/logs")
        async def get_logs():
            """Get application logs."""
            try:
                log_file = self.settings.logs_dir / "main.log"
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        return {"logs": lines[-100:]}  # Return last 100 lines
                else:
                    return {"logs": []}
            except Exception as e:
                logger.error(f"Logs error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/admin/shutdown")
        async def shutdown():
            """Shutdown the application."""
            try:
                logger.info("Shutdown requested via API")
                
                # Cleanup components
                if self.bot_manager:
                    await self.bot_manager.shutdown()
                if self.platform_manager:
                    await self.platform_manager.shutdown()
                if self.mcp_manager:
                    await self.mcp_manager.shutdown()
                if self.data_processor:
                    await self.data_processor.close()
                
                return {"message": "Shutdown initiated"}
                
            except Exception as e:
                logger.error(f"Shutdown error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def create_templates(self):
        """Create HTML templates."""
        # Main chat interface
        self.index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Zohar - AI Assistant</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .chat-container {
            height: 500px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            background-color: #f9f9f9;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
        }
        .user-message {
            background-color: #007bff;
            color: white;
            text-align: right;
        }
        .assistant-message {
            background-color: #e9ecef;
            color: #333;
        }
        .sidebar {
            height: 100vh;
            overflow-y: auto;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        .status-connected { background-color: #28a745; }
        .status-disconnected { background-color: #dc3545; }
        .status-connecting { background-color: #ffc107; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 bg-light sidebar">
                <h4 class="p-3">Project Zohar</h4>
                
                <!-- Connection Status -->
                <div class="p-3">
                    <h6>System Status</h6>
                    <div id="connection-status">
                        <span class="status-indicator status-connecting"></span>
                        <span>Connecting...</span>
                    </div>
                </div>
                
                <!-- Settings -->
                <div class="p-3">
                    <h6>Settings</h6>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="agent" id="personal-agent" value="personal" checked>
                        <label class="form-check-label" for="personal-agent">Personal Agent</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="agent" id="public-agent" value="public">
                        <label class="form-check-label" for="public-agent">Public Agent</label>
                    </div>
                </div>
                
                <!-- File Upload -->
                <div class="p-3">
                    <h6>File Upload</h6>
                    <input type="file" id="file-upload" class="form-control" accept=".txt,.pdf,.docx,.csv,.json">
                    <button class="btn btn-sm btn-primary mt-2" onclick="uploadFile()">Upload</button>
                </div>
                
                <!-- Setup Wizard -->
                <div class="p-3">
                    <h6>Setup</h6>
                    <a href="/setup" class="btn btn-outline-primary btn-sm w-100 mb-2">
                        <i class="fas fa-cog"></i> Setup Wizard
                    </a>
                </div>
                
                <!-- Platform Status -->
                <div class="p-3">
                    <h6>Platforms</h6>
                    <div id="platform-status"></div>
                </div>
            </div>
            
            <!-- Main Chat Area -->
            <div class="col-md-9">
                <div class="p-3">
                    <h2>AI Assistant Chat</h2>
                    
                    <!-- Chat Messages -->
                    <div id="chat-container" class="chat-container mb-3"></div>
                    
                    <!-- Message Input -->
                    <div class="input-group">
                        <input type="text" id="message-input" class="form-control" placeholder="Type your message...">
                        <button class="btn btn-primary" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let websocket;
        let currentUserId = 'default_user';
        
        // Initialize WebSocket connection
        function initWebSocket() {
            websocket = new WebSocket(`ws://localhost:8000/ws/${currentUserId}`);
            
            websocket.onopen = function(event) {
                updateConnectionStatus('connected');
                console.log('WebSocket connected');
            };
            
            websocket.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };
            
            websocket.onclose = function(event) {
                updateConnectionStatus('disconnected');
                console.log('WebSocket disconnected');
                // Attempt to reconnect after 5 seconds
                setTimeout(initWebSocket, 5000);
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus('disconnected');
            };
        }
        
        function updateConnectionStatus(status) {
            const statusElement = document.getElementById('connection-status');
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('span:last-child');
            
            indicator.className = `status-indicator status-${status}`;
            
            switch(status) {
                case 'connected':
                    text.textContent = 'Connected';
                    break;
                case 'disconnected':
                    text.textContent = 'Disconnected';
                    break;
                case 'connecting':
                    text.textContent = 'Connecting...';
                    break;
            }
        }
        
        function handleWebSocketMessage(message) {
            if (message.type === 'chat_response') {
                addMessage(message.response, 'assistant');
            } else if (message.type === 'pong') {
                console.log('Pong received');
            }
        }
        
        function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (message && websocket && websocket.readyState === WebSocket.OPEN) {
                addMessage(message, 'user');
                
                const agentType = document.querySelector('input[name="agent"]:checked').value;
                
                websocket.send(JSON.stringify({
                    type: 'chat',
                    content: message,
                    agent_type: agentType
                }));
                
                input.value = '';
            }
        }
        
        function addMessage(text, sender) {
            const chatContainer = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            messageDiv.textContent = text;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function uploadFile() {
            const fileInput = document.getElementById('file-upload');
            const file = fileInput.files[0];
            
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const fileData = {
                        filename: file.name,
                        content: btoa(e.target.result),
                        content_type: file.type
                    };
                    
                    fetch('/api/upload', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(fileData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            addMessage(`File "${file.name}" uploaded successfully`, 'assistant');
                        } else {
                            addMessage(`Failed to upload file: ${data.error}`, 'assistant');
                        }
                    });
                };
                reader.readAsBinaryString(file);
            }
        }
        
        // Handle Enter key in message input
        document.getElementById('message-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Initialize WebSocket when page loads
        window.addEventListener('load', function() {
            initWebSocket();
            
            // Send ping every 30 seconds to keep connection alive
            setInterval(function() {
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({type: 'ping'}));
                }
            }, 30000);
        });
    </script>
</body>
</html>
        """
        
        # Save template
        template_path = self.templates_dir / "index.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(self.index_html)
        
        # Create setup wizard template
        self.create_setup_wizard_template()
        
        logger.info("Created HTML templates")
    
    def create_setup_wizard_template(self):
        """Create the setup wizard HTML template."""
        self.setup_wizard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Zohar Setup Wizard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .setup-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .setup-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }
        .setup-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .setup-header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .setup-header p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin: 0;
        }
        .setup-content {
            padding: 40px;
        }
        .progress-container {
            margin-bottom: 40px;
        }
        .progress {
            height: 8px;
            border-radius: 10px;
            background-color: #e9ecef;
        }
        .progress-bar {
            border-radius: 10px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.6s ease;
        }
        .step {
            display: none;
            animation: fadeIn 0.5s ease-in;
        }
        .step.active {
            display: block;
        }
        .step-header {
            display: flex;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }
        .step-number {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2rem;
            margin-right: 20px;
        }
        .step-title {
            font-size: 1.8rem;
            font-weight: 600;
            margin: 0;
            color: #2c3e50;
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-label {
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            font-size: 1.1rem;
        }
        .form-control, .form-select {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            padding: 12px 16px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        .form-control:focus, .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            font-size: 1.1rem;
            transition: transform 0.2s ease;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        .btn-secondary {
            background: #6c757d;
            border: none;
            border-radius: 10px;
            padding: 12px 30px;
            font-weight: 600;
            font-size: 1.1rem;
        }
        .navigation-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }
        .status-indicator {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            display: inline-block;
        }
        .status-success {
            background: #d4edda;
            color: #155724;
        }
        .status-warning {
            background: #fff3cd;
            color: #856404;
        }
        .status-error {
            background: #f8d7da;
            color: #721c24;
        }
        .requirement-item {
            display: flex;
            align-items: center;
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .requirement-icon {
            margin-right: 15px;
            font-size: 1.2rem;
        }
        .requirement-text {
            flex: 1;
        }
        .requirement-status {
            font-weight: 600;
        }
        .config-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .config-section h5 {
            color: #495057;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .alert {
            border-radius: 10px;
            border: none;
            padding: 15px 20px;
        }
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
        }
        .alert-warning {
            background: #fff3cd;
            color: #856404;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .spinner-border {
            width: 1.5rem;
            height: 1.5rem;
        }
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .loading-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="setup-container">
        <div class="setup-card">
            <div class="setup-header">
                <h1><i class="fas fa-robot"></i> Project Zohar</h1>
                <p>Privacy-focused AI Assistant Setup</p>
            </div>
            
            <div class="setup-content">
                <div class="progress-container">
                    <div class="progress">
                        <div class="progress-bar" id="progress-bar" style="width: 14%"></div>
                    </div>
                    <div class="mt-2 text-center">
                        <span id="progress-text">Step 1 of 7</span>
                    </div>
                </div>
                
                <!-- Step 1: Welcome -->
                <div class="step active" id="step-1">
                    <div class="step-header">
                        <div class="step-number">1</div>
                        <h2 class="step-title">Welcome</h2>
                    </div>
                    <div class="text-center">
                        <h4>Welcome to Project Zohar Setup!</h4>
                        <p class="lead">This wizard will help you configure your privacy-focused AI assistant.</p>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i>
                            <strong>What we'll configure:</strong><br>
                            • System requirements and dependencies<br>
                            • LLM provider (Ollama recommended)<br>
                            • Privacy and security settings<br>
                            • Platform integrations<br>
                            • Tool services (MCP servers)
                        </div>
                    </div>
                </div>
                
                <!-- Step 2: System Requirements -->
                <div class="step" id="step-2">
                    <div class="step-header">
                        <div class="step-number">2</div>
                        <h2 class="step-title">System Requirements</h2>
                    </div>
                    <div id="requirements-content">
                        <p>Checking your system requirements...</p>
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Step 3: LLM Configuration -->
                <div class="step" id="step-3">
                    <div class="step-header">
                        <div class="step-number">3</div>
                        <h2 class="step-title">LLM Configuration</h2>
                    </div>
                    <div class="config-section">
                        <h5>Choose Your LLM Provider</h5>
                        <div class="form-group">
                            <label class="form-label">Provider</label>
                            <select class="form-select" id="llm-provider">
                                <option value="ollama">Ollama (Recommended - Local)</option>
                                <option value="openai">OpenAI</option>
                                <option value="anthropic">Anthropic Claude</option>
                                <option value="custom">Custom Provider</option>
                            </select>
                        </div>
                        
                        <div id="ollama-config" class="provider-config">
                            <div class="form-group">
                                <label class="form-label">Base URL</label>
                                <input type="text" class="form-control" id="ollama-url" value="http://localhost:11434">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Model</label>
                                <select class="form-select" id="ollama-model">
                                    <option value="llama3.2">Llama 3.2 (Recommended)</option>
                                    <option value="llama3.1">Llama 3.1</option>
                                    <option value="mistral">Mistral</option>
                                    <option value="codellama">Code Llama</option>
                                    <option value="custom">Custom Model</option>
                                </select>
                            </div>
                        </div>
                        
                        <div id="openai-config" class="provider-config" style="display: none;">
                            <div class="form-group">
                                <label class="form-label">API Key</label>
                                <input type="password" class="form-control" id="openai-key" placeholder="Enter your OpenAI API key">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Model</label>
                                <select class="form-select" id="openai-model">
                                    <option value="gpt-4">GPT-4</option>
                                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                </select>
                            </div>
                        </div>
                        
                        <div id="anthropic-config" class="provider-config" style="display: none;">
                            <div class="form-group">
                                <label class="form-label">API Key</label>
                                <input type="password" class="form-control" id="anthropic-key" placeholder="Enter your Anthropic API key">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Model</label>
                                <select class="form-select" id="anthropic-model">
                                    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                                    <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                                    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                                </select>
                            </div>
                        </div>
                        
                        <div id="custom-config" class="provider-config" style="display: none;">
                            <div class="form-group">
                                <label class="form-label">Base URL</label>
                                <input type="text" class="form-control" id="custom-url" placeholder="https://api.example.com/v1">
                            </div>
                            <div class="form-group">
                                <label class="form-label">API Key (Optional)</label>
                                <input type="password" class="form-control" id="custom-key" placeholder="Enter API key if required">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Model Name</label>
                                <input type="text" class="form-control" id="custom-model" placeholder="model-name">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Step 4: Privacy Settings -->
                <div class="step" id="step-4">
                    <div class="step-header">
                        <div class="step-number">4</div>
                        <h2 class="step-title">Privacy Settings</h2>
                    </div>
                    <div class="config-section">
                        <h5>Privacy Level</h5>
                        <div class="form-group">
                            <select class="form-select" id="privacy-level">
                                <option value="maximum">Maximum - No external connections</option>
                                <option value="high" selected>High - Local processing with minimal external access</option>
                                <option value="medium">Medium - Balanced privacy and functionality</option>
                                <option value="low">Low - Full external service access</option>
                            </select>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="local-only" checked>
                            <label class="form-check-label" for="local-only">
                                <strong>Local-only mode</strong> - No data sent to external services
                            </label>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="anonymize-data" checked>
                            <label class="form-check-label" for="anonymize-data">
                                <strong>Anonymize data</strong> - Remove personal information from logs
                            </label>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Data Retention (days)</label>
                            <input type="number" class="form-control" id="data-retention" value="365" min="1" max="3650">
                        </div>
                    </div>
                </div>
                
                <!-- Step 5: Platform Integrations -->
                <div class="step" id="step-5">
                    <div class="step-header">
                        <div class="step-number">5</div>
                        <h2 class="step-title">Platform Integrations</h2>
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        Platform integrations allow Project Zohar to connect with your email, messaging apps, and other services.
                        You can skip this step and configure platforms later.
                    </div>
                    
                    <div class="config-section">
                        <h5>Email Integration</h5>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enable-gmail">
                            <label class="form-check-label" for="enable-gmail">Gmail</label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enable-outlook">
                            <label class="form-check-label" for="enable-outlook">Outlook</label>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <h5>Messaging Integration</h5>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enable-slack">
                            <label class="form-check-label" for="enable-slack">Slack</label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enable-discord">
                            <label class="form-check-label" for="enable-discord">Discord</label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="enable-telegram">
                            <label class="form-check-label" for="enable-telegram">Telegram</label>
                        </div>
                    </div>
                </div>
                
                <!-- Step 6: Tool Services -->
                <div class="step" id="step-6">
                    <div class="step-header">
                        <div class="step-number">6</div>
                        <h2 class="step-title">Tool Services</h2>
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-tools"></i>
                        Tool services (MCP servers) give your AI assistant access to various tools and capabilities.
                    </div>
                    
                    <div class="config-section">
                        <h5>Core Tools</h5>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-filesystem" checked>
                            <label class="form-check-label" for="tool-filesystem">
                                <strong>Filesystem</strong> - File operations and management
                            </label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-git">
                            <label class="form-check-label" for="tool-git">
                                <strong>Git</strong> - Version control operations
                            </label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-sqlite">
                            <label class="form-check-label" for="tool-sqlite">
                                <strong>SQLite</strong> - Database operations
                            </label>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <h5>External Services</h5>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-search">
                            <label class="form-check-label" for="tool-search">
                                <strong>Web Search</strong> - Search the internet
                            </label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-weather">
                            <label class="form-check-label" for="tool-weather">
                                <strong>Weather</strong> - Weather information
                            </label>
                        </div>
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" id="tool-calendar">
                            <label class="form-check-label" for="tool-calendar">
                                <strong>Calendar</strong> - Calendar management
                            </label>
                        </div>
                    </div>
                </div>
                
                <!-- Step 7: Installation -->
                <div class="step" id="step-7">
                    <div class="step-header">
                        <div class="step-number">7</div>
                        <h2 class="step-title">Installation</h2>
                    </div>
                    <div id="installation-content">
                        <p>Installing dependencies and configuring your system...</p>
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Navigation -->
                <div class="navigation-buttons">
                    <button type="button" class="btn btn-secondary" id="prev-btn" onclick="previousStep()" disabled>
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    <button type="button" class="btn btn-primary" id="next-btn" onclick="nextStep()">
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loading-overlay" style="display: none;">
        <div class="loading-content">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <h5 id="loading-message">Processing...</h5>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentStep = 1;
        const totalSteps = 7;
        
        function showStep(step) {
            // Hide all steps
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            
            // Show current step
            document.getElementById(`step-${step}`).classList.add('active');
            
            // Update progress
            const progress = (step / totalSteps) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('progress-text').textContent = `Step ${step} of ${totalSteps}`;
            
            // Update navigation buttons
            document.getElementById('prev-btn').disabled = step === 1;
            const nextBtn = document.getElementById('next-btn');
            
            if (step === totalSteps) {
                nextBtn.innerHTML = 'Finish <i class="fas fa-check"></i>';
                nextBtn.onclick = finishSetup;
            } else {
                nextBtn.innerHTML = 'Next <i class="fas fa-chevron-right"></i>';
                nextBtn.onclick = nextStep;
            }
        }
        
        function nextStep() {
            if (currentStep < totalSteps) {
                // Validate current step
                if (validateStep(currentStep)) {
                    currentStep++;
                    showStep(currentStep);
                    
                    // Load step content
                    loadStepContent(currentStep);
                }
            }
        }
        
        function previousStep() {
            if (currentStep > 1) {
                currentStep--;
                showStep(currentStep);
            }
        }
        
        function validateStep(step) {
            switch (step) {
                case 3: // LLM Configuration
                    const provider = document.getElementById('llm-provider').value;
                    if (provider === 'openai' && !document.getElementById('openai-key').value) {
                        alert('Please enter your OpenAI API key');
                        return false;
                    }
                    if (provider === 'anthropic' && !document.getElementById('anthropic-key').value) {
                        alert('Please enter your Anthropic API key');
                        return false;
                    }
                    break;
                case 4: // Privacy Settings
                    const retention = document.getElementById('data-retention').value;
                    if (!retention || retention < 1) {
                        alert('Please enter a valid data retention period');
                        return false;
                    }
                    break;
            }
            return true;
        }
        
        function loadStepContent(step) {
            switch (step) {
                case 2:
                    loadSystemRequirements();
                    break;
                case 7:
                    startInstallation();
                    break;
            }
        }
        
        function loadSystemRequirements() {
            fetch('/api/setup/requirements')
                .then(response => response.json())
                .then(data => {
                    const content = document.getElementById('requirements-content');
                    content.innerHTML = '';
                    
                    data.requirements.forEach(req => {
                        const item = document.createElement('div');
                        item.className = 'requirement-item';
                        
                        const statusClass = req.status === 'ok' ? 'text-success' : 
                                          req.status === 'warning' ? 'text-warning' : 'text-danger';
                        const icon = req.status === 'ok' ? 'fa-check-circle' : 
                                   req.status === 'warning' ? 'fa-exclamation-triangle' : 'fa-times-circle';
                        
                        item.innerHTML = `
                            <div class="requirement-icon ${statusClass}">
                                <i class="fas ${icon}"></i>
                            </div>
                            <div class="requirement-text">
                                <strong>${req.name}</strong><br>
                                ${req.description}
                            </div>
                            <div class="requirement-status ${statusClass}">
                                ${req.status.toUpperCase()}
                            </div>
                        `;
                        
                        content.appendChild(item);
                    });
                })
                .catch(error => {
                    console.error('Error loading requirements:', error);
                    document.getElementById('requirements-content').innerHTML = 
                        '<div class="alert alert-danger">Failed to load system requirements</div>';
                });
        }
        
        function startInstallation() {
            const config = collectConfiguration();
            
            fetch('/api/setup/install', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('installation-content');
                
                if (data.success) {
                    content.innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-check-circle text-success" style="font-size: 4rem;"></i>
                            <h3 class="mt-3 text-success">Installation Complete!</h3>
                            <p class="lead">Project Zohar has been successfully configured.</p>
                            <div class="alert alert-success">
                                <strong>Next Steps:</strong><br>
                                • Start using the chat interface<br>
                                • Configure additional platforms<br>
                                • Upload documents for processing
                            </div>
                            <button class="btn btn-primary" onclick="goToChat()">
                                Go to Chat Interface <i class="fas fa-comments"></i>
                            </button>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div class="alert alert-danger">
                            <h5>Installation Failed</h5>
                            <p>${data.error}</p>
                            <button class="btn btn-warning" onclick="retryInstallation()">
                                Retry Installation
                            </button>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Installation error:', error);
                document.getElementById('installation-content').innerHTML = 
                    '<div class="alert alert-danger">Installation failed. Please try again.</div>';
            });
        }
        
        function collectConfiguration() {
            const config = {
                llm: {
                    provider: document.getElementById('llm-provider').value,
                    model: '',
                    base_url: '',
                    api_key: ''
                },
                privacy: {
                    level: document.getElementById('privacy-level').value,
                    local_only: document.getElementById('local-only').checked,
                    anonymize_data: document.getElementById('anonymize-data').checked,
                    data_retention: parseInt(document.getElementById('data-retention').value)
                },
                platforms: {
                    enabled: []
                },
                tools: {
                    enabled: []
                }
            };
            
            // LLM configuration
            const provider = config.llm.provider;
            switch (provider) {
                case 'ollama':
                    config.llm.base_url = document.getElementById('ollama-url').value;
                    config.llm.model = document.getElementById('ollama-model').value;
                    break;
                case 'openai':
                    config.llm.api_key = document.getElementById('openai-key').value;
                    config.llm.model = document.getElementById('openai-model').value;
                    config.llm.base_url = 'https://api.openai.com/v1';
                    break;
                case 'anthropic':
                    config.llm.api_key = document.getElementById('anthropic-key').value;
                    config.llm.model = document.getElementById('anthropic-model').value;
                    config.llm.base_url = 'https://api.anthropic.com';
                    break;
                case 'custom':
                    config.llm.base_url = document.getElementById('custom-url').value;
                    config.llm.api_key = document.getElementById('custom-key').value;
                    config.llm.model = document.getElementById('custom-model').value;
                    break;
            }
            
            // Platform configuration
            const platforms = ['gmail', 'outlook', 'slack', 'discord', 'telegram'];
            platforms.forEach(platform => {
                if (document.getElementById(`enable-${platform}`).checked) {
                    config.platforms.enabled.push(platform);
                }
            });
            
            // Tool configuration
            const tools = ['filesystem', 'git', 'sqlite', 'search', 'weather', 'calendar'];
            tools.forEach(tool => {
                if (document.getElementById(`tool-${tool}`).checked) {
                    config.tools.enabled.push(tool);
                }
            });
            
            return config;
        }
        
        function finishSetup() {
            if (currentStep === totalSteps) {
                const config = collectConfiguration();
                
                fetch('/api/setup/finish', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(config)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        goToChat();
                    } else {
                        alert('Setup completion failed: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Setup completion error:', error);
                    alert('Setup completion failed. Please try again.');
                });
            }
        }
        
        function goToChat() {
            window.location.href = '/';
        }
        
        function retryInstallation() {
            document.getElementById('installation-content').innerHTML = `
                <p>Retrying installation...</p>
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            startInstallation();
        }
        
        // LLM provider change handler
        document.getElementById('llm-provider').addEventListener('change', function() {
            const provider = this.value;
            
            // Hide all provider configs
            document.querySelectorAll('.provider-config').forEach(config => {
                config.style.display = 'none';
            });
            
            // Show selected provider config
            document.getElementById(`${provider}-config`).style.display = 'block';
        });
        
        // Initialize
        showStep(1);
    </script>
</body>
</html>
        """
        
        # Save setup wizard template
        setup_template_path = self.templates_dir / "setup_wizard.html"
        with open(setup_template_path, 'w', encoding='utf-8') as f:
            f.write(self.setup_wizard_html)
    
    async def check_system_requirements(self) -> List[Dict[str, Any]]:
        """Check system requirements for setup wizard."""
        requirements = []
        
        # Check Python version
        import sys
        python_version = sys.version_info
        requirements.append({
            "name": "Python Version",
            "description": f"Python {python_version.major}.{python_version.minor}.{python_version.micro}",
            "status": "ok" if python_version >= (3, 10) else "error"
        })
        
        # Check disk space
        import shutil
        try:
            disk_usage = shutil.disk_usage(self.settings.data_dir)
            free_gb = disk_usage.free / (1024**3)
            requirements.append({
                "name": "Disk Space",
                "description": f"{free_gb:.1f}GB available",
                "status": "ok" if free_gb >= 5.0 else "warning"
            })
        except Exception:
            requirements.append({
                "name": "Disk Space",
                "description": "Could not check disk space",
                "status": "warning"
            })
        
        # Check Ollama installation
        if shutil.which("ollama"):
            requirements.append({
                "name": "Ollama",
                "description": "Ollama is installed",
                "status": "ok"
            })
        else:
            requirements.append({
                "name": "Ollama",
                "description": "Ollama not found - download from https://ollama.ai",
                "status": "warning"
            })
        
        # Check Git installation
        if shutil.which("git"):
            requirements.append({
                "name": "Git",
                "description": "Git is installed",
                "status": "ok"
            })
        else:
            requirements.append({
                "name": "Git",
                "description": "Git not found - optional for version control",
                "status": "warning"
            })
        
        # Check dependencies
        try:
            import fastapi
            requirements.append({
                "name": "FastAPI",
                "description": "FastAPI is installed",
                "status": "ok"
            })
        except ImportError:
            requirements.append({
                "name": "FastAPI",
                "description": "FastAPI not installed",
                "status": "error"
            })
        
        try:
            import uvicorn
            requirements.append({
                "name": "Uvicorn",
                "description": "Uvicorn is installed",
                "status": "ok"
            })
        except ImportError:
            requirements.append({
                "name": "Uvicorn",
                "description": "Uvicorn not installed",
                "status": "error"
            })
        
        return requirements
    
    async def install_project_zohar(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Install and configure Project Zohar."""
        try:
            # Create directories
            self.settings.data_dir.mkdir(parents=True, exist_ok=True)
            self.settings.logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Save basic configuration
            config_path = self.settings.data_dir / "setup_config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Create environment file
            env_file = Path("config.env")
            with open(env_file, 'w') as f:
                f.write("# Project Zohar Configuration\n")
                f.write(f"LLM_PROVIDER={config['llm']['provider']}\n")
                f.write(f"LLM_MODEL_NAME={config['llm']['model']}\n")
                f.write(f"LLM_BASE_URL={config['llm']['base_url']}\n")
                
                if config['llm'].get('api_key'):
                    f.write(f"LLM_API_KEY={config['llm']['api_key']}\n")
                
                f.write(f"PRIVACY_LEVEL={config['privacy']['level']}\n")
                f.write(f"LOCAL_ONLY={config['privacy']['local_only']}\n")
                f.write(f"ANONYMIZE_DATA={config['privacy']['anonymize_data']}\n")
                f.write(f"DATA_RETENTION_DAYS={config['privacy']['data_retention']}\n")
            
            # Test LLM connection if Ollama
            if config['llm']['provider'] == 'ollama':
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{config['llm']['base_url']}/api/tags", 
                                             timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status != 200:
                                return {"success": False, "error": "Could not connect to Ollama"}
                except Exception as e:
                    return {"success": False, "error": f"Ollama connection failed: {e}"}
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def finish_setup(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Finish setup and save final configuration."""
        try:
            # Save final configuration
            config_path = self.settings.data_dir / "final_config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Create platform configuration if needed
            if config['platforms']['enabled']:
                platform_config = {
                    "version": "1.0.0",
                    "platforms": []
                }
                
                for platform in config['platforms']['enabled']:
                    platform_config["platforms"].append({
                        "id": platform,
                        "name": platform.title(),
                        "enabled": True,
                        "configured": False
                    })
                
                platform_path = self.settings.data_dir / "platforms.json"
                with open(platform_path, 'w') as f:
                    json.dump(platform_config, f, indent=2)
            
            # Create MCP server configuration
            if config['tools']['enabled']:
                mcp_config = {
                    "version": "1.0.0",
                    "services": []
                }
                
                for tool in config['tools']['enabled']:
                    mcp_config["services"].append({
                        "id": tool,
                        "name": tool.title(),
                        "description": f"{tool.title()} MCP server",
                        "connection_type": "subprocess",
                        "endpoint": "",
                        "command": f"mcp-server-{tool}",
                        "args": [],
                        "auto_start": True
                    })
                
                mcp_path = self.settings.data_dir / "mcp_services.json"
                with open(mcp_path, 'w') as f:
                    json.dump(mcp_config, f, indent=2)
            
            # Mark setup as completed
            setup_marker = self.settings.data_dir / ".setup_completed"
            with open(setup_marker, 'w') as f:
                f.write(f"Setup completed at {datetime.now().isoformat()}\n")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Setup completion failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def run(self, host: str = "localhost", port: int = 8000):
        """Run the web application."""
        try:
            # Create templates
            self.create_templates()
            
            # Initialize components
            if not await self.initialize():
                logger.error("Failed to initialize web application")
                return
            
            # Run server
            logger.info(f"Starting web server at http://{host}:{port}")
            
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to run web application: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the web application."""
        try:
            if self.bot_manager:
                await self.bot_manager.shutdown()
            if self.platform_manager:
                await self.platform_manager.shutdown()
            if self.mcp_manager:
                await self.mcp_manager.shutdown()
            if self.data_processor:
                await self.data_processor.close()
            
            logger.info("Web application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during web application shutdown: {e}")


# Factory function for uvicorn
def create_app():
    """Create and return the FastAPI application for uvicorn."""
    try:
        web_app = ZoharWebApp()
        web_app.create_templates()
        return web_app.app
    except Exception as e:
        logger.error(f"Failed to create app: {e}")
        raise


# Main function
async def main():
    """Main function to run the web application."""
    app = ZoharWebApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main()) 