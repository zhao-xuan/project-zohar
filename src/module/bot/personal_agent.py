"""
Personal Agent for Project Zohar.

This agent handles personal tasks and has access to the user's private data.
It can process emails, messages, and personal documents while maintaining privacy.
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
from ..chat_analyser.conversation_memory import ConversationMemory
from ..file_parser.vector_store import VectorStore
from ..mcp.mcp_manager import MCPClient, MCPManager
from ..agent.privacy_filter import PrivacyFilter
from ..agent.camel_tool_manager import CamelToolManager, ToolEnabledAgent
from ..agent.logging import get_logger

logger = get_logger(__name__)


class PersonalAgent:
    """
    Personal Agent that handles private user data and tasks.
    
    This agent has access to:
    - User's personal data (emails, messages, documents)
    - Private conversation history
    - Personal preferences and settings
    - Local file system and databases
    """
    
    def __init__(
        self,
        user_id: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize the Personal Agent.
        
        Args:
            user_id: Unique identifier for the user
            model_name: LLM model to use (defaults to settings)
            temperature: Model temperature for generation
            max_tokens: Maximum tokens for generation
        """
        self.user_id = user_id
        self.settings = get_settings()
        
        # Initialize model
        self.model_name = model_name or self.settings.default_model
        self.model = self._initialize_model()
        
        # Initialize agent
        self.agent = ChatAgent(
            system_message=self._get_system_message(),
            model=self.model,
            message_window_size=10,
        )
        
        # Initialize components
        self.memory = ConversationMemory(user_id=user_id)
        self.vector_store = VectorStore(user_id=user_id)
        self.mcp_client = None  # Will be initialized when needed
        self.mcp_manager = MCPManager()
        self.privacy_filter = PrivacyFilter()
        
        # Initialize CAMEL AI tool manager
        self.tool_manager = CamelToolManager()
        self.tool_enabled_agent = None
        
        # Agent state
        self.is_active = False
        self.current_task = None
        self.context = {}
        
        logger.info(f"Personal agent initialized for user {user_id}")
    
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
        You are a personal AI assistant for a user with ID {self.user_id}. Your role is to:
        
        1. Help with personal tasks and queries
        2. Process and analyze personal data (emails, messages, documents)
        3. Maintain strict privacy and confidentiality
        4. Use available tools to complete tasks
        5. Provide personalized recommendations and insights
        
        PRIVACY GUIDELINES:
        - All user data is private and confidential
        - Never share personal information with external services
        - Use local processing whenever possible
        - Anonymize data when necessary for external queries
        
        CAPABILITIES:
        - Access to user's personal data and documents
        - Email and message processing
        - File analysis and organization
        - Calendar and task management
        - Web search and information retrieval
        - Various productivity tools via MCP servers
        
        INTERACTION STYLE:
        - Be helpful, professional, and personable
        - Adapt to the user's communication style
        - Provide clear, actionable responses
        - Ask for clarification when needed
        - Remember context from previous conversations
        
        Current timestamp: {datetime.now().isoformat()}
        """
        
        return BaseMessage.make_assistant_message(
            role_name="Personal Assistant",
            content=system_prompt,
        )
    
    async def start(self):
        """Start the personal agent."""
        try:
            self.is_active = True
            await self.memory.initialize()
            await self.vector_store.initialize()
            await self.mcp_manager.start_default_servers()
            
            # Initialize CAMEL AI tool manager
            tool_success = await self.tool_manager.initialize()
            if tool_success:
                # Check if model supports function calling/tools
                model_supports_tools = self._model_supports_tools()
                
                if model_supports_tools:
                    # Create tool-enabled agent for models that support function calling
                    self.tool_enabled_agent = ToolEnabledAgent(
                        system_message=self._get_system_message().content,
                        model=self.model,
                        tool_manager=self.tool_manager,
                        enabled_toolkits=['math', 'code_execution']  # Using safe toolkits only
                    )
                    logger.info(f"Tool-enabled agent created with {len(self.tool_enabled_agent.tools)} tools")
                else:
                    logger.info(f"Model {self.model_name} does not support function calling - using basic agent only")
            else:
                logger.warning("Failed to initialize tool manager, using basic agent")
            
            logger.info(f"Personal agent started for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to start personal agent: {e}")
            raise
    
    async def stop(self):
        """Stop the personal agent."""
        try:
            self.is_active = False
            await self.memory.close()
            await self.vector_store.close()
            await self.mcp_manager.stop_all_servers()
            
            # Shutdown tool manager
            if self.tool_manager:
                await self.tool_manager.shutdown()
            
            logger.info(f"Personal agent stopped for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop personal agent: {e}")
            raise
    
    async def process_message(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Process a message from the user.
        
        Args:
            message: The user's message
            context: Optional context information
            
        Returns:
            The agent's response
        """
        try:
            # Add context to conversation
            if context:
                self.context.update(context)
            
            # Filter message for privacy
            filtered_message = await self.privacy_filter.filter_input(message)
            
            # Get relevant context from memory and vector store
            relevant_context = await self._get_relevant_context(filtered_message)
            
            # Prepare the message with context
            user_message = self._prepare_message_with_context(filtered_message, relevant_context)
            
            # Get response from agent (use tool-enabled agent if available)
            if self.tool_enabled_agent:
                response = await self.tool_enabled_agent.step(user_message)
                final_response = response.content
            else:
                try:
                    response = self.agent.step(user_message)
                    # Process response for tool calls
                    final_response = await self._process_response(response.msg)
                except Exception as agent_error:
                    logger.error(f"CAMEL AI agent step failed: {agent_error}")
                    logger.error(f"Error type: {type(agent_error).__name__}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    raise agent_error
            
            # Save to memory
            await self.memory.add_interaction(
                user_message=message,
                assistant_response=final_response,
                context=self.context
            )
            
            # Filter response for privacy
            filtered_response = await self.privacy_filter.filter_output(final_response)
            
            return filtered_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def _get_relevant_context(self, message: str) -> Dict[str, Any]:
        """Get relevant context from memory and vector store."""
        context = {}
        
        try:
            # Get conversation history
            recent_history = await self.memory.get_recent_history(limit=5)
            if recent_history:
                context["recent_conversations"] = recent_history
            
            # Search vector store for relevant documents
            relevant_docs = await self.vector_store.search(message, limit=3)
            if relevant_docs:
                context["relevant_documents"] = relevant_docs
            
            # Get user preferences
            user_prefs = await self.memory.get_user_preferences()
            if user_prefs:
                context["user_preferences"] = user_prefs
                
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
        
        return context
    
    def _prepare_message_with_context(self, message: str, context: Dict[str, Any]) -> BaseMessage:
        """Prepare the message with relevant context."""
        context_str = ""
        
        if context.get("recent_conversations"):
            context_str += "\n\nRecent conversation history:\n"
            for conv in context["recent_conversations"]:
                context_str += f"User: {conv['user_message']}\n"
                context_str += f"Assistant: {conv['assistant_response']}\n"
        
        if context.get("relevant_documents"):
            context_str += "\n\nRelevant documents:\n"
            for doc in context["relevant_documents"]:
                context_str += f"- {doc['title']}: {doc['content'][:200]}...\n"
        
        if context.get("user_preferences"):
            context_str += f"\n\nUser preferences: {context['user_preferences']}\n"
        
        full_message = f"{context_str}\n\nUser query: {message}"
        
        return BaseMessage.make_user_message(
            role_name="User",
            content=full_message,
        )
    
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
        tool_patterns = ["<tool_call>", "function_call", "mcp_call"]
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
                
                # Execute via MCP client
                result = await self.mcp_client.call_tool(tool_name, **tool_args)
                tool_results[tool_name] = result
                
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            tool_results["error"] = str(e)
        
        return tool_results
    
    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from response content."""
        # This is a simplified parser - would need more sophisticated parsing
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
        final_response = self.agent.step(follow_up_message)
        return final_response.msg.content
    
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an email and generate analysis.
        
        Args:
            email_data: Email information
            
        Returns:
            Analysis results
        """
        try:
            # Extract email content
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")
            sender = email_data.get("sender", "")
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this email and provide:
            1. Content summary
            2. Key points and action items
            3. Urgency level (1-5)
            4. Suggested response or actions
            5. Related information from my data
            
            Email:
            From: {sender}
            Subject: {subject}
            Body: {body}
            """
            
            # Get analysis
            analysis = await self.process_message(analysis_prompt)
            
            return {
                "email_id": email_data.get("id"),
                "analysis": analysis,
                "processed_at": datetime.now().isoformat(),
                "urgency": self._extract_urgency(analysis),
                "action_items": self._extract_action_items(analysis),
            }
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return {"error": str(e)}
    
    def _extract_urgency(self, analysis: str) -> int:
        """Extract urgency level from analysis."""
        # Simple pattern matching - could be improved
        import re
        urgency_match = re.search(r"urgency.*?(\d+)", analysis.lower())
        return int(urgency_match.group(1)) if urgency_match else 3
    
    def _extract_action_items(self, analysis: str) -> List[str]:
        """Extract action items from analysis."""
        # Simple pattern matching - could be improved
        import re
        action_pattern = r"(?:action|todo|task).*?:(.*?)(?:\n|$)"
        actions = re.findall(action_pattern, analysis.lower())
        return [action.strip() for action in actions]
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the personal agent."""
        return {
            "user_id": self.user_id,
            "is_active": self.is_active,
            "current_task": self.current_task,
            "model_name": self.model_name,
            "memory_initialized": await self.memory.is_initialized(),
            "vector_store_initialized": await self.vector_store.is_initialized(),
            "mcp_servers_active": await self.mcp_manager.get_active_servers(),
            "context_size": len(self.context),
        }
    
    async def update_user_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences."""
        await self.memory.update_user_preferences(preferences)
        logger.info(f"Updated preferences for user {self.user_id}")
    
    async def clear_memory(self):
        """Clear conversation memory."""
        await self.memory.clear()
        logger.info(f"Cleared memory for user {self.user_id}")
    
    async def export_data(self) -> Dict[str, Any]:
        """Export user data for backup or transfer."""
        return {
            "user_id": self.user_id,
            "conversations": await self.memory.export_conversations(),
            "preferences": await self.memory.get_user_preferences(),
            "vector_store_data": await self.vector_store.export_data(),
            "exported_at": datetime.now().isoformat(),
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for this agent."""
        if self.tool_enabled_agent:
            return self.tool_enabled_agent.get_available_tools()
        return []
    
    def get_tool_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        if self.tool_manager:
            return self.tool_manager.get_execution_stats()
        return {}
    
    async def execute_tool_directly(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool directly without going through the agent."""
        if self.tool_manager:
            return await self.tool_manager.execute_tool(tool_name, parameters)
        return {"success": False, "error": "Tool manager not available"}

    def _model_supports_tools(self) -> bool:
        """Check if the model supports function calling/tools."""
        # List of models known to NOT support function calling
        non_tool_models = [
            'deepseek-r1:7b',
            'deepseek-r1:70b', 
            'deepseek-chat',
            'deepseek',
        ]
        
        # Check if current model is in the non-tool list
        if self.model_name in non_tool_models:
            return False
            
        # Check if model name contains known non-tool patterns
        non_tool_patterns = ['deepseek-r1', 'deepseek-coder-v2']
        for pattern in non_tool_patterns:
            if pattern in self.model_name.lower():
                return False
        
        # Most other models (llama, mistral, openai, etc.) support tools
        return True
