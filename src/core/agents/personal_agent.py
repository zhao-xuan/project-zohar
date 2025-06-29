"""
Personal Agent - Full access chatbot with private data and tools
"""
from typing import List, Dict, Any, Optional
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import TaskType, RoleType

from src.config.settings import settings
from src.rag.retrieval.retriever import PersonalDataRetriever
from src.tools.mcp_servers.client import ToolClient
from src.core.memory.conversation_memory import ConversationMemory


class PersonalAgent:
    """
    Personal chatbot agent with full access to private data and tools.
    
    This agent can:
    - Access all personal data through RAG
    - Use all available tools (email, browser, system commands)
    - Maintain conversation memory
    - Mimic user's personal tone and style
    """
    
    def __init__(self):
        self.retriever = PersonalDataRetriever()
        self.tool_client = ToolClient()
        self.memory = ConversationMemory("personal")
        self.persona_prompt = self._load_persona_prompt()
        
        # Note: Using direct Ollama integration instead of CAMEL agents
    
    def _load_persona_prompt(self) -> str:
        """Load personal tone and style from configuration"""
        try:
            with open(settings.persona.personal_tone_examples_path, 'r') as f:
                tone_examples = f.read()
            
            with open(settings.persona.personal_bio_path, 'r') as f:
                bio = f.read()
            
            return f"""
You are a personal AI assistant representing the user. You have access to their private data and can perform actions on their behalf.

PERSONALITY AND TONE:
{bio}

COMMUNICATION STYLE:
{tone_examples}

CAPABILITIES:
- Access to personal emails, documents, and chat history
- Can send emails, browse the web, and execute system commands
- Maintain context across conversations
- Provide detailed, personalized responses

IMPORTANT GUIDELINES:
- Always maintain the user's communication style and tone
- Protect private information - never share sensitive data inappropriately
- Confirm before taking potentially impactful actions (sending emails, etc.)
- Use retrieved personal data to provide accurate, contextualized responses
- Be proactive in helping with tasks and questions
"""
        except FileNotFoundError:
            return """
You are a personal AI assistant with access to private data and tools.
You can help with emails, documents, web browsing, and system tasks.
Always confirm before taking actions that could have consequences.
"""
    
    # CAMEL agent methods commented out - using direct Ollama integration instead
    # 
    # def _create_user_agent(self) -> ChatAgent:
    #     """Create the AI User agent for task planning"""
    #     user_prompt = """..."""
    #     return ChatAgent(system_message=user_prompt, ...)
    # 
    # def _create_assistant_agent(self) -> ChatAgent:
    #     """Create the AI Assistant agent for task execution"""
    #     assistant_prompt = f"""..."""
    #     return ChatAgent(system_message=assistant_prompt, ...)
    # 
    # def _create_task_specifier(self) -> ChatAgent:
    #     """Create the Task Specifier agent for refining requests"""
    #     specifier_prompt = """..."""
    #     return ChatAgent(system_message=specifier_prompt, ...)
    
    async def process_message(self, user_message: str, conversation_id: str = None) -> str:
        """
        Process a user message using Ollama-powered intelligent system
        
        Args:
            user_message: The user's input message
            conversation_id: Optional conversation ID for context
            
        Returns:
            The agent's response
        """
        try:
            from src.services.ollama_service import ollama_service
            
            # Check if Ollama is available
            if not await ollama_service.is_available():
                return "❌ Local AI service (Ollama) is not available. Please run 'make start-ollama' to start the service."
            
            # Load conversation context
            context = await self.memory.get_context(conversation_id) if conversation_id else []
            
            # Retrieve relevant personal data
            relevant_data = await self.retriever.retrieve_relevant_data(user_message)
            
            # Check if we need tools
            tool_results = ""
            if self._requires_tools(user_message):
                tool_results = await self._execute_tools(user_message)
            
            # Create comprehensive prompt for Ollama
            full_prompt = self._create_comprehensive_prompt(
                user_message, context, relevant_data, tool_results
            )
            
            # Get response from Ollama with persona
            response = await ollama_service.generate_response(
                prompt=full_prompt,
                system_prompt=self.persona_prompt
            )
            
            # Save to memory
            if conversation_id:
                await self.memory.add_exchange(conversation_id, user_message, response)
            
            return response
            
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"
    
    def _needs_task_specification(self, message: str) -> bool:
        """Determine if a message needs task specification"""
        # Simple heuristic - complex or vague requests might need specification
        complexity_indicators = [
            "help me with", "figure out", "organize", "plan", 
            "multiple", "several", "complex", "manage"
        ]
        return any(indicator in message.lower() for indicator in complexity_indicators)
    
    async def _specify_task(self, message: str) -> str:
        """Use task specifier to refine the request"""
        specifier_message = BaseMessage.make_user_message(
            role_name="User",
            content=f"Please specify this task clearly: {message}"
        )
        
        response = await self.task_specifier.step(specifier_message)
        return response.msg.content
    
    async def _coordinate_agents(self, message: str, relevant_data: List[Dict], context: List[Dict]) -> str:
        """Coordinate between user and assistant agents"""
        # Format context and data for agents
        context_str = self._format_context(context)
        data_str = self._format_retrieved_data(relevant_data)
        
        # User agent plans the approach
        planning_prompt = f"""
User request: {message}

Available context: {context_str}

Retrieved personal data: {data_str}

Plan the approach to handle this request and instruct the Assistant agent.
"""
        
        user_message = BaseMessage.make_user_message(
            role_name="User", 
            content=planning_prompt
        )
        
        plan_response = await self.user_agent.step(user_message)
        
        # Assistant agent executes the plan
        assistant_message = BaseMessage.make_user_message(
            role_name="User",
            content=f"Execute this plan: {plan_response.msg.content}"
        )
        
        # Check if tools need to be used
        if self._requires_tools(plan_response.msg.content):
            tool_results = await self._execute_tools(plan_response.msg.content)
            assistant_message.content += f"\n\nTool results: {tool_results}"
        
        final_response = await self.assistant_agent.step(assistant_message)
        return final_response.msg.content
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format conversation context for agents"""
        if not context:
            return "No previous context"
        
        formatted = []
        for exchange in context[-5:]:  # Last 5 exchanges
            formatted.append(f"User: {exchange['user_message']}")
            formatted.append(f"Assistant: {exchange['assistant_response']}")
        
        return "\n".join(formatted)
    
    def _format_retrieved_data(self, data: List[Dict]) -> str:
        """Format retrieved data for agents"""
        if not data:
            return "No relevant personal data found"
        
        formatted = []
        for item in data:
            formatted.append(f"Source: {item.get('source', 'Unknown')}")
            formatted.append(f"Content: {item.get('content', '')[:500]}...")
            formatted.append("---")
        
        return "\n".join(formatted)
    
    def _requires_tools(self, content: str) -> bool:
        """Determine if the request requires tool usage"""
        tool_indicators = [
            "send email", "email", "browse", "search web", "execute", 
            "command", "file", "read", "write", "check", "find", "search"
        ]
        return any(indicator in content.lower() for indicator in tool_indicators)
    
    def _create_comprehensive_prompt(self, user_message: str, context: List[Dict], 
                                   relevant_data: List[Dict], tool_results: str) -> str:
        """Create a comprehensive prompt combining all available information"""
        
        # Format context
        context_str = self._format_context(context)
        
        # Format retrieved data
        data_str = self._format_retrieved_data(relevant_data)
        
        # Build comprehensive prompt
        prompt_parts = [
            f"User Request: {user_message}",
            "",
            "Previous Conversation Context:",
            context_str,
            "",
            "Retrieved Personal Data:",
            data_str,
        ]
        
        if tool_results:
            prompt_parts.extend([
                "",
                "Tool Execution Results:",
                tool_results,
            ])
        
        prompt_parts.extend([
            "",
            "Instructions:",
            "- Use the retrieved personal data to provide accurate, contextualized responses",
            "- Maintain my personal communication style and tone",
            "- If tool results are available, incorporate them into your response",
            "- Be helpful and proactive in offering assistance",
            "- If you need to access specific data or perform actions, mention what you would do",
            "",
            "Please provide a helpful and personalized response:"
        ])
        
        return "\n".join(prompt_parts)
    
    async def _execute_tools(self, plan_content: str) -> str:
        """Execute tools based on the plan"""
        # This is a simplified tool execution
        # In practice, you'd parse the plan and execute specific tools
        try:
            if "send email" in plan_content.lower():
                return await self.tool_client.call_tool("email", "send_email", {})
            elif "browse" in plan_content.lower() or "search web" in plan_content.lower():
                return await self.tool_client.call_tool("browser", "browse_url", {})
            elif "execute" in plan_content.lower() or "command" in plan_content.lower():
                return await self.tool_client.call_tool("system", "execute_command", {})
            else:
                return "No specific tools executed"
        except Exception as e:
            return f"Tool execution error: {str(e)}" 