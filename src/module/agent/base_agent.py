"""
Base Agent for Multi-Agent Framework.

This module defines the base agent class that all agents in the
multi-agent framework should inherit from.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

from zohar.utils.logging import get_logger
from .agent_types import AgentProfile, AgentCapability, AgentRole
from .message_types import Message, MessageType, MessageFactory
from .message_bus import MessageBusManager

logger = get_logger(__name__)


class BaseAgent:
    """
    Base class for all agents in the multi-agent framework.
    
    This class provides:
    - Message handling capabilities
    - Agent registration and lifecycle management
    - Basic communication patterns
    - Error handling and logging
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        model_name: str,
        role: AgentRole,
        capabilities: List[AgentCapability],
        description: str,
        **kwargs
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            model_name: Name of the model this agent uses
            role: Role of this agent in the system
            capabilities: List of capabilities this agent has
            description: Description of what this agent does
            **kwargs: Additional configuration
        """
        self.agent_id = agent_id
        self.name = name
        self.model_name = model_name
        self.role = role
        self.capabilities = capabilities
        self.description = description
        
        # Agent state
        self.is_active = False
        self.is_initialized = False
        self.start_time: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        
        # Message bus integration
        self.message_bus = MessageBusManager.get_instance()
        self.message_handler_registered = False
        
        # Agent profile
        self.profile = AgentProfile(
            agent_id=agent_id,
            name=name,
            model_name=model_name,
            role=role,
            capabilities=capabilities,
            description=description,
        )
        
        # Configuration
        self.config = kwargs.get('config', {})
        self.max_concurrent_tasks = kwargs.get('max_concurrent_tasks', 5)
        self.task_timeout = kwargs.get('task_timeout', 30.0)
        
        # Task management
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        
        logger.info(f"Base agent initialized: {name} ({agent_id})")
    
    async def initialize(self) -> bool:
        """
        Initialize the agent.
        
        Returns:
            Success status
        """
        try:
            if self.is_initialized:
                return True
            
            # Register with message bus
            await self._register_message_handler()
            
            # Initialize agent-specific components
            await self._initialize_components()
            
            self.is_initialized = True
            logger.info(f"Agent {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {self.name}: {e}")
            return False
    
    async def start(self) -> bool:
        """
        Start the agent.
        
        Returns:
            Success status
        """
        try:
            if self.is_active:
                return True
            
            # Ensure initialization
            if not self.is_initialized:
                success = await self.initialize()
                if not success:
                    return False
            
            self.is_active = True
            self.start_time = datetime.now()
            self.last_activity = datetime.now()
            
            # Start agent-specific processes
            await self._start_processes()
            
            logger.info(f"Agent {self.name} started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the agent.
        
        Returns:
            Success status
        """
        try:
            if not self.is_active:
                return True
            
            self.is_active = False
            
            # Cancel active tasks
            await self._cancel_active_tasks()
            
            # Stop agent-specific processes
            await self._stop_processes()
            
            # Unregister from message bus
            await self._unregister_message_handler()
            
            logger.info(f"Agent {self.name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {self.name}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the agent (alias for stop)."""
        return await self.stop()
    
    async def process_message(self, message: Message) -> Optional[Message]:
        """
        Process an incoming message.
        
        Args:
            message: Message to process
            
        Returns:
            Response message or None
        """
        try:
            self.last_activity = datetime.now()
            self.profile.update_activity()
            
            # Route message based on type
            if message.message_type == MessageType.USER_QUERY:
                return await self._handle_user_query(message)
            elif message.message_type == MessageType.AGENT_REQUEST:
                return await self._handle_agent_request(message)
            elif message.message_type == MessageType.TOOL_REQUEST:
                return await self._handle_tool_request(message)
            elif message.message_type == MessageType.COORDINATION:
                return await self._handle_coordination(message)
            else:
                logger.warning(f"Unknown message type: {message.message_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing message in {self.name}: {e}")
            return MessageFactory.create_error_message(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                error_type="MessageProcessingError",
                error_details=str(e)
            )
    
    async def send_message(self, message: Message) -> bool:
        """
        Send a message through the message bus.
        
        Args:
            message: Message to send
            
        Returns:
            Success status
        """
        try:
            return await self.message_bus.send_message(message)
        except Exception as e:
            logger.error(f"Error sending message from {self.name}: {e}")
            return False
    
    async def broadcast_message(self, message: Message) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Success status
        """
        try:
            return await self.message_bus.broadcast_message(message)
        except Exception as e:
            logger.error(f"Error broadcasting message from {self.name}: {e}")
            return False
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if this agent has a specific capability."""
        return capability in self.capabilities
    
    def can_perform_role(self, role: AgentRole) -> bool:
        """Check if this agent can perform a specific role."""
        return self.role == role
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "is_active": self.is_active,
            "is_initialized": self.is_initialized,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "active_tasks": len(self.active_tasks),
            "model_name": self.model_name,
        }
    
    async def _register_message_handler(self):
        """Register this agent with the message bus."""
        if self.message_handler_registered:
            return
        
        success = self.message_bus.register_handler(
            handler_id=self.agent_id,
            callback=self.process_message
        )
        
        if success:
            self.message_handler_registered = True
            logger.debug(f"Registered message handler for {self.name}")
        else:
            logger.error(f"Failed to register message handler for {self.name}")
    
    async def _unregister_message_handler(self):
        """Unregister this agent from the message bus."""
        if not self.message_handler_registered:
            return
        
        success = self.message_bus.unregister_handler(self.agent_id)
        if success:
            self.message_handler_registered = False
            logger.debug(f"Unregistered message handler for {self.name}")
    
    async def _initialize_components(self):
        """Initialize agent-specific components. Override in subclasses."""
        pass
    
    async def _start_processes(self):
        """Start agent-specific processes. Override in subclasses."""
        pass
    
    async def _stop_processes(self):
        """Stop agent-specific processes. Override in subclasses."""
        pass
    
    async def _cancel_active_tasks(self):
        """Cancel all active tasks."""
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.active_tasks.clear()
    
    async def _handle_user_query(self, message: Message) -> Optional[Message]:
        """Handle a user query. Override in subclasses."""
        logger.warning(f"User query handling not implemented in {self.name}")
        return None
    
    async def _handle_agent_request(self, message: Message) -> Optional[Message]:
        """Handle an agent request. Override in subclasses."""
        logger.warning(f"Agent request handling not implemented in {self.name}")
        return None
    
    async def _handle_tool_request(self, message: Message) -> Optional[Message]:
        """Handle a tool request. Override in subclasses."""
        logger.warning(f"Tool request handling not implemented in {self.name}")
        return None
    
    async def _handle_coordination(self, message: Message) -> Optional[Message]:
        """Handle a coordination message. Override in subclasses."""
        logger.warning(f"Coordination handling not implemented in {self.name}")
        return None
    
    async def _create_task(self, task_func, *args, **kwargs) -> str:
        """Create and track a new task."""
        task_id = str(uuid.uuid4())
        
        async def wrapped_task():
            try:
                result = await task_func(*args, **kwargs)
                self.task_results[task_id] = result
                return result
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self.task_results[task_id] = {"error": str(e)}
                raise
            finally:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
        
        # Check if we can start a new task
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            # Wait for a task to complete
            await asyncio.wait(list(self.active_tasks.values()), return_when=asyncio.FIRST_COMPLETED)
        
        # Create and start the task
        task = asyncio.create_task(wrapped_task())
        self.active_tasks[task_id] = task
        
        return task_id
    
    async def _wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for a task to complete."""
        if task_id not in self.active_tasks:
            return self.task_results.get(task_id)
        
        try:
            if timeout:
                await asyncio.wait_for(self.active_tasks[task_id], timeout=timeout)
            else:
                await self.active_tasks[task_id]
            
            return self.task_results.get(task_id)
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out")
            return {"error": "Task timed out"}
        except Exception as e:
            logger.error(f"Error waiting for task {task_id}: {e}")
            return {"error": str(e)} 