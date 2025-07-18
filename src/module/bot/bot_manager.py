"""
Bot Manager for Project Zohar.

This module manages multiple agents and orchestrates their interactions.
It handles agent lifecycle, task delegation, and coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid
import json

from config.settings import get_settings
from .personal_agent import PersonalAgent
from .public_agent import PublicAgent
from ..agent.logging import get_logger

logger = get_logger(__name__)


class AgentType(str, Enum):
    """Types of agents."""
    PERSONAL = "personal"
    PUBLIC = "public"


class AgentStatus(str, Enum):
    """Agent status."""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BotManager:
    """
    Bot Manager that orchestrates multiple agents.
    
    This manager handles:
    - Agent lifecycle management
    - Task delegation and coordination
    - Inter-agent communication
    - Resource management
    - Health monitoring
    """
    
    def __init__(self):
        """Initialize the Bot Manager."""
        self.settings = get_settings()
        
        # Agent storage
        self.agents: Dict[str, Union[PersonalAgent, PublicAgent]] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Task management
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue: List[str] = []
        
        # Manager state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        logger.info("Bot Manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the Bot Manager.
        
        Returns:
            Success status
        """
        try:
            await self.start()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Bot Manager: {e}")
            return False
    
    async def start(self):
        """Start the Bot Manager."""
        try:
            self.is_running = True
            self.start_time = datetime.now()
            
            # Start background tasks
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._task_processor_loop())
            
            logger.info("Bot Manager started")
            
        except Exception as e:
            logger.error(f"Failed to start Bot Manager: {e}")
            raise
    
    async def stop(self):
        """Stop the Bot Manager."""
        try:
            self.is_running = False
            
            # Stop all agents
            for agent_id in list(self.agents.keys()):
                await self.stop_agent(agent_id)
            
            # Cancel all pending tasks
            for task_id in list(self.tasks.keys()):
                if self.tasks[task_id]["status"] == TaskStatus.PENDING:
                    await self.cancel_task(task_id)
            
            logger.info("Bot Manager stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop Bot Manager: {e}")
            raise
    
    async def shutdown(self):
        """
        Shutdown the Bot Manager.
        
        This is an alias for stop() to match the interface expected by other components.
        """
        await self.stop()
    
    async def create_agent(
        self,
        agent_type: AgentType,
        user_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new agent.
        
        Args:
            agent_type: Type of agent to create
            user_id: User ID for personal agents
            config: Agent configuration
            
        Returns:
            Agent ID
        """
        try:
            agent_id = str(uuid.uuid4())
            config = config or {}
            
            # Create agent based on type
            if agent_type == AgentType.PERSONAL:
                if not user_id:
                    raise ValueError("User ID is required for personal agents")
                
                agent = PersonalAgent(
                    user_id=user_id,
                    model_name=config.get("model_name"),
                    temperature=config.get("temperature", 0.7),
                    max_tokens=config.get("max_tokens", 4096),
                )
                
            elif agent_type == AgentType.PUBLIC:
                agent = PublicAgent(
                    agent_id=agent_id,
                    model_name=config.get("model_name"),
                    temperature=config.get("temperature", 0.7),
                    max_tokens=config.get("max_tokens", 4096),
                )
                
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Store agent
            self.agents[agent_id] = agent
            self.agent_status[agent_id] = AgentStatus.INACTIVE
            self.agent_metadata[agent_id] = {
                "type": agent_type,
                "user_id": user_id,
                "config": config,
                "created_at": datetime.now().isoformat(),
                "last_activity": None,
            }
            
            logger.info(f"Created {agent_type} agent with ID {agent_id}")
            return agent_id
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    async def start_agent(self, agent_id: str) -> bool:
        """
        Start an agent.
        
        Args:
            agent_id: Agent ID to start
            
        Returns:
            Success status
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.agents[agent_id]
            
            # Update status
            self.agent_status[agent_id] = AgentStatus.STARTING
            
            # Start agent
            await agent.start()
            
            # Update status and metadata
            self.agent_status[agent_id] = AgentStatus.ACTIVE
            self.agent_metadata[agent_id]["started_at"] = datetime.now().isoformat()
            self.agent_metadata[agent_id]["last_activity"] = datetime.now().isoformat()
            
            logger.info(f"Started agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
            self.agent_status[agent_id] = AgentStatus.ERROR
            return False
    
    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop an agent.
        
        Args:
            agent_id: Agent ID to stop
            
        Returns:
            Success status
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.agents[agent_id]
            
            # Update status
            self.agent_status[agent_id] = AgentStatus.STOPPING
            
            # Stop agent
            await agent.stop()
            
            # Update status and metadata
            self.agent_status[agent_id] = AgentStatus.INACTIVE
            self.agent_metadata[agent_id]["stopped_at"] = datetime.now().isoformat()
            
            logger.info(f"Stopped agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            self.agent_status[agent_id] = AgentStatus.ERROR
            return False
    
    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent.
        
        Args:
            agent_id: Agent ID to remove
            
        Returns:
            Success status
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Stop agent if it's running
            if self.agent_status[agent_id] == AgentStatus.ACTIVE:
                await self.stop_agent(agent_id)
            
            # Remove from storage
            del self.agents[agent_id]
            del self.agent_status[agent_id]
            del self.agent_metadata[agent_id]
            
            logger.info(f"Removed agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id}: {e}")
            return False
    
    async def process_message(
        self,
        agent_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Process a message with a specific agent.
        
        Args:
            agent_id: Agent ID to use
            message: Message to process
            context: Optional context
            session_id: Optional session ID
            
        Returns:
            Agent response
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            if self.agent_status[agent_id] != AgentStatus.ACTIVE:
                raise ValueError(f"Agent {agent_id} is not active")
            
            agent = self.agents[agent_id]
            
            # Process based on agent type
            if isinstance(agent, PersonalAgent):
                response = await agent.process_message(message, context)
            elif isinstance(agent, PublicAgent):
                response = await agent.process_message(message, session_id)
            else:
                raise ValueError(f"Unknown agent type for {agent_id}")
            
            # Update last activity
            self.agent_metadata[agent_id]["last_activity"] = datetime.now().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message with agent {agent_id}: {e}")
            return f"Error: {str(e)}"
    
    async def create_task(
        self,
        task_type: str,
        agent_id: str,
        data: Dict[str, Any],
        priority: int = 1
    ) -> str:
        """
        Create a new task.
        
        Args:
            task_type: Type of task
            agent_id: Agent ID to handle the task
            data: Task data
            priority: Task priority (1-10, higher is more urgent)
            
        Returns:
            Task ID
        """
        try:
            task_id = str(uuid.uuid4())
            
            task = {
                "id": task_id,
                "type": task_type,
                "agent_id": agent_id,
                "data": data,
                "priority": priority,
                "status": TaskStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }
            
            self.tasks[task_id] = task
            
            # Add to queue (sorted by priority)
            self.task_queue.append(task_id)
            self.task_queue.sort(key=lambda x: self.tasks[x]["priority"], reverse=True)
            
            logger.info(f"Created task {task_id} for agent {agent_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            Success status
        """
        try:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
            
            if task["status"] == TaskStatus.COMPLETED:
                return False  # Cannot cancel completed task
            
            # Update status
            task["status"] = TaskStatus.CANCELLED
            task["completed_at"] = datetime.now().isoformat()
            
            # Remove from queue
            if task_id in self.task_queue:
                self.task_queue.remove(task_id)
            
            logger.info(f"Cancelled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent status.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent status information
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.agents[agent_id]
            
            # Get agent-specific status
            if hasattr(agent, 'get_status'):
                agent_status = await agent.get_status()
            else:
                agent_status = {}
            
            return {
                "agent_id": agent_id,
                "status": self.agent_status[agent_id],
                "metadata": self.agent_metadata[agent_id],
                "agent_details": agent_status,
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return {"error": str(e)}
    
    async def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all agents."""
        result = {}
        
        for agent_id in self.agents:
            try:
                result[agent_id] = await self.get_agent_status(agent_id)
            except Exception as e:
                result[agent_id] = {"error": str(e)}
        
        return result
    
    async def get_all_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all agents.
        
        This is an alias for get_all_agents() to match web app expectations.
        """
        return await self.get_all_agents()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status information
        """
        try:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
            
            return self.tasks[task_id]
            
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return {"error": str(e)}
    
    async def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all tasks."""
        return self.tasks.copy()
    
    async def get_manager_status(self) -> Dict[str, Any]:
        """Get Bot Manager status."""
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime": str(datetime.now() - self.start_time) if self.start_time else None,
            "agent_count": len(self.agents),
            "active_agents": len([a for a in self.agent_status.values() if a == AgentStatus.ACTIVE]),
            "task_count": len(self.tasks),
            "pending_tasks": len(self.task_queue),
        }
    
    async def _health_check_loop(self):
        """Background task to check agent health."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for agent_id, agent in self.agents.items():
                    try:
                        # Check if agent is responsive
                        if self.agent_status[agent_id] == AgentStatus.ACTIVE:
                            # Simple health check
                            if hasattr(agent, 'get_status'):
                                await agent.get_status()
                            
                            # Update last activity
                            self.agent_metadata[agent_id]["last_health_check"] = datetime.now().isoformat()
                            
                    except Exception as e:
                        logger.error(f"Health check failed for agent {agent_id}: {e}")
                        self.agent_status[agent_id] = AgentStatus.ERROR
                        
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _task_processor_loop(self):
        """Background task to process the task queue."""
        while self.is_running:
            try:
                await asyncio.sleep(1)  # Check every second
                
                if not self.task_queue:
                    continue
                
                # Get next task
                task_id = self.task_queue.pop(0)
                
                if task_id not in self.tasks:
                    continue
                
                task = self.tasks[task_id]
                
                # Skip if task is no longer pending
                if task["status"] != TaskStatus.PENDING:
                    continue
                
                # Process task
                await self._process_task(task)
                
            except Exception as e:
                logger.error(f"Task processor loop error: {e}")
    
    async def _process_task(self, task: Dict[str, Any]):
        """Process a single task."""
        try:
            task_id = task["id"]
            agent_id = task["agent_id"]
            
            # Update task status
            task["status"] = TaskStatus.IN_PROGRESS
            task["started_at"] = datetime.now().isoformat()
            
            # Check if agent exists and is active
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            if self.agent_status[agent_id] != AgentStatus.ACTIVE:
                raise ValueError(f"Agent {agent_id} is not active")
            
            agent = self.agents[agent_id]
            
            # Process based on task type
            if task["type"] == "process_message":
                result = await agent.process_message(
                    task["data"]["message"],
                    task["data"].get("context")
                )
                
            elif task["type"] == "process_email":
                if isinstance(agent, PersonalAgent):
                    result = await agent.process_email(task["data"])
                else:
                    raise ValueError("Email processing only available for personal agents")
                    
            else:
                raise ValueError(f"Unknown task type: {task['type']}")
            
            # Update task with result
            task["status"] = TaskStatus.COMPLETED
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = result
            
            logger.info(f"Completed task {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to process task {task['id']}: {e}")
            
            # Update task with error
            task["status"] = TaskStatus.FAILED
            task["completed_at"] = datetime.now().isoformat()
            task["error"] = str(e)
    
    async def delegate_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        agent_type: Optional[AgentType] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Delegate a task to an appropriate agent.
        
        Args:
            task_type: Type of task
            data: Task data
            agent_type: Preferred agent type
            user_id: User ID for personal agent tasks
            
        Returns:
            Task ID
        """
        try:
            # Find or create appropriate agent
            agent_id = await self._find_or_create_agent(agent_type, user_id)
            
            # Create task
            task_id = await self.create_task(task_type, agent_id, data)
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to delegate task: {e}")
            raise
    
    async def _find_or_create_agent(
        self,
        agent_type: Optional[AgentType] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Find or create an appropriate agent."""
        # If user_id is provided, look for personal agent
        if user_id:
            for agent_id, metadata in self.agent_metadata.items():
                if (metadata["type"] == AgentType.PERSONAL and 
                    metadata["user_id"] == user_id and 
                    self.agent_status[agent_id] == AgentStatus.ACTIVE):
                    return agent_id
            
            # Create new personal agent
            agent_id = await self.create_agent(AgentType.PERSONAL, user_id)
            await self.start_agent(agent_id)
            return agent_id
        
        # Look for active public agent
        for agent_id, metadata in self.agent_metadata.items():
            if (metadata["type"] == AgentType.PUBLIC and 
                self.agent_status[agent_id] == AgentStatus.ACTIVE):
                return agent_id
        
        # Create new public agent
        agent_id = await self.create_agent(AgentType.PUBLIC)
        await self.start_agent(agent_id)
        return agent_id
    
    async def get_personal_agent(self, user_id: str):
        """
        Get or create a personal agent for the specified user.
        
        Args:
            user_id: User ID
            
        Returns:
            PersonalAgent instance
        """
        try:
            # Look for existing active personal agent for this user
            for agent_id, metadata in self.agent_metadata.items():
                if (metadata["type"] == AgentType.PERSONAL and 
                    metadata["user_id"] == user_id and 
                    self.agent_status[agent_id] == AgentStatus.ACTIVE):
                    return self.agents[agent_id]
            
            # Create new personal agent
            agent_id = await self.create_agent(AgentType.PERSONAL, user_id)
            await self.start_agent(agent_id)
            return self.agents[agent_id]
            
        except Exception as e:
            logger.error(f"Failed to get personal agent for user {user_id}: {e}")
            raise
    
    async def get_public_agent(self):
        """
        Get or create a public agent.
        
        Returns:
            PublicAgent instance
        """
        try:
            # Look for existing active public agent
            for agent_id, metadata in self.agent_metadata.items():
                if (metadata["type"] == AgentType.PUBLIC and 
                    self.agent_status[agent_id] == AgentStatus.ACTIVE):
                    return self.agents[agent_id]
            
            # Create new public agent
            agent_id = await self.create_agent(AgentType.PUBLIC)
            await self.start_agent(agent_id)
            return self.agents[agent_id]
            
        except Exception as e:
            logger.error(f"Failed to get public agent: {e}")
            raise
