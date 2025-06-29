"""
Web Application for Personal Chatbot System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings


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
    
    @app.get("/")
    async def root():
        return {
            "message": "Personal Bot - Private Access",
            "version": settings.app_version,
            "bot_type": "personal"
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "bot_type": "personal"}
    
    @app.post("/chat")
    async def chat_endpoint():
        # TODO: Implement actual chat functionality
        return {"response": "Personal bot chat endpoint - implementation pending"}
    
    return app


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