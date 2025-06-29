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
    - Handle temporal and metadata-based queries
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
- Advanced metadata-based search (by date, sender, file type, etc.)

IMPORTANT GUIDELINES:
- Always maintain the user's communication style and tone
- Protect private information - never share sensitive data inappropriately
- Confirm before taking potentially impactful actions (sending emails, etc.)
- Use retrieved personal data to provide accurate, contextualized responses
- Be proactive in helping with tasks and questions

DOCUMENT SEARCH EXPERTISE:
- When you find documents in the retrieved data, clearly explain what they are
- Pay special attention to file names, extensions, and content types  
- Highlight important documents (agreements, contracts, certificates, receipts, media files, etc.) prominently
- Always mention the document location/path when relevant
- If a document is marked as "Available for review", explain that it can be accessed
- Recognize various file formats and explain their purpose (PDFs, images, audio, video, text files, etc.)

TEMPORAL AND METADATA SEARCH EXPERTISE:
- I can search for messages by specific dates, senders, and time periods
- When you see dates and sender information in search results, use them to provide context
- For temporal queries (earliest, latest, date-specific), pay attention to chronological order
- When showing chat messages, always include the date and sender information
- If asked about conversation timelines, I can analyze patterns and provide summaries
"""
        except FileNotFoundError:
            return """
You are a personal AI assistant with access to private data and tools.
You can help with emails, documents, web browsing, and system tasks.
Always confirm before taking actions that could have consequences.

DOCUMENT SEARCH EXPERTISE:
- When you find documents in the retrieved data, clearly explain what they are
- Pay special attention to file names, extensions, and content types  
- Highlight important documents (agreements, contracts, certificates, receipts, media files, etc.) prominently
- Always mention the document location/path when relevant
- If a document is marked as "Available for review", explain that it can be accessed
- Recognize various file formats and explain their purpose (PDFs, images, audio, video, text files, etc.)

