"""
Coordinator Agent for Multi-Agent Framework.

This module implements the coordinator agent that manages the multi-agent system,
delegates tasks to appropriate agents, and synthesizes results.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

from zohar.utils.logging import get_logger
from zohar.config.settings import get_settings
from .base_agent import BaseAgent
from .agent_types import AgentRole, AgentCapability, AgentRegistry
from .message_types import (
    Message, MessageType, MessageFactory, 
    UserQuery, AgentRequest, AgentResponse, ToolRequest, ToolResult
)

logger = get_logger(__name__)


class CoordinatorAgent(BaseAgent):
    """
    Coordinator agent that manages the multi-agent system.
    
    This agent:
    - Receives user queries and analyzes them
    - Determines which agents are needed for the task
    - Delegates subtasks to appropriate agents
    - Synthesizes results from multiple agents
    - Manages the overall conversation flow
    """
    
    def __init__(self, agent_id: str, model_name: str = None, **kwargs):
        """Initialize the coordinator agent."""
        self.settings = get_settings()
        
        super().__init__(
            agent_id=agent_id,
            name="Coordinator",
            model_name=model_name or self.settings.default_model,
            role=AgentRole.COORDINATOR,
            capabilities=[
                AgentCapability.REASONING,
                AgentCapability.MEMORY,
                AgentCapability.PRIVACY,
            ],
            description="Coordinates multi-agent tasks and synthesizes results",
            **kwargs
        )
        
        # Agent registry
        self.agent_registry = AgentRegistry()
        
        # Task management
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        self.conversation_history: Dict[str, List[Message]] = {}
        
        # Model for reasoning
        self.model = self._initialize_model()
        
        logger.info(f"Coordinator agent initialized with model: {self.model_name}")
    
    def _initialize_model(self):
        """Initialize the model for reasoning."""
        try:
            from camel.models import ModelFactory
            from camel.types import ModelPlatformType
            
            # Use Ollama for local models
            return ModelFactory.create(
                model_platform=ModelPlatformType.OLLAMA,
                model_type=self.model_name,
                url="http://localhost:11434/v1",
                model_config_dict={
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return None
    
    async def _initialize_components(self):
        """Initialize coordinator-specific components."""
        # Initialize agent registry
        # This will be populated as agents register themselves
        
        # Start conversation cleanup task
        asyncio.create_task(self._cleanup_old_conversations())
        
        logger.info("Coordinator components initialized")
    
    async def _start_processes(self):
        """Start coordinator-specific processes."""
        # Start monitoring task
        asyncio.create_task(self._monitor_agent_health())
        
        logger.info("Coordinator processes started")
    
    async def _stop_processes(self):
        """Stop coordinator-specific processes."""
        # Cancel monitoring tasks
        pass
    
    async def _handle_user_query(self, message: Message) -> Optional[Message]:
        """Handle a user query by coordinating with other agents."""
        try:
            user_query = message.content
            conversation_id = message.conversation_id or str(uuid.uuid4())
            
            logger.info(f"Processing user query: {user_query[:100]}...")
            
            # Analyze the query to determine required capabilities
            required_capabilities = await self._analyze_query_requirements(user_query)
            
            # Find appropriate agents
            available_agents = self._find_agents_for_capabilities(required_capabilities)
            
            if not available_agents:
                return MessageFactory.create_error_message(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    error_type="NoAgentsAvailable",
                    error_details="No agents available with required capabilities"
                )
            
            # Create conversation context
            conversation_context = {
                "user_query": user_query,
                "required_capabilities": required_capabilities,
                "selected_agents": [agent.agent_id for agent in available_agents],
                "start_time": datetime.now(),
                "status": "processing"
            }
            
            self.active_conversations[conversation_id] = conversation_context
            self.conversation_history[conversation_id] = []
            
            # Delegate tasks to agents
            agent_responses = await self._delegate_tasks_to_agents(
                conversation_id, user_query, available_agents
            )
            
            # Synthesize results
            final_response = await self._synthesize_results(
                conversation_id, user_query, agent_responses
            )
            
            # Update conversation status
            conversation_context["status"] = "completed"
            conversation_context["end_time"] = datetime.now()
            
            # Create response message
            response = MessageFactory.create_agent_response(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                result=final_response,
                confidence=0.9,
                tools_used=[agent.name for agent in available_agents]
            )
            response.conversation_id = conversation_id
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling user query: {e}")
            return MessageFactory.create_error_message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                error_type="QueryProcessingError",
                error_details=str(e)
            )
    
    async def _handle_agent_request(self, message: Message) -> Optional[Message]:
        """Handle requests from other agents."""
        try:
            # Extract request details
            requested_capability = message.metadata.get("requested_capability")
            task_description = message.content
            
            # Find agents with the requested capability
            available_agents = self.agent_registry.get_agents_by_capability(
                AgentCapability(requested_capability)
            )
            
            if not available_agents:
                return MessageFactory.create_error_message(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    error_type="NoAgentsAvailable",
                    error_details=f"No agents available with capability: {requested_capability}"
                )
            
            # Select the best agent (for now, just pick the first one)
            selected_agent = available_agents[0]
            
            # Forward the request to the selected agent
            agent_request = MessageFactory.create_agent_request(
                sender_id=self.agent_id,
                recipient_id=selected_agent.agent_id,
                requested_capability=requested_capability,
                task_description=task_description,
                required_tools=message.metadata.get("required_tools", [])
            )
            
            success = await self.send_message(agent_request)
            if not success:
                return MessageFactory.create_error_message(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    error_type="MessageDeliveryError",
                    error_details="Failed to forward request to agent"
                )
            
            return MessageFactory.create_agent_response(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                result=f"Request forwarded to {selected_agent.name}",
                confidence=1.0
            )
            
        except Exception as e:
            logger.error(f"Error handling agent request: {e}")
            return MessageFactory.create_error_message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                error_type="AgentRequestError",
                error_details=str(e)
            )
    
    async def _analyze_query_requirements(self, query: str) -> List[AgentCapability]:
        """Analyze a query to determine required agent capabilities."""
        required_capabilities = []
        
        # Simple keyword-based analysis
        query_lower = query.lower()
        
        # Math operations
        if any(word in query_lower for word in ["calculate", "math", "equation", "formula", "+", "-", "*", "/"]):
            required_capabilities.append(AgentCapability.MATH)
        
        # Code execution
        if any(word in query_lower for word in ["code", "program", "script", "execute", "run"]):
            required_capabilities.append(AgentCapability.CODE_EXECUTION)
        
        # Web search
        if any(word in query_lower for word in ["search", "find", "lookup", "information", "news"]):
            required_capabilities.append(AgentCapability.SEARCH)
        
        # Weather
        if any(word in query_lower for word in ["weather", "temperature", "forecast", "climate"]):
            required_capabilities.append(AgentCapability.WEATHER)
        
        # Research
        if any(word in query_lower for word in ["research", "analyze", "study", "investigate"]):
            required_capabilities.append(AgentCapability.RESEARCH)
        
        # Always include reasoning capability
        required_capabilities.append(AgentCapability.REASONING)
        
        return list(set(required_capabilities))  # Remove duplicates
    
    def _find_agents_for_capabilities(self, capabilities: List[AgentCapability]) -> List[Any]:
        """Find agents that can handle the required capabilities."""
        available_agents = []
        
        for capability in capabilities:
            agents = self.agent_registry.get_agents_by_capability(capability)
            available_agents.extend(agents)
        
        # Remove duplicates and inactive agents
        unique_agents = {}
        for agent in available_agents:
            if agent.is_active and agent.agent_id not in unique_agents:
                unique_agents[agent.agent_id] = agent
        
        return list(unique_agents.values())
    
    async def _delegate_tasks_to_agents(
        self, 
        conversation_id: str, 
        user_query: str, 
        agents: List[Any]
    ) -> Dict[str, Any]:
        """Delegate tasks to appropriate agents."""
        agent_responses = {}
        
        # Create tasks for each agent
        tasks = []
        for agent in agents:
            task = self._create_task(
                self._request_agent_assistance,
                conversation_id,
                user_query,
                agent
            )
            tasks.append((agent.agent_id, task))
        
        # Wait for all tasks to complete
        for agent_id, task_id in tasks:
            try:
                result = await self._wait_for_task(task_id, timeout=30.0)
                agent_responses[agent_id] = result
            except Exception as e:
                logger.error(f"Task for agent {agent_id} failed: {e}")
                agent_responses[agent_id] = {"error": str(e)}
        
        return agent_responses
    
    async def _request_agent_assistance(
        self, 
        conversation_id: str, 
        user_query: str, 
        agent: Any
    ) -> Dict[str, Any]:
        """Request assistance from a specific agent."""
        try:
            # Create agent request
            request = MessageFactory.create_agent_request(
                sender_id=self.agent_id,
                recipient_id=agent.agent_id,
                requested_capability="general_assistance",
                task_description=user_query,
                required_tools=[]
            )
            request.conversation_id = conversation_id
            
            # Send request
            success = await self.send_message(request)
            if not success:
                return {"error": "Failed to send request to agent"}
            
            # For now, return a placeholder response
            # In a full implementation, we would wait for the agent's response
            return {
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "response": f"Agent {agent.name} is processing the request",
                "status": "processing"
            }
            
        except Exception as e:
            logger.error(f"Error requesting assistance from {agent.name}: {e}")
            return {"error": str(e)}
    
    async def _synthesize_results(
        self, 
        conversation_id: str, 
        user_query: str, 
        agent_responses: Dict[str, Any]
    ) -> str:
        """Synthesize results from multiple agents."""
        try:
            # Build synthesis prompt
            synthesis_prompt = f"""
            User Query: {user_query}
            
            Agent Responses:
            """
            
            for agent_id, response in agent_responses.items():
                if isinstance(response, dict) and "error" not in response:
                    synthesis_prompt += f"\n- Agent {agent_id}: {response.get('response', 'No response')}"
                else:
                    synthesis_prompt += f"\n- Agent {agent_id}: Error - {response.get('error', 'Unknown error')}"
            
            synthesis_prompt += """
            
            Please synthesize these responses into a coherent, helpful answer for the user.
            Focus on the most relevant information and provide a clear, concise response.
            """
            
            # Use the model to synthesize results
            if self.model:
                from camel.messages import BaseMessage
                messages = [BaseMessage.make_user_message(role_name="User", content=synthesis_prompt)]
                
                try:
                    response = self.model.run(messages)
                    return response.msg.content
                except Exception as e:
                    logger.error(f"Model synthesis failed: {e}")
            
            # Fallback synthesis
            return self._fallback_synthesis(user_query, agent_responses)
            
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def _fallback_synthesis(self, user_query: str, agent_responses: Dict[str, Any]) -> str:
        """Fallback synthesis when model is not available."""
        successful_responses = []
        
        for agent_id, response in agent_responses.items():
            if isinstance(response, dict) and "error" not in response:
                successful_responses.append(f"Agent {agent_id}: {response.get('response', 'No response')}")
        
        if successful_responses:
            return f"Based on the responses from {len(successful_responses)} agents:\n\n" + "\n\n".join(successful_responses)
        else:
            return "I apologize, but I was unable to get responses from any agents to help with your query."
    
    async def _monitor_agent_health(self):
        """Monitor the health of registered agents."""
        while self.is_active:
            try:
                # Check agent status
                active_agents = self.agent_registry.get_active_agents()
                
                for agent in active_agents:
                    # Check if agent has been inactive for too long
                    if agent.last_activity:
                        time_since_activity = (datetime.now() - agent.last_activity).total_seconds()
                        if time_since_activity > 300:  # 5 minutes
                            logger.warning(f"Agent {agent.name} has been inactive for {time_since_activity:.0f} seconds")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in agent health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_conversations(self):
        """Clean up old conversation data."""
        while self.is_active:
            try:
                current_time = datetime.now()
                
                # Remove conversations older than 1 hour
                conversations_to_remove = []
                for conv_id, context in self.active_conversations.items():
                    if context.get("status") == "completed":
                        end_time = context.get("end_time")
                        if end_time and (current_time - end_time).total_seconds() > 3600:
                            conversations_to_remove.append(conv_id)
                
                for conv_id in conversations_to_remove:
                    del self.active_conversations[conv_id]
                    if conv_id in self.conversation_history:
                        del self.conversation_history[conv_id]
                
                if conversations_to_remove:
                    logger.info(f"Cleaned up {len(conversations_to_remove)} old conversations")
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in conversation cleanup: {e}")
                await asyncio.sleep(300)
    
    def register_agent(self, agent_profile: Any) -> bool:
        """Register an agent with the coordinator."""
        return self.agent_registry.register_agent(agent_profile)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the coordinator."""
        return self.agent_registry.unregister_agent(agent_id)
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all registered agents."""
        agents = self.agent_registry.list_agents()
        return {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if a.is_active]),
            "agents": [agent.to_dict() for agent in agents]
        }
    
    def get_conversation_status(self) -> Dict[str, Any]:
        """Get status of active conversations."""
        return {
            "active_conversations": len(self.active_conversations),
            "conversations": [
                {
                    "conversation_id": conv_id,
                    "status": context["status"],
                    "start_time": context["start_time"].isoformat(),
                    "agents": context.get("selected_agents", [])
                }
                for conv_id, context in self.active_conversations.items()
            ]
        } 