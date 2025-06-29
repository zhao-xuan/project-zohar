"""
Public Agent - Restricted chatbot for general public use
"""
from typing import List, Dict, Any, Optional
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import TaskType

from src.config.settings import settings
from src.rag.retrieval.retriever import PublicDataRetriever
from src.core.memory.conversation_memory import ConversationMemory


class PublicAgent:
    """
    Public chatbot agent with restricted access to only public information.
    
    This agent can:
    - Access only public biographical data
    - Use limited tools (web search only)
    - Maintain conversation memory for session
    - Mimic user's public communication style
    - Cannot access private data or perform sensitive actions
    """
    
    def __init__(self):
        self.retriever = PublicDataRetriever()
        self.memory = ConversationMemory("public")
        self.persona_prompt = self._load_public_persona_prompt()
        
        # Note: Using direct Ollama integration instead of CAMEL agents
    
    def _load_public_persona_prompt(self) -> str:
        """Load public persona information"""
        try:
            with open(settings.persona.public_bio_path, 'r') as f:
                public_bio = f.read()
            
            # Extract tone from personal examples but sanitize
            try:
                with open(settings.persona.personal_tone_examples_path, 'r') as f:
                    tone_examples = f.read()
                # Extract general communication style without personal details
                tone_style = self._extract_communication_style(tone_examples)
            except FileNotFoundError:
                tone_style = "Professional, helpful, and friendly communication style."
            
            return f"""
You are a public-facing AI assistant representing the user for general inquiries.

PUBLIC INFORMATION:
{public_bio}

COMMUNICATION STYLE:
{tone_style}

RESTRICTIONS:
- You can ONLY share information that is publicly available
- You cannot access private emails, documents, or personal data
- You cannot perform actions like sending emails or executing commands
- You can provide general information and help with public inquiries
- You can search the web for publicly available information

CAPABILITIES:
- Answer questions about publicly available information
- Provide general assistance and information
- Search the web for relevant information
- Maintain conversational context

IMPORTANT GUIDELINES:
- Always maintain a helpful and professional tone
- If asked about private information, politely explain that you can only share public information
- Redirect sensitive queries appropriately
- Be transparent about your limitations
"""
        except FileNotFoundError:
            return """
You are a public-facing AI assistant for general inquiries.
You can only share publicly available information and cannot access private data.
You can help with general questions and search the web for information.
Always be helpful, professional, and transparent about your limitations.
"""
    
    def _extract_communication_style(self, tone_examples: str) -> str:
        """Extract general communication style from personal examples"""
        # This is a simplified extraction - in practice, you might use
        # a more sophisticated method to extract style without personal content
        
        style_elements = []
        
        # Analyze for general tone characteristics
        if "casual" in tone_examples.lower() or "hey" in tone_examples.lower():
            style_elements.append("Conversational and approachable")
        
        if "thanks" in tone_examples.lower() or "appreciate" in tone_examples.lower():
            style_elements.append("Appreciative and courteous")
        
        if "!" in tone_examples:
            style_elements.append("Enthusiastic and expressive")
        
        if len(tone_examples.split(".")) > 10:  # Many sentences
            style_elements.append("Detailed and thorough in explanations")
        
        if not style_elements:
            style_elements.append("Professional and helpful")
        
        return ". ".join(style_elements) + "."
    
    # CAMEL agent method commented out - using direct Ollama integration instead
    # 
    # def _create_public_assistant_agent(self) -> ChatAgent:
    #     """Create the public assistant agent with limited capabilities"""
    #     assistant_prompt = f"""..."""
    #     return ChatAgent(system_message=assistant_prompt, ...)
    
    async def process_message(self, user_message: str, conversation_id: str = None) -> str:
        """
        Process a user message with restricted public access using Ollama
        
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
                return "❌ Local AI service is not available. Please contact the administrator."
            
            # Check for restricted content requests
            if self._is_restricted_request(user_message):
                return self._get_restriction_response()
            
            # Load conversation context (limited)
            context = await self.memory.get_context(conversation_id) if conversation_id else []
            
            # Retrieve public data only
            relevant_data = await self.retriever.retrieve_public_data(user_message)
            
            # Check if web search would be helpful
            web_results = ""
            if self._needs_web_search(user_message):
                web_results = await self._perform_web_search(user_message)
            
            # Create comprehensive prompt for public response
            full_prompt = self._create_public_prompt(
                user_message, context, relevant_data, web_results
            )
            
            # Get response from Ollama with public restrictions
            response = await ollama_service.generate_response(
                prompt=full_prompt,
                system_prompt=self.persona_prompt
            )
            
            # Save to memory (limited retention)
            if conversation_id:
                await self.memory.add_exchange(conversation_id, user_message, response)
            
            return response
            
        except Exception as e:
            return "I encountered an error processing your request. Please try again or contact support."
    
    def _is_restricted_request(self, message: str) -> bool:
        """Check if the request involves restricted/private information"""
        restricted_keywords = [
            "email", "send", "private", "personal", "confidential",
            "password", "login", "execute", "command", "file",
            "document", "internal", "delete", "modify", "admin"
        ]
        
        return any(keyword in message.lower() for keyword in restricted_keywords)
    
    def _get_restriction_response(self) -> str:
        """Get a standard response for restricted requests"""
        return """
