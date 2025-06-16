"""
Personal Agent - Full access chatbot with private data and tools
"""
from typing import List, Dict, Any, Optional
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import TaskType, RoleType

from src.config.settings import settings
from src.rag.retrieval.retriever import PersonalDataRetriever
from src.tools.mcp_servers.client import MCPClient
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
        self.mcp_client = MCPClient()
        self.memory = ConversationMemory("personal")
        self.persona_prompt = self._load_persona_prompt()
        
        # Initialize CAMEL agents
        self.user_agent = self._create_user_agent()
        self.assistant_agent = self._create_assistant_agent()
        self.task_specifier = self._create_task_specifier()
    
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
    
    def _create_user_agent(self) -> ChatAgent:
        """Create the AI User agent for task planning"""
        user_prompt = """
You are an AI User agent responsible for planning and coordinating tasks.
Your role is to:
1. Analyze user requests and break them into actionable steps
2. Coordinate with the Assistant agent to execute tasks
3. Ensure all necessary information is gathered before proceeding
4. Manage the overall flow of multi-step operations

When you receive a user request, plan the approach and instruct the Assistant agent accordingly.
"""
        
        return ChatAgent(
            system_message=user_prompt,
            model_type=settings.llm.model_name,
            task_type=TaskType.AI_SOCIETY
        )
    
    def _create_assistant_agent(self) -> ChatAgent:
        """Create the AI Assistant agent for task execution"""
        assistant_prompt = f"""
{self.persona_prompt}

You are an AI Assistant agent responsible for executing tasks.
Your capabilities include:
- Retrieving information from personal data using RAG
- Using tools via MCP (email, browser, system commands)
- Maintaining conversation context
- Providing detailed responses in the user's style

Available tools:
- email: send_email, read_emails, search_emails
- browser: browse_url, search_web
- system: execute_command, list_files
- rag: search_personal_data

Always use tools when needed to provide accurate information or perform actions.
"""
        
        return ChatAgent(
            system_message=assistant_prompt,
            model_type=settings.llm.model_name,
            task_type=TaskType.AI_SOCIETY
        )
    
    def _create_task_specifier(self) -> ChatAgent:
        """Create the Task Specifier agent for refining requests"""
        specifier_prompt = """
You are a Task Specifier agent responsible for clarifying and refining user requests.
Your role is to:
1. Analyze vague or complex requests
2. Break them down into specific, actionable tasks
3. Identify what information or tools might be needed
4. Ensure the request is well-defined before execution

Provide clear, structured task specifications.
"""
        
        return ChatAgent(
            system_message=specifier_prompt,
            model_type=settings.llm.model_name,
            task_type=TaskType.AI_SOCIETY
        )
    
    async def process_message(self, user_message: str, conversation_id: str = None) -> str:
        """
        Process a user message through the multi-agent system
        
        Args:
            user_message: The user's input message
            conversation_id: Optional conversation ID for context
            
        Returns:
            The agent's response
        """
        try:
            # Load conversation context
            context = await self.memory.get_context(conversation_id) if conversation_id else []
            
            # Step 1: Task specification (if needed)
            if self._needs_task_specification(user_message):
                task_spec = await self._specify_task(user_message)
                working_message = task_spec
            else:
                working_message = user_message
            
            # Step 2: Retrieve relevant personal data
            relevant_data = await self.retriever.retrieve_relevant_data(working_message)
            
            # Step 3: Multi-agent coordination
            response = await self._coordinate_agents(working_message, relevant_data, context)
            
            # Step 4: Save to memory
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
        """Determine if the plan requires tool usage"""
        tool_indicators = [
            "send email", "browse", "search web", "execute", 
            "command", "file", "read", "write"
        ]
        return any(indicator in content.lower() for indicator in tool_indicators)
    
    async def _execute_tools(self, plan_content: str) -> str:
        """Execute tools based on the plan"""
        # This is a simplified tool execution
        # In practice, you'd parse the plan and execute specific tools
        try:
            if "send email" in plan_content.lower():
                return await self.mcp_client.call_tool("email", "send_email", {})
            elif "browse" in plan_content.lower() or "search web" in plan_content.lower():
                return await self.mcp_client.call_tool("browser", "browse_url", {})
            elif "execute" in plan_content.lower() or "command" in plan_content.lower():
                return await self.mcp_client.call_tool("system", "execute_command", {})
            else:
                return "No specific tools executed"
        except Exception as e:
            return f"Tool execution error: {str(e)}" 