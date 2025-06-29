"""
Web Application for Personal Chatbot System
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.config.settings import settings


# Pydantic models for API requests
class SetupRequest(BaseModel):
    features: List[str]
    platforms: List[str]
    actions: List[str]
    bot_mode: str

class ProcessingStatusUpdate(BaseModel):
    status: str
    progress: int
    message: str
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    status: str = "success"

# Global processing status
processing_status = {
    "active": False,
    "progress": 0,
    "message": "",
    "error": None,
    "results": None
}


def create_web_app():
    """Create the main web application"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Personal Chatbot System"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.web_ui.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files if directory exists
    static_dir = Path("src/ui/web/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def root():
        return {"message": "Personal Chatbot System", "version": settings.app_version}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "bot_type": "general"}
    
    return app


def create_personal_app():
    """Create the personal bot web application"""
    app = FastAPI(
        title=f"{settings.app_name} - Personal Bot",
        version=settings.app_version,
        description="Personal chatbot with full access to private data and tools"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files if directory exists
    static_dir = Path("src/ui/web/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def root():
        return {
            "message": "Personal Bot - Private Access",
            "version": settings.app_version,
            "bot_type": "personal"
        }
    
    @app.get("/setup", response_class=HTMLResponse)
    async def setup_wizard():
        """Serve the setup wizard page"""
        try:
            setup_file = Path("src/ui/web/setup_wizard.html")
            if setup_file.exists():
                return HTMLResponse(content=setup_file.read_text(), status_code=200)
            else:
                return HTMLResponse(content="<h1>Setup wizard not found</h1>", status_code=404)
        except Exception as e:
            return HTMLResponse(content=f"<h1>Error loading setup wizard: {e}</h1>", status_code=500)
    
    @app.get("/chat-interface", response_class=HTMLResponse)
    async def chat_interface():
        """Serve the chat interface page"""
        try:
            chat_file = Path("src/ui/web/chat_interface.html")
            if chat_file.exists():
                return HTMLResponse(content=chat_file.read_text(), status_code=200)
            else:
                return HTMLResponse(content="<h1>Chat interface not found</h1>", status_code=404)
        except Exception as e:
            return HTMLResponse(content=f"<h1>Error loading chat interface: {e}</h1>", status_code=500)
    
    @app.post("/api/setup/save-config")
    async def save_setup_config(setup: SetupRequest):
        """Save the setup configuration"""
        try:
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            config_data = {
                "features": setup.features,
                "platforms": setup.platforms,
                "actions": setup.actions,
                "bot_mode": setup.bot_mode,
                "timestamp": "now"
            }
            
            config_file = config_dir / "setup_config.json"
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            return {"status": "success", "message": "Configuration saved successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")
    
    @app.post("/api/setup/upload-credentials")
    async def upload_credentials(file: UploadFile = File(...), platform: str = Form(...)):
        """Upload and save credential files"""
        try:
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            # Save the uploaded file
            filename = f"{platform}_credentials.json"
            file_path = config_dir / filename
            
            content = await file.read()
            
            # Validate JSON format
            try:
                json.loads(content.decode('utf-8'))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format")
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return {"status": "success", "message": f"Credentials saved for {platform}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")
    
    @app.post("/api/setup/start-processing")
    async def start_file_processing(
        background_tasks: BackgroundTasks,
        folder_path: str = Form(None),
        files: List[UploadFile] = File(None)
    ):
        """Start the file processing pipeline"""
        global processing_status
        
        if processing_status["active"]:
            raise HTTPException(status_code=409, detail="Processing already in progress")
        
        # Reset processing status
        processing_status.update({
            "active": True,
            "progress": 0,
            "message": "Starting file processing...",
            "error": None,
            "results": None
        })
        
        # Start background processing
        background_tasks.add_task(process_files_background, folder_path, files)
        
        return {"status": "success", "message": "File processing started"}
    
    @app.get("/api/setup/processing-status")
    async def get_processing_status():
        """Get the current processing status"""
        return processing_status
    
    @app.get("/api/setup/database-results")
    async def get_database_results():
        """Get the vector database processing results"""
        try:
            results_file = Path("data/camel_processing_details.json")
            if results_file.exists():
                with open(results_file, 'r') as f:
                    results = json.load(f)
                return results
            else:
                # Return mock results if file doesn't exist
                return {
                    "databases": [
                        {
                            "name": "personal_documents",
                            "documents": 1247,
                            "size": "45.2 MB",
                            "types": ["PDF", "DOCX", "TXT"],
                            "languages": ["English"]
                        }
                    ]
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get database results: {str(e)}")
    
    @app.post("/api/setup/finalize")
    async def finalize_setup(bot_mode: str = Form(...)):
        """Finalize the setup and configure the bot"""
        try:
            # Save final configuration
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            final_config = {
                "bot_mode": bot_mode,
                "database_location": "./data/camel_vector_db/",
                "endpoints": {
                    "personal": f"http://localhost:{settings.web_ui.personal_bot_port}",
                    "public": f"http://localhost:{settings.web_ui.public_bot_port}"
                },
                "setup_completed": True,
                "timestamp": "now"
            }
            
            config_file = config_dir / "final_config.json"
            with open(config_file, 'w') as f:
                json.dump(final_config, f, indent=2)
            
            return {
                "status": "success",
                "message": "Setup completed successfully",
                "config": final_config
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to finalize setup: {str(e)}")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "bot_type": "personal"}
    
    # Initialize personal agent
    personal_agent = None
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize the personal agent on startup"""
        nonlocal personal_agent
        try:
            from src.core.agents.personal_agent import PersonalAgent
            personal_agent = PersonalAgent()
            print("✅ Personal agent initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize personal agent: {e}")
    
    @app.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(chat_request: ChatRequest):
        """Chat with the personal agent using vector database retrieval"""
        try:
            if not personal_agent:
                return ChatResponse(
                    response="Personal agent is not available. Please check the server configuration.",
                    status="error"
                )
            
            # Process the message through the personal agent
            response = await personal_agent.process_message(
                user_message=chat_request.message,
                conversation_id=chat_request.conversation_id
            )
            
            # Get information about what data was retrieved
            sources = []
            try:
                # Get recent retrieval info for transparency
                retrieval_info = personal_agent.retriever.get_database_info()
                if retrieval_info.get("status") == "connected":
                    sources.append({
                        "source": "vector_database",
                        "collections": [f"{col['name']} ({col['document_count']} docs)" 
                                      for col in retrieval_info.get("collections", [])]
                    })
            except:
                pass
            
            return ChatResponse(
                response=response,
                conversation_id=chat_request.conversation_id,
                sources=sources,
                status="success"
            )
            
        except Exception as e:
            return ChatResponse(
                response=f"I encountered an error processing your request: {str(e)}",
                status="error"
            )
    
    @app.get("/chat/database-info")
    async def get_database_info():
        """Get information about the vector database connection"""
        try:
            if personal_agent and personal_agent.retriever:
                return personal_agent.retriever.get_database_info()
            else:
                return {"status": "agent_not_initialized"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    return app


async def process_files_background(folder_path: Optional[str], files: Optional[List[UploadFile]]):
    """Background task to process files"""
    global processing_status
    
    try:
        # Update processing status
        processing_status.update({
            "progress": 10,
            "message": "Initializing file processor..."
        })
        
        # Import the actual file processing system
        try:
            import subprocess
            import sys
            import tempfile
        except ImportError as e:
            raise Exception(f"Required modules not available: {e}")
        
        processing_status.update({
            "progress": 20,
            "message": "Preparing data path..."
        })
        
        # Determine the data path to process
        data_path = None
        if folder_path and os.path.exists(folder_path):
            data_path = folder_path
        elif files:
            # Create a temporary directory and save uploaded files
            temp_dir = tempfile.mkdtemp(prefix="setup_wizard_")
            for file in files:
                if file.filename:
                    file_path = os.path.join(temp_dir, file.filename)
                    content = await file.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
            data_path = temp_dir
        else:
            raise Exception("No data path or files provided")
        
        processing_status.update({
            "progress": 30,
            "message": f"Processing data from: {data_path}"
        })
        
        # Call the actual file processor using the main.py script
        cmd = [
            sys.executable, "main.py", "parse-personal-data",
            "--data-path", data_path,
            "--output", "./data/setup_wizard_results.json",
            "--chunk-size", "1000",
            "--include-chat"
        ]
        
        processing_status.update({
            "progress": 40,
            "message": "Starting camel-ai file processor..."
        })
        
        # Run the file processor
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor the process and update status
        progress_steps = [
            "Discovering files...",
            "Analyzing file types...", 
            "Extracting text content...",
            "Generating embeddings...",
            "Creating vector database...",
            "Indexing documents...",
            "Finalizing setup..."
        ]
        
        # Simulate progress updates while process runs
        for i, step in enumerate(progress_steps):
            progress = 40 + int((i + 1) / len(progress_steps) * 50)
            processing_status.update({
                "progress": progress,
                "message": step
            })
            
            # Check if process is still running
            if process.poll() is not None:
                break
            
            await asyncio.sleep(3)
        
        # Wait for process completion
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"File processing failed: {stderr}")
        
        processing_status.update({
            "progress": 95,
            "message": "Loading processing results..."
        })
        
        # Load the actual results
        results_file = Path("data/setup_wizard_results.json")
        actual_results = {}
        if results_file.exists():
            with open(results_file, 'r') as f:
                actual_results = json.load(f)
        
        # Also try to load detailed results
        details_file = Path("data/camel_processing_details.json")
        detailed_results = {}
        if details_file.exists():
            with open(details_file, 'r') as f:
                detailed_results = json.load(f)
        
        processing_status.update({
            "active": False,
            "progress": 100,
            "message": "Processing completed successfully",
            "results": {
                "total_files": actual_results.get('file_processing', {}).get('stats', {}).get('total_files', 0),
                "processed_files": actual_results.get('file_processing', {}).get('stats', {}).get('processed_files', 0),
                "total_chunks": actual_results.get('file_processing', {}).get('stats', {}).get('total_chunks', 0),
                "collections_created": actual_results.get('file_processing', {}).get('collections_created', []),
                "database_location": "./data/camel_vector_db/",
                "processing_details": detailed_results
            }
        })
        
        # Clean up temporary directory if created
        if files and data_path and data_path.startswith(tempfile.gettempdir()):
            import shutil
            shutil.rmtree(data_path, ignore_errors=True)
        
    except Exception as e:
        processing_status.update({
            "active": False,
            "progress": 0,
            "message": "Processing failed",
            "error": str(e)
        })


def create_public_app():
    """Create the public bot web application"""
    app = FastAPI(
        title=f"{settings.app_name} - Public Bot",
        version=settings.app_version,
        description="Public chatbot with restricted access to public information only"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Public bot can accept requests from anywhere
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {
            "message": "Public Bot - General Access",
            "version": settings.app_version,
            "bot_type": "public"
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "bot_type": "public"}
    
    @app.post("/chat")
    async def chat_endpoint():
        # TODO: Implement actual chat functionality
        return {"response": "Public bot chat endpoint - implementation pending"}
    
    return app 