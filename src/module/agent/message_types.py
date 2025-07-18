"""
Message Types for Multi-Agent Communication.

This module defines the message types and structures used for
communication between agents in the multi-agent framework.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid


class MessageType(Enum):
    """Types of messages in the multi-agent system."""
    USER_QUERY = "user_query"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    COORDINATION = "coordination"
    ERROR = "error"
    STATUS = "status"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    """Message status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Message:
    """Base message class for inter-agent communication."""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    parent_message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "metadata": self.metadata,
            "priority": self.priority.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "parent_message_id": self.parent_message_id,
            "conversation_id": self.conversation_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            priority=MessagePriority(data.get("priority", "normal")),
            status=MessageStatus(data.get("status", "pending")),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            parent_message_id=data.get("parent_message_id"),
            conversation_id=data.get("conversation_id"),
        )


@dataclass
class UserQuery(Message):
    """Message representing a user query."""
    user_id: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.message_type = MessageType.USER_QUERY
        self.content = self.query


@dataclass
class AgentRequest(Message):
    """Message for requesting assistance from another agent."""
    requested_capability: str
    task_description: str
    required_tools: List[str] = field(default_factory=list)
    expected_output_format: Optional[str] = None
    
    def __post_init__(self):
        self.message_type = MessageType.AGENT_REQUEST
        self.content = self.task_description
        self.metadata.update({
            "requested_capability": self.requested_capability,
            "required_tools": self.required_tools,
            "expected_output_format": self.expected_output_format,
        })


@dataclass
class AgentResponse(Message):
    """Message containing an agent's response."""
    result: Any
    confidence: float = 1.0
    tools_used: List[str] = field(default_factory=list)
    execution_time: Optional[float] = None
    
    def __post_init__(self):
        self.message_type = MessageType.AGENT_RESPONSE
        self.content = str(self.result)
        self.metadata.update({
            "confidence": self.confidence,
            "tools_used": self.tools_used,
            "execution_time": self.execution_time,
        })


@dataclass
class ToolRequest(Message):
    """Message for requesting tool execution."""
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    
    def __post_init__(self):
        self.message_type = MessageType.TOOL_REQUEST
        self.content = f"Execute tool: {self.tool_name}"
        self.metadata.update({
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "timeout": self.timeout,
        })


@dataclass
class ToolResult(Message):
    """Message containing tool execution results."""
    tool_name: str
    result: Any
    success: bool = True
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    
    def __post_init__(self):
        self.message_type = MessageType.TOOL_RESULT
        self.content = str(self.result) if self.success else f"Error: {self.error_message}"
        self.metadata.update({
            "tool_name": self.tool_name,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
        })


@dataclass
class CoordinationMessage(Message):
    """Message for coordinating between agents."""
    coordination_type: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.message_type = MessageType.COORDINATION
        self.content = f"{self.coordination_type}: {self.action}"
        self.metadata.update({
            "coordination_type": self.coordination_type,
            "action": self.action,
            "parameters": self.parameters,
        })


@dataclass
class ErrorMessage(Message):
    """Message for reporting errors."""
    error_type: str
    error_details: str
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        self.message_type = MessageType.ERROR
        self.content = f"{self.error_type}: {self.error_details}"
        self.metadata.update({
            "error_type": self.error_type,
            "error_details": self.error_details,
            "stack_trace": self.stack_trace,
        })


class MessageFactory:
    """Factory for creating different types of messages."""
    
    @staticmethod
    def create_user_query(user_id: str, query: str, context: Dict[str, Any] = None) -> UserQuery:
        """Create a user query message."""
        return UserQuery(
            message_id=str(uuid.uuid4()),
            sender_id=user_id,
            user_id=user_id,
            query=query,
            context=context or {},
        )
    
    @staticmethod
    def create_agent_request(
        sender_id: str,
        recipient_id: str,
        requested_capability: str,
        task_description: str,
        required_tools: List[str] = None,
        expected_output_format: str = None
    ) -> AgentRequest:
        """Create an agent request message."""
        return AgentRequest(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            requested_capability=requested_capability,
            task_description=task_description,
            required_tools=required_tools or [],
            expected_output_format=expected_output_format,
        )
    
    @staticmethod
    def create_agent_response(
        sender_id: str,
        recipient_id: str,
        result: Any,
        confidence: float = 1.0,
        tools_used: List[str] = None,
        execution_time: float = None
    ) -> AgentResponse:
        """Create an agent response message."""
        return AgentResponse(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            result=result,
            confidence=confidence,
            tools_used=tools_used or [],
            execution_time=execution_time,
        )
    
    @staticmethod
    def create_tool_request(
        sender_id: str,
        recipient_id: str,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        timeout: float = None
    ) -> ToolRequest:
        """Create a tool request message."""
        return ToolRequest(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            tool_name=tool_name,
            parameters=parameters or {},
            timeout=timeout,
        )
    
    @staticmethod
    def create_tool_result(
        sender_id: str,
        recipient_id: str,
        tool_name: str,
        result: Any,
        success: bool = True,
        error_message: str = None,
        execution_time: float = None
    ) -> ToolResult:
        """Create a tool result message."""
        return ToolResult(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            tool_name=tool_name,
            result=result,
            success=success,
            error_message=error_message,
            execution_time=execution_time,
        )
    
    @staticmethod
    def create_error_message(
        sender_id: str,
        recipient_id: str,
        error_type: str,
        error_details: str,
        stack_trace: str = None
    ) -> ErrorMessage:
        """Create an error message."""
        return ErrorMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            error_type=error_type,
            error_details=error_details,
            stack_trace=stack_trace,
        ) 