TEMPORAL AND METADATA SEARCH EXPERTISE:
- I can search for messages by specific dates, senders, and time periods
- When you see dates and sender information in search results, use them to provide context
- For temporal queries (earliest, latest, date-specific), pay attention to chronological order
- When showing chat messages, always include the date and sender information
- If asked about conversation timelines, I can analyze patterns and provide summaries
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
    
    def _detect_specialized_query(self, user_message: str) -> Optional[str]:
        """Detect if this is a specialized metadata query that needs special handling"""
        message_lower = user_message.lower()
        
        # Result reference queries (expand on result X, tell me more about result Y)
        if any(pattern in message_lower for pattern in ['result ', 'expand on result', 'tell me more about result', 'more details on result']):
            return "result_reference"
        
        # Temporal queries
        if any(keyword in message_lower for keyword in ['earliest', 'first', 'oldest', 'latest', 'last', 'newest']):
            return "temporal"
        
        # Sender-based queries
        if any(pattern in message_lower for pattern in ['from ', 'sent by', 'messages by']):
            return "sender_based"
        
        # Date-based queries
        if any(pattern in message_lower for pattern in ['on ', 'in 20', 'date', 'when']):
            return "date_based"
        
        # Timeline analysis
        if any(keyword in message_lower for keyword in ['timeline', 'conversation history', 'over time']):
            return "timeline_analysis"
        
        return None
    
    def _extract_result_number(self, user_message: str) -> Optional[int]:
        """Extract result number from user message like 'expand on result 2'"""
        import re
        message_lower = user_message.lower()
        
        # Look for patterns like "result 2", "result number 3", etc.
        patterns = [
            r'result\s+(\d+)',
            r'result\s+number\s+(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s+result',
            r'#(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return int(match.group(1))
        
        return None
    
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
            
            # Detect if this is a specialized query
            query_type = self._detect_specialized_query(user_message)
            result_number = None
            
            # Handle result reference queries
            if query_type == "result_reference":
                result_number = self._extract_result_number(user_message)
                if result_number and conversation_id:
                    # Get the most recent search results
                    stored_results = await self.memory.get_most_recent_search_results(conversation_id)
                    if stored_results and 1 <= result_number <= len(stored_results):
                        # Get the specific result the user is asking about
                        target_result = stored_results[result_number - 1]
                        relevant_data = [target_result]  # Use the specific result for expansion
                    else:
                        return f"I couldn't find result #{result_number} from your previous search. Please try your search again or specify a different result number."
                else:
                    return "I couldn't determine which result you're referring to. Please specify like 'expand on result 2' or search again."
            
            # Retrieve relevant personal data with enhanced parameters for special queries
            elif query_type == "temporal":
                relevant_data = await self.retriever.retrieve_relevant_data(user_message, limit=8)
            elif query_type == "sender_based":
                relevant_data = await self.retriever.retrieve_relevant_data(user_message, limit=10)
            elif query_type == "timeline_analysis":
                # For timeline analysis, we might want to use the specialized method
                if "kristiane" in user_message.lower():
                    timeline_data = await self.retriever.analyze_conversation_timeline("Kristiane")
                    relevant_data = [{"source": "timeline_analysis", "content": f"📊 CONVERSATION TIMELINE ANALYSIS:\n{timeline_data}", "metadata": {"type": "timeline"}, "relevance_score": 1.0}]
                else:
                    timeline_data = await self.retriever.analyze_conversation_timeline()
                    relevant_data = [{"source": "timeline_analysis", "content": f"📊 CONVERSATION TIMELINE ANALYSIS:\n{timeline_data}", "metadata": {"type": "timeline"}, "relevance_score": 1.0}]
            else:
                relevant_data = await self.retriever.retrieve_relevant_data(user_message, limit=5)
            
            # Check if we need tools
            tool_results = ""
            if self._requires_tools(user_message):
                tool_results = await self._execute_tools(user_message)
            
            # Create comprehensive prompt for Ollama  
            # Pass result_number only for result_reference queries
            result_num_to_pass = result_number if query_type == "result_reference" else None
            full_prompt = self._create_comprehensive_prompt(
                user_message, context, relevant_data, tool_results, query_type, result_num_to_pass
            )
            
            # Get response from Ollama with persona
            response = await ollama_service.generate_response(
                prompt=full_prompt,
                system_prompt=self.persona_prompt
            )
            
            # Determine if this was a search that should store results for future reference
            should_store_results = False
            search_results_to_store = None
            
            # Check if the user asked for numbered results (top X, list X messages, etc.)
            if any(pattern in user_message.lower() for pattern in ['top ', 'list ', 'find ', 'search ', 'show me', 'messages that']):
                if query_type != "result_reference":  # Don't store results for result reference queries
                    should_store_results = True
                    search_results_to_store = relevant_data
            
            # Save to memory with search results if applicable
            if conversation_id:
                if should_store_results:
                    await self.memory.add_exchange(
                        conversation_id, 
                        user_message, 
                        response,
                        search_results=search_results_to_store
                    )
                else:
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
    
    def _format_context(self, context: List[Dict], exclude_search_results: bool = False) -> str:
        """Format conversation context for agents"""
        if not context:
            return "No previous context"
        
        formatted = []
        for exchange in context[-5:]:  # Last 5 exchanges
            user_msg = exchange['user_message']
            assistant_resp = exchange['assistant_response']
            
            # If excluding search results, filter out search-related exchanges
            if exclude_search_results:
                # Skip if this was a search query that returned numbered results
                if any(pattern in user_msg.lower() for pattern in ['top ', 'list ', 'find ', 'search ', 'messages that']):
                    # Only include the query, not the detailed results
                    formatted.append(f"User: {user_msg}")
                    formatted.append(f"Assistant: [Previous search completed - results excluded to avoid contamination]")
                    continue
                # Skip result reference queries
                elif any(pattern in user_msg.lower() for pattern in ['result ', 'expand on result', 'tell me more about result']):
                    formatted.append(f"User: {user_msg}")
                    formatted.append(f"Assistant: [Previous result expansion - excluded to avoid contamination]")
                    continue
            
            formatted.append(f"User: {user_msg}")
            formatted.append(f"Assistant: {assistant_resp}")
        
        return "\n".join(formatted)
    
    def _format_retrieved_data(self, data: List[Dict]) -> str:
        """Format retrieved data for agents with enhanced document presentation"""
        if not data:
            return "No relevant personal data found"
        
        formatted = []
        formatted.append(f"📊 Found {len(data)} relevant results:")
        formatted.append("")
        
        for i, item in enumerate(data, 1):
            # Get enhanced content (already formatted by retriever)
            content = item.get('content', '')
            source = item.get('source', 'Unknown')
            relevance = item.get('relevance_score', 0)
            metadata = item.get('metadata', {})
            
            # Format the result entry with cleaner presentation
            formatted.append(f"🔍 RESULT {i} (Similarity: {relevance:.3f})")
            
            # Add temporal information first if available (most important for user queries)
            if 'parsed_date' in item:
                if isinstance(item['parsed_date'], str):
                    # Handle stored datetime strings
                    try:
                        from datetime import datetime
                        parsed_date = datetime.strptime(item['parsed_date'], '%Y-%m-%d %H:%M:%S')
                        formatted.append(f"📅 {parsed_date.strftime('%B %d, %Y at %I:%M %p')}")
                    except:
                        formatted.append(f"📅 {item['parsed_date']}")
                else:
                    # Handle datetime objects
                    formatted.append(f"📅 {item['parsed_date'].strftime('%B %d, %Y at %I:%M %p')}")
            
            # Add the content (already enhanced by retriever)
            formatted.append(content)
            
            # Add file source info at the end (less cluttered)
            source_info = []
            if 'filename' in metadata:
                source_info.append(f"File: {metadata['filename']}")
            if source_info:
                formatted.append(f"📂 Source: {' | '.join(source_info)}")
            
            formatted.append("-" * 60)
        
        return "\n".join(formatted)
    
    def _requires_tools(self, content: str) -> bool:
        """Determine if the request requires tool usage"""
        tool_indicators = [
            "send email", "email", "browse", "search web", "execute", 
            "command", "file", "read", "write", "check", "find", "search"
        ]
        return any(indicator in content.lower() for indicator in tool_indicators)
    
    def _create_comprehensive_prompt(self, user_message: str, context: List[Dict], 
                                   relevant_data: List[Dict], tool_results: str, query_type: str = None, result_number: int = None) -> str:
        """Create a comprehensive prompt combining all available information"""
        
        # Determine if this is a new search that should exclude previous search results from context
        is_new_search = any(pattern in user_message.lower() for pattern in ['top ', 'list ', 'find ', 'search ', 'messages that'])
        exclude_search_context = is_new_search and query_type != "result_reference"
        
        # Format context (exclude previous search results for new searches to avoid contamination)
        context_str = self._format_context(context, exclude_search_results=exclude_search_context)
        
        # Format retrieved data (enhanced formatting)
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
        
        # Add contamination prevention for new searches
        if exclude_search_context:
            prompt_parts.extend([
                "",
                "🚨 CRITICAL - NEW SEARCH ALERT:",
                "- This is a NEW search query - ignore any previous search results mentioned in context",
                "- Use ONLY the 'Retrieved Personal Data' section above for your response",
                "- DO NOT reference or repeat results from previous searches",
                "- Focus exclusively on the fresh data retrieved for this specific query",
                "- If no relevant results are found in 'Retrieved Personal Data', state that clearly",
            ])
        
        if tool_results:
            prompt_parts.extend([
                "",
                "Tool Execution Results:",
                tool_results,
            ])
        
        # Add query-specific instructions
        if query_type == "result_reference" and result_number:
            prompt_parts.extend([
                "",
                "🔍 RESULT EXPANSION REQUEST:",
                f"- The user is asking you to expand on RESULT #{result_number} from their previous search",
                "- The retrieved data contains the EXACT result they're referring to",
                f"- You MUST focus on and expand ONLY result #{result_number}",
                "- Provide detailed information about this specific result",
                "- Include the full message content, context, and any additional details",
                "- Reference the original search context if helpful",
                "- Don't confuse this with other results or previous searches",
                f"- Start your response by clearly stating you're expanding on result #{result_number}",
            ])
        elif query_type == "temporal":
            prompt_parts.extend([
                "",
                "Special Instructions for Temporal Queries:",
                "- This is a temporal query (earliest, latest, first, last, etc.)",
                "- Pay attention to the chronological order of results",
                "- If you found chat messages, sort them by date and highlight the earliest/latest",
                "- Always mention the specific dates and times when available",
                "- If looking for 'earliest' messages, focus on the oldest dates found",
                "- If looking for 'latest' messages, focus on the most recent dates found",
            ])
        elif query_type == "sender_based":
            prompt_parts.extend([
                "",
                "Special Instructions for Sender-Based Queries:",
                "- This query is about messages from a specific person",
                "- Pay attention to sender names in the chat messages",
                "- Group messages by sender and highlight the requested person's messages",
                "- Include dates for each message to provide timeline context",
                "- If multiple messages from the same sender, organize them chronologically",
            ])
        elif query_type == "timeline_analysis":
            prompt_parts.extend([
                "",
                "Special Instructions for Timeline Analysis:",
                "- This is a timeline analysis query",
                "- The retrieved data contains conversation statistics and patterns",
                "- Present the timeline information in a clear, organized format",
                "- Highlight key insights like most active periods, conversation patterns, etc.",
                "- Use the date range and daily counts to provide meaningful analysis",
            ])
        
        prompt_parts.extend([
            "",
            "Special Instructions for Document/File Queries:",
            "- When documents or files are found in retrieved data, clearly identify and highlight them",
            "- Explain what type of document was found (PDF, contract, agreement, image, audio, etc.) and its significance",
            "- For any important documents (agreements, contracts, certificates, receipts, etc.), state their type explicitly",
            "- Always mention the file path/location when available so the user knows where to find the actual file",
            "- If a document is marked as 'Available for review', explain that it can be accessed at the given location",
            "- Use the filename and content preview to provide specific information about what the document contains",
            "- Distinguish between file references and actual document content in your response",
            "",
            "General Instructions:",
            "- Use the retrieved personal data to provide accurate, contextualized responses",
            "- Maintain my personal communication style and tone",
            "- If tool results are available, incorporate them into your response",
            "- Be helpful and proactive in offering assistance",
            "- For chat messages, always include date and sender information when available",
            "- Present temporal information in a clear, chronological format",
            "",
            "🚨 CRITICAL: If the user asks for 'top 5' or specific number of results:",
            "- You MUST list EVERY SINGLE result found in the retrieved data",
            "- Number them clearly: 1. Result 1, 2. Result 2, 3. Result 3, etc.",
            "- For EACH result, include: Date, Sender, and Message content", 
            "- DO NOT skip any results - if 5 results are provided, show all 5",
            "- DO NOT summarize or combine results - each gets its own numbered entry",
            "- If fewer results than requested were found, state the exact number found",
            "- Present results in order of similarity score (highest to lowest)",
            "",
            "🚨 NAME RECOGNITION: When searching for people's names:",
            "- Recognize that nicknames and full names refer to the same person (e.g., 'Jon'/'Jonathan', 'Mike'/'Michael', 'Alex'/'Alexander')",
            "- Common name variations, abbreviations, and nicknames should be counted as matches",
            "- Be flexible with spelling variations and cultural name adaptations",
            "- Don't dismiss results just because the exact spelling or form differs",
            "- Consider initials, surnames only, or first names only as potential matches",
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