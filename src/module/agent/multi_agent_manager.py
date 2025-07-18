"""
Multi-Agent Manager for Project Zohar.

This module implements the main manager that orchestrates the multi-agent system,
allowing DeepSeek models to collaborate with tool-supporting models.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

from zohar.utils.logging import get_logger
from zohar.config.settings import get_settings
from .agent_types import AgentProfile, AgentCapability, AgentRole
from .message_types import Message, MessageType, MessageFactory, UserQuery
from .message_bus import MessageBusManager
from .coordinator_agent import CoordinatorAgent
from .tool_executor_agent import ToolExecutorAgent

logger = get_logger(__name__)


class MultiAgentManager:
    """
    Main manager for the multi-agent system.
    
    This manager:
    - Initializes and manages all agents
    - Handles user queries and routes them appropriately
    - Coordinates between DeepSeek and tool-supporting models
    - Provides a unified interface for the rest of the system
    """
    
    def __init__(self):
        """Initialize the multi-agent manager."""
        self.settings = get_settings()
        
        # Message bus
        self.message_bus = MessageBusManager.get_instance()
        
        # Agent storage
        self.agents: Dict[str, Any] = {}
        self.agent_profiles: Dict[str, AgentProfile] = {}
        
        # System state
        self.is_initialized = False
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        # Configuration
        self.coordinator_id = "coordinator_001"
        self.tool_executor_id = "tool_executor_001"
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0,
            "last_query_time": None
        }
        
        logger.info("Multi-agent manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the multi-agent system.
        
        Returns:
            Success status
        """
        try:
            if self.is_initialized:
                return True
            
            logger.info("Initializing multi-agent system...")
            
            # Start message bus
            await MessageBusManager.start()
            
            # Create coordinator agent
            coordinator = CoordinatorAgent(
                agent_id=self.coordinator_id,
                model_name=self.settings.default_model
            )
            
            # Create tool executor agent
            tool_executor = ToolExecutorAgent(
                agent_id=self.tool_executor_id,
                model_name="llama3.2:latest"  # Use tool-supporting model
            )
            
            # Start agents
            await coordinator.start()
            await tool_executor.start()
            
            # Register agents
            self.agents[self.coordinator_id] = coordinator
            self.agents[self.tool_executor_id] = tool_executor
            
            # Register agent profiles with coordinator
            coordinator.register_agent(coordinator.profile)
            coordinator.register_agent(tool_executor.profile)
            
            # Store agent profiles
            self.agent_profiles[self.coordinator_id] = coordinator.profile
            self.agent_profiles[self.tool_executor_id] = tool_executor.profile
            
            self.is_initialized = True
            logger.info("Multi-agent system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize multi-agent system: {e}")
            return False
    
    async def start(self) -> bool:
        """
        Start the multi-agent system.
        
        Returns:
            Success status
        """
        try:
            if self.is_running:
                return True
            
            # Ensure initialization
            if not self.is_initialized:
                success = await self.initialize()
                if not success:
                    return False
            
            self.is_running = True
            self.start_time = datetime.now()
            
            logger.info("Multi-agent system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start multi-agent system: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the multi-agent system.
        
        Returns:
            Success status
        """
        try:
            if not self.is_running:
                return True
            
            self.is_running = False
            
            # Stop all agents
            for agent_id, agent in self.agents.items():
                try:
                    await agent.stop()
                except Exception as e:
                    logger.error(f"Error stopping agent {agent_id}: {e}")
            
            # Stop message bus
            await MessageBusManager.stop()
            
            logger.info("Multi-agent system stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop multi-agent system: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the multi-agent system (alias for stop)."""
        return await self.stop()
    
    async def process_user_query(
        self, 
        user_id: str, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user query through the multi-agent system.
        
        Args:
            user_id: User identifier
            query: User's query
            context: Optional context information
            
        Returns:
            Response from the multi-agent system
        """
        try:
            if not self.is_running:
                return "Multi-agent system is not running. Please start the system first."
            
            start_time = time.time()
            self.stats["total_queries"] += 1
            self.stats["last_query_time"] = datetime.now().isoformat()
            
            logger.info(f"Processing user query: {query[:100]}...")
            
            # Create user query message
            user_message = MessageFactory.create_user_query(
                user_id=user_id,
                query=query,
                context=context or {}
            )
            
            # Send to coordinator
            coordinator = self.agents.get(self.coordinator_id)
            if not coordinator:
                return "Error: Coordinator agent not available"
            
            # Process through coordinator
            response = await coordinator.process_message(user_message)
            
            if response and response.message_type == MessageType.AGENT_RESPONSE:
                self.stats["successful_queries"] += 1
                response_time = time.time() - start_time
                
                # Update average response time
                total_queries = self.stats["successful_queries"]
                current_avg = self.stats["average_response_time"]
                self.stats["average_response_time"] = (
                    (current_avg * (total_queries - 1) + response_time) / total_queries
                )
                
                logger.info(f"Query processed successfully in {response_time:.2f}s")
                return response.content
            
            else:
                self.stats["failed_queries"] += 1
                error_msg = "Error: Failed to process query"
                if response and response.message_type == MessageType.ERROR:
                    error_msg = f"Error: {response.content}"
                
                logger.error(f"Query processing failed: {error_msg}")
                return error_msg
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            logger.error(f"Error processing user query: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def add_agent(
        self,
        agent_id: str,
        name: str,
        model_name: str,
        role: AgentRole,
        capabilities: List[AgentCapability],
        description: str,
        agent_instance: Optional[Any] = None
    ) -> bool:
        """
        Add a new agent to the system.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name
            model_name: Model name the agent uses
            role: Agent role
            capabilities: List of agent capabilities
            description: Agent description
            agent_instance: Optional agent instance (if None, will create one)
            
        Returns:
            Success status
        """
        try:
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already exists")
                return False
            
            # Create agent profile
            profile = AgentProfile(
                agent_id=agent_id,
                name=name,
                model_name=model_name,
                role=role,
                capabilities=capabilities,
                description=description
            )
            
            # If no agent instance provided, we would create one here
            # For now, we'll just register the profile
            if agent_instance:
                self.agents[agent_id] = agent_instance
                await agent_instance.start()
            else:
                logger.warning(f"No agent instance provided for {agent_id}")
                return False
            
            # Register with coordinator
            coordinator = self.agents.get(self.coordinator_id)
            if coordinator:
                coordinator.register_agent(profile)
            
            # Store profile
            self.agent_profiles[agent_id] = profile
            
            logger.info(f"Added agent: {name} ({agent_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding agent {agent_id}: {e}")
            return False
    
    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the system.
        
        Args:
            agent_id: Agent identifier to remove
            
        Returns:
            Success status
        """
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Stop agent
            agent = self.agents[agent_id]
            await agent.stop()
            
            # Remove from storage
            del self.agents[agent_id]
            if agent_id in self.agent_profiles:
                del self.agent_profiles[agent_id]
            
            # Unregister from coordinator
            coordinator = self.agents.get(self.coordinator_id)
            if coordinator:
                coordinator.unregister_agent(agent_id)
            
            logger.info(f"Removed agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing agent {agent_id}: {e}")
            return False
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        profile = self.agent_profiles.get(agent_id)
        
        status = agent.get_status()
        if profile:
            status["profile"] = profile.to_dict()
        
        return status
    
    def get_all_agents_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents."""
        result = {}
        for agent_id in self.agents:
            result[agent_id] = self.get_agent_status(agent_id)
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        coordinator = self.agents.get(self.coordinator_id)
        
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_agents": len(self.agents),
            "active_agents": len([a for a in self.agents.values() if a.is_active]),
            "statistics": self.stats,
            "coordinator_status": coordinator.get_conversation_status() if coordinator else {},
            "message_bus_stats": self.message_bus.get_bus_stats()
        }
    
    def get_available_capabilities(self) -> List[str]:
        """Get list of all available capabilities in the system."""
        capabilities = set()
        for profile in self.agent_profiles.values():
            capabilities.update([cap.value for cap in profile.capabilities])
        return list(capabilities)
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[AgentProfile]:
        """Get all agents with a specific capability."""
        return [
            profile for profile in self.agent_profiles.values()
            if profile.has_capability(capability)
        ]
    
    def get_agents_by_role(self, role: AgentRole) -> List[AgentProfile]:
        """Get all agents with a specific role."""
        return [
            profile for profile in self.agent_profiles.values()
            if profile.role == role
        ]
    
    async def broadcast_message(self, message: Message) -> bool:
        """Broadcast a message to all agents."""
        try:
            return await self.message_bus.broadcast_message(message)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return False
    
    async def send_message_to_agent(self, agent_id: str, message: Message) -> bool:
        """Send a message to a specific agent."""
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            agent = self.agents[agent_id]
            response = await agent.process_message(message)
            
            # Handle response if needed
            if response:
                logger.debug(f"Agent {agent_id} responded: {response.message_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to agent {agent_id}: {e}")
            return False
    
    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get message history with optional filtering."""
        return self.message_bus.get_message_history(
            handler_id=agent_id,
            message_type=message_type,
            limit=limit
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the system."""
        total_queries = self.stats["total_queries"]
        successful_queries = self.stats["successful_queries"]
        
        success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": self.stats["failed_queries"],
            "success_rate": f"{success_rate:.1f}%",
            "average_response_time": f"{self.stats['average_response_time']:.2f}s",
            "last_query_time": self.stats["last_query_time"],
            "uptime": (
                (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else 0
            )
        }


# Global instance
_multi_agent_manager: Optional[MultiAgentManager] = None


def get_multi_agent_manager() -> MultiAgentManager:
    """Get the global multi-agent manager instance."""
    global _multi_agent_manager
    if _multi_agent_manager is None:
        _multi_agent_manager = MultiAgentManager()
    return _multi_agent_manager


async def initialize_multi_agent_system() -> bool:
    """Initialize the global multi-agent system."""
    manager = get_multi_agent_manager()
    return await manager.initialize()


async def start_multi_agent_system() -> bool:
    """Start the global multi-agent system."""
    manager = get_multi_agent_manager()
    return await manager.start()


async def stop_multi_agent_system() -> bool:
    """Stop the global multi-agent system."""
    manager = get_multi_agent_manager()
    return await manager.stop()


async def process_query(user_id: str, query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Process a user query through the multi-agent system."""
    manager = get_multi_agent_manager()
    return await manager.process_user_query(user_id, query, context) 