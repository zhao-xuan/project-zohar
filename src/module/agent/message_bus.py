"""
Message Bus for Multi-Agent Communication.

This module implements the message bus that handles communication
between agents in the multi-agent framework.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime
import json
from collections import defaultdict

from zohar.utils.logging import get_logger
from .message_types import Message, MessageType, MessageStatus, MessagePriority

logger = get_logger(__name__)


class MessageHandler:
    """Handler for processing messages."""
    
    def __init__(self, handler_id: str, callback: Callable[[Message], Awaitable[Any]]):
        self.handler_id = handler_id
        self.callback = callback
        self.is_active = True
        self.message_count = 0
        self.last_activity = datetime.now()
    
    async def handle_message(self, message: Message) -> Any:
        """Handle a message."""
        if not self.is_active:
            return None
        
        try:
            self.message_count += 1
            self.last_activity = datetime.now()
            return await self.callback(message)
        except Exception as e:
            logger.error(f"Error in message handler {self.handler_id}: {e}")
            raise


class MessageBus:
    """
    Message bus for inter-agent communication.
    
    Handles message routing, queuing, and delivery between agents.
    """
    
    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}
        self.message_queues: Dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())
        self.broadcast_handlers: List[MessageHandler] = []
        self.message_history: List[Message] = []
        self.max_history_size = 1000
        self.is_running = False
        self.processing_tasks: List[asyncio.Task] = []
        
        logger.info("Message bus initialized")
    
    async def start(self):
        """Start the message bus."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all processing tasks
        for task in self.processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        self.processing_tasks.clear()
        logger.info("Message bus stopped")
    
    def register_handler(
        self,
        handler_id: str,
        callback: Callable[[Message], Awaitable[Any]],
        message_types: Optional[List[MessageType]] = None
    ) -> bool:
        """
        Register a message handler.
        
        Args:
            handler_id: Unique identifier for the handler
            callback: Async function to handle messages
            message_types: Optional list of message types to handle
            
        Returns:
            Success status
        """
        if handler_id in self.handlers:
            logger.warning(f"Handler {handler_id} already registered")
            return False
        
        handler = MessageHandler(handler_id, callback)
        self.handlers[handler_id] = handler
        
        # Start processing task for this handler
        task = asyncio.create_task(self._process_messages_for_handler(handler_id))
        self.processing_tasks.append(task)
        
        logger.info(f"Registered message handler: {handler_id}")
        return True
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister a message handler."""
        if handler_id not in self.handlers:
            return False
        
        handler = self.handlers[handler_id]
        handler.is_active = False
        del self.handlers[handler_id]
        
        logger.info(f"Unregistered message handler: {handler_id}")
        return True
    
    def register_broadcast_handler(
        self,
        handler_id: str,
        callback: Callable[[Message], Awaitable[Any]]
    ) -> bool:
        """Register a broadcast message handler."""
        if handler_id in self.handlers:
            return False
        
        handler = MessageHandler(handler_id, callback)
        self.broadcast_handlers.append(handler)
        self.handlers[handler_id] = handler
        
        logger.info(f"Registered broadcast handler: {handler_id}")
        return True
    
    async def send_message(self, message: Message) -> bool:
        """
        Send a message to a specific recipient.
        
        Args:
            message: Message to send
            
        Returns:
            Success status
        """
        if not self.is_running:
            logger.warning("Message bus not running")
            return False
        
        try:
            # Add to history
            self._add_to_history(message)
            
            # Update message status
            message.status = MessageStatus.PROCESSING
            
            # Route to specific recipient
            if message.recipient_id:
                if message.recipient_id in self.handlers:
                    await self.message_queues[message.recipient_id].put(message)
                    logger.debug(f"Sent message {message.message_id} to {message.recipient_id}")
                else:
                    logger.warning(f"Recipient {message.recipient_id} not found")
                    message.status = MessageStatus.FAILED
                    return False
            
            # Broadcast to all broadcast handlers
            for handler in self.broadcast_handlers:
                if handler.is_active:
                    await self.message_queues[handler.handler_id].put(message)
            
            message.status = MessageStatus.COMPLETED
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            message.status = MessageStatus.FAILED
            return False
    
    async def broadcast_message(self, message: Message) -> bool:
        """
        Broadcast a message to all handlers.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Success status
        """
        if not self.is_running:
            return False
        
        try:
            # Add to history
            self._add_to_history(message)
            
            # Update message status
            message.status = MessageStatus.PROCESSING
            
            # Send to all handlers
            for handler_id in self.handlers:
                await self.message_queues[handler_id].put(message)
            
            message.status = MessageStatus.COMPLETED
            logger.debug(f"Broadcasted message {message.message_id} to {len(self.handlers)} handlers")
            return True
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            message.status = MessageStatus.FAILED
            return False
    
    async def _process_messages_for_handler(self, handler_id: str):
        """Process messages for a specific handler."""
        queue = self.message_queues[handler_id]
        
        while self.is_running and handler_id in self.handlers:
            try:
                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process message
                handler = self.handlers[handler_id]
                if handler.is_active:
                    await handler.handle_message(message)
                
                # Mark as done
                queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message for handler {handler_id}: {e}")
    
    def _add_to_history(self, message: Message):
        """Add message to history."""
        self.message_history.append(message)
        
        # Maintain history size
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)
    
    def get_message_history(
        self,
        handler_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get message history with optional filtering."""
        history = self.message_history
        
        if handler_id:
            history = [msg for msg in history if msg.sender_id == handler_id or msg.recipient_id == handler_id]
        
        if message_type:
            history = [msg for msg in history if msg.message_type == message_type]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_handler_stats(self) -> Dict[str, Any]:
        """Get statistics about message handlers."""
        stats = {}
        
        for handler_id, handler in self.handlers.items():
            stats[handler_id] = {
                "is_active": handler.is_active,
                "message_count": handler.message_count,
                "last_activity": handler.last_activity.isoformat(),
                "queue_size": self.message_queues[handler_id].qsize(),
            }
        
        return stats
    
    def get_bus_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "is_running": self.is_running,
            "total_handlers": len(self.handlers),
            "broadcast_handlers": len(self.broadcast_handlers),
            "message_history_size": len(self.message_history),
            "total_queues": len(self.message_queues),
            "processing_tasks": len(self.processing_tasks),
        }


class MessageBusManager:
    """Manager for the global message bus instance."""
    
    _instance: Optional[MessageBus] = None
    
    @classmethod
    def get_instance(cls) -> MessageBus:
        """Get the global message bus instance."""
        if cls._instance is None:
            cls._instance = MessageBus()
        return cls._instance
    
    @classmethod
    async def start(cls):
        """Start the global message bus."""
        bus = cls.get_instance()
        await bus.start()
    
    @classmethod
    async def stop(cls):
        """Stop the global message bus."""
        if cls._instance:
            await cls._instance.stop()
            cls._instance = None 