I can only access publicly available information and cannot perform private actions like accessing emails, files, or executing commands. 

For personal matters or private information, please contact the user directly. I'm here to help with general questions and publicly available information.

Is there something else I can help you with using publicly available information?
"""
    
    # Method removed - now using direct Ollama integration in process_message
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format conversation context (limited for public use)"""
        if not context:
            return "No previous context"
        
        # Only keep last 3 exchanges for public conversations
        formatted = []
        for exchange in context[-3:]:
            formatted.append(f"User: {exchange['user_message']}")
            formatted.append(f"Assistant: {exchange['assistant_response']}")
        
        return "\n".join(formatted)
    
    def _format_public_data(self, data: List[Dict]) -> str:
        """Format public data for the agent"""
        if not data:
            return "No relevant public information found"
        
        formatted = []
        for item in data:
            formatted.append(f"Source: {item.get('source', 'Public Bio')}")
            formatted.append(f"Content: {item.get('content', '')}")
            formatted.append("---")
        
        return "\n".join(formatted)
    
    def _needs_web_search(self, message: str) -> bool:
        """Determine if web search would be helpful"""
        search_indicators = [
            "what is", "who is", "when did", "where is", "how to",
            "current", "latest", "recent", "news", "information about"
        ]
        return any(indicator in message.lower() for indicator in search_indicators)
    
    async def _perform_web_search(self, query: str) -> str:
        """Perform a web search for publicly available information"""
        # Simplified web search - in practice, integrate with actual search API
        try:
            # This would integrate with a web search tool/API
            # For now, return a placeholder
            return f"Web search results for: {query} (Implementation needed)"
        except Exception as e:
            return "Web search unavailable at the moment"
    
    def _create_public_prompt(self, user_message: str, context: List[Dict], 
                            relevant_data: List[Dict], web_results: str) -> str:
        """Create a comprehensive prompt for public responses"""
        
        # Format context (limited)
        context_str = self._format_context(context)
        
        # Format public data
        data_str = self._format_public_data(relevant_data)
        
        # Build comprehensive prompt
        prompt_parts = [
            f"User Request: {user_message}",
            "",
            "Previous Conversation Context (Limited):",
            context_str,
            "",
            "Available Public Information:",
            data_str,
        ]
        
        if web_results:
            prompt_parts.extend([
                "",
                "Web Search Results:",
                web_results,
            ])
        
        prompt_parts.extend([
            "",
            "Instructions:",
            "- Only use publicly available information in your response",
            "- Maintain a professional and helpful tone",
            "- If asked about private information, politely explain limitations",
            "- Be transparent about what you can and cannot access",
            "- Provide helpful guidance within public information boundaries",
            "",
            "Please provide a helpful public response:"
        ])
        
        return "\n".join(prompt_parts) 