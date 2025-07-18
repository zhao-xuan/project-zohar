"""
Public Agent for Project Zohar.

This agent handles general queries and tasks without access to private user data.
It can be used for public-facing interactions and general information retrieval.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import RoleType, ModelType
from camel.models import ModelFactory

from config.settings import get_settings
from ..mcp.mcp_manager import MCPClient, MCPManager
from ..agent.logging import get_logger

logger = get_logger(__name__)


class PublicAgent:
    """
    Public Agent that handles general queries without access to private data.
    
    This agent can:
    - Answer general questions
    - Perform web searches
    - Execute public tools and APIs
    - Provide general assistance
    
    This agent cannot:
    - Access private user data
    - View personal files or messages
    - Store conversation history
    - Access user preferences
    """
    
    def __init__(
        self,
        agent_id: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize the Public Agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            model_name: LLM model to use (defaults to settings)
            temperature: Model temperature for generation
            max_tokens: Maximum tokens for generation
        """
        self.agent_id = agent_id
        self.settings = get_settings()
        
        # Initialize model
        self.model_name = model_name or self.settings.default_model
        self.model = self._initialize_model()
        
        # Initialize agent
        self.agent = ChatAgent(
            system_message=self._get_system_message(),
            model=self.model,
            message_window_size=5,  # Shorter window for public agent
        )
        
        # Initialize components
        self.mcp_client = None  # Will be initialized when needed
        self.mcp_manager = MCPManager()
        
        # Agent state
        self.is_active = False
        self.current_task = None
        self.session_context = {}  # Temporary session context only
        
        logger.info(f"Public agent initialized with ID {agent_id}")
    
    def _initialize_model(self):
        """Initialize the LLM model."""
        try:
            # Try to use Ollama first
            if self.settings.ollama_base_url:
                from camel.models import OllamaModel
                # Ensure the URL includes /v1 for OpenAI-compatible API
                ollama_url = self.settings.ollama_base_url
                if not ollama_url.endswith('/v1'):
                    ollama_url = ollama_url.rstrip('/') + '/v1'
                
                return OllamaModel(
                    model_type=self.model_name,
                    url=ollama_url,
                    model_config_dict={
                        "temperature": self.settings.temperature,
                        "max_tokens": self.settings.max_tokens,
                    }
                )
            else:
                # Fallback to OpenAI-compatible models
                return ModelFactory.create(
                    model_platform=ModelType.OPENAI,
                    model_type=self.model_name,
                    api_key=self.settings.openai_api_key,
                )
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def _get_system_message(self) -> BaseMessage:
        """Get the system message that defines the agent's role."""
        system_prompt = f"""
        You are a public AI assistant for Project Zohar. Your role is to:
        
        1. Provide helpful, accurate information on general topics
        2. Assist with public tasks and queries
        3. Use available tools for web search and information retrieval
        4. Help with general productivity and knowledge tasks
        5. Maintain a professional, helpful demeanor
        
        PRIVACY AND SECURITY:
        - You do NOT have access to any private user data
        - You cannot view personal files, emails, or messages
        - You cannot store conversation history beyond the current session
        - Always maintain user privacy and data security
        
        CAPABILITIES:
        - General knowledge and information
        - Web search and information retrieval
        - Public API access and tool usage
        - Code assistance and technical help
        - General productivity assistance
        
        LIMITATIONS:
        - No access to personal data or files
        - No long-term memory storage
        - Cannot perform actions that require private authentication
        - Cannot access local file systems or private databases
        
        INTERACTION STYLE:
        - Be helpful, professional, and informative
        - Provide accurate, up-to-date information
        - Ask clarifying questions when needed
        - Explain your limitations clearly
        - Offer alternative approaches when direct help isn't possible
        
        Current timestamp: {datetime.now().isoformat()}
        """
        
        return BaseMessage.make_assistant_message(
            role_name="Public Assistant",
            content=system_prompt,
        )
    
    async def start(self):
        """Start the public agent."""
        try:
            self.is_active = True
            await self.mcp_manager.start_public_servers()
            
            logger.info(f"Public agent started with ID {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to start public agent: {e}")
            raise
    
    async def stop(self):
        """Stop the public agent."""
        try:
            self.is_active = False
            await self.mcp_manager.stop_public_servers()
            
            # Clear session context
            self.session_context.clear()
            
            logger.info(f"Public agent stopped with ID {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop public agent: {e}")
            raise
    
    async def process_message(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a message from a user.
        
        Args:
            message: The user's message
            session_id: Optional session identifier for temporary context
            
        Returns:
            The agent's response
        """
        try:
            # Add session context if provided
            if session_id and session_id in self.session_context:
                context = self.session_context[session_id]
            else:
                context = {}
            
            # Prepare the message with context
            user_message = self._prepare_message_with_context(message, context)
            
            # Get response from agent
            response = await self.agent.step(user_message)
            
            # Process response for tool calls
            final_response = await self._process_response(response)
            
            # Update session context (temporary only)
            if session_id:
                self._update_session_context(session_id, message, final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def _prepare_message_with_context(self, message: str, context: Dict[str, Any]) -> BaseMessage:
        """Prepare the message with session context."""
        context_str = ""
        
        if context.get("recent_messages"):
            context_str += "\n\nRecent conversation:\n"
            for msg in context["recent_messages"][-3:]:  # Only last 3 messages
                context_str += f"User: {msg['user']}\n"
                context_str += f"Assistant: {msg['assistant']}\n"
        
        full_message = f"{context_str}\n\nUser query: {message}"
        
        return BaseMessage.make_user_message(
            role_name="User",
            content=full_message,
        )
    
    def _update_session_context(self, session_id: str, user_message: str, assistant_response: str):
        """Update temporary session context."""
        if session_id not in self.session_context:
            self.session_context[session_id] = {"recent_messages": []}
        
        # Add to recent messages
        self.session_context[session_id]["recent_messages"].append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 5 messages per session
        if len(self.session_context[session_id]["recent_messages"]) > 5:
            self.session_context[session_id]["recent_messages"] = \
                self.session_context[session_id]["recent_messages"][-5:]
    
    async def _process_response(self, response: BaseMessage) -> str:
        """Process the agent's response, handling tool calls if needed."""
        try:
            content = response.content
            
            # Check if response contains tool calls
            if self._has_tool_calls(content):
                # Execute tool calls
                tool_results = await self._execute_tool_calls(content)
                
                # Get final response with tool results
                final_response = await self._get_final_response_with_tools(content, tool_results)
                return final_response
            
            return content
            
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return content
    
    def _has_tool_calls(self, content: str) -> bool:
        """Check if the response contains tool calls."""
        # Simple check for tool call patterns
        tool_patterns = ["<tool_call>", "function_call", "mcp_call", "search_web", "get_weather"]
        return any(pattern in content.lower() for pattern in tool_patterns)
    
    async def _execute_tool_calls(self, content: str) -> Dict[str, Any]:
        """Execute tool calls found in the response."""
        tool_results = {}
        
        try:
            # Parse tool calls from content
            tool_calls = self._parse_tool_calls(content)
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                # Only execute public tools
                if self._is_public_tool(tool_name):
                    result = await self.mcp_client.call_tool(tool_name, **tool_args)
                    tool_results[tool_name] = result
                else:
                    tool_results[tool_name] = "Error: Tool not available for public use"
                
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            tool_results["error"] = str(e)
        
        return tool_results
    
    def _is_public_tool(self, tool_name: str) -> bool:
        """Check if a tool is available for public use."""
        # List of tools that are safe for public use
        public_tools = [
            "search_web",
            "get_weather",
            "get_news",
            "translate_text",
            "calculate",
            "get_time",
            "convert_currency",
            "get_stock_price",
            "search_wikipedia",
            "get_definition",
            "code_interpreter",
            "math_solver",
        ]
        
        return tool_name.lower() in public_tools
    
    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from response content."""
        tool_calls = []
        
        # Look for JSON-like tool calls
        import re
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def _get_final_response_with_tools(self, original_content: str, tool_results: Dict[str, Any]) -> str:
        """Get the final response incorporating tool results."""
        # Prepare tool results for the model
        tool_results_str = json.dumps(tool_results, indent=2)
        
        # Create a follow-up message with tool results
        follow_up_message = BaseMessage.make_user_message(
            role_name="System",
            content=f"Tool execution results:\n{tool_results_str}\n\nPlease provide a final response based on these results."
        )
        
        # Get final response
        final_response = await self.agent.step(follow_up_message)
        return final_response.content
    
    async def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            Search results
        """
        try:
            # Use MCP client to perform web search
            results = await self.mcp_client.call_tool(
                "search_web",
                query=query,
                num_results=num_results
            )
            
            return {
                "query": query,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {"error": str(e)}
    
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get weather information for a location.
        
        Args:
            location: Location name or coordinates
            
        Returns:
            Weather information
        """
        try:
            # Use MCP client to get weather
            weather_data = await self.mcp_client.call_tool(
                "get_weather",
                location=location
            )
            
            return {
                "location": location,
                "weather": weather_data,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return {"error": str(e)}
    
    async def get_news(self, category: str = "general", num_articles: int = 5) -> Dict[str, Any]:
        """
        Get latest news articles.
        
        Args:
            category: News category
            num_articles: Number of articles to return
            
        Returns:
            News articles
        """
        try:
            # Use MCP client to get news
            news_data = await self.mcp_client.call_tool(
                "get_news",
                category=category,
                num_articles=num_articles
            )
            
            return {
                "category": category,
                "articles": news_data,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error getting news: {e}")
            return {"error": str(e)}
    
    async def translate_text(self, text: str, target_language: str) -> Dict[str, Any]:
        """
        Translate text to a target language.
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Translation result
        """
        try:
            # Use MCP client to translate
            translation = await self.mcp_client.call_tool(
                "translate_text",
                text=text,
                target_language=target_language
            )
            
            return {
                "original_text": text,
                "target_language": target_language,
                "translated_text": translation,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the public agent."""
        return {
            "agent_id": self.agent_id,
            "is_active": self.is_active,
            "current_task": self.current_task,
            "model_name": self.model_name,
            "session_count": len(self.session_context),
            "public_servers_active": await self.mcp_manager.get_public_servers(),
        }
    
    async def clear_session(self, session_id: str):
        """Clear a specific session context."""
        if session_id in self.session_context:
            del self.session_context[session_id]
            logger.info(f"Cleared session {session_id}")
    
    async def clear_all_sessions(self):
        """Clear all session contexts."""
        self.session_context.clear()
        logger.info("Cleared all sessions")
    
    async def get_available_tools(self) -> List[str]:
        """Get list of available public tools."""
        try:
            public_tools = await self.mcp_manager.get_public_tools()
            return public_tools
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return []
    
    async def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool."""
        try:
            tool_info = await self.mcp_manager.get_tool_info(tool_name)
            return tool_info
        except Exception as e:
            logger.error(f"Error getting tool info: {e}")
            return {"error": str(e)}
