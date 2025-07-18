"""
Agent Types for Multi-Agent Framework.

This module defines the different types of agents that can participate
in the multi-agent collaboration system.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


class AgentCapability(Enum):
    """Agent capabilities."""
    REASONING = "reasoning"
    TOOL_CALLING = "tool_calling"
    MEMORY = "memory"
    PRIVACY = "privacy"
    SEARCH = "search"
    CODE_EXECUTION = "code_execution"
    MATH = "math"
    WEATHER = "weather"
    RESEARCH = "research"


class AgentRole(Enum):
    """Agent roles in multi-agent system."""
    COORDINATOR = "coordinator"
    REASONER = "reasoner"
    TOOL_EXECUTOR = "tool_executor"
    MEMORY_MANAGER = "memory_manager"
    PRIVACY_GUARDIAN = "privacy_guardian"
    RESEARCHER = "researcher"
    CALCULATOR = "calculator"
    CODER = "coder"


@dataclass
class AgentProfile:
    """Profile of an agent in the multi-agent system."""
    agent_id: str
    name: str
    model_name: str
    role: AgentRole
    capabilities: list[AgentCapability]
    description: str
    is_active: bool = True
    created_at: datetime = None
    last_activity: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model_name": self.model_name,
            "role": self.role.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentProfile':
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            model_name=data["model_name"],
            role=AgentRole(data["role"]),
            capabilities=[AgentCapability(cap) for cap in data["capabilities"]],
            description=data["description"],
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
        )
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities
    
    def can_perform_role(self, role: AgentRole) -> bool:
        """Check if agent can perform a specific role."""
        return self.role == role
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


class AgentRegistry:
    """Registry for managing agent profiles."""
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
    
    def register_agent(self, profile: AgentProfile) -> bool:
        """Register an agent profile."""
        if profile.agent_id in self.agents:
            return False
        
        self.agents[profile.agent_id] = profile
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent profile."""
        if agent_id not in self.agents:
            return False
        
        del self.agents[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get an agent profile by ID."""
        return self.agents.get(agent_id)
    
    def get_agents_by_role(self, role: AgentRole) -> list[AgentProfile]:
        """Get all agents with a specific role."""
        return [agent for agent in self.agents.values() if agent.role == role]
    
    def get_agents_by_capability(self, capability: AgentCapability) -> list[AgentProfile]:
        """Get all agents with a specific capability."""
        return [agent for agent in self.agents.values() if agent.has_capability(capability)]
    
    def get_active_agents(self) -> list[AgentProfile]:
        """Get all active agents."""
        return [agent for agent in self.agents.values() if agent.is_active]
    
    def list_agents(self) -> list[AgentProfile]:
        """List all agents."""
        return list(self.agents.values()) 