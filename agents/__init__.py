"""Canonical agent package."""

from .agent_registry import AgentDescriptor, AgentRegistry
from .base import AgentBase, AgentRunResult
from .orchestrator import AgentControlPlaneOrchestrator, AgentControlPlaneResult
from .permissions import (
    AgentToolPermissionDecision,
    AgentToolPermissionError,
    AgentToolPermissionService,
)
from .task_manager import (
    AgentTaskManager,
    AgentTaskTransitionError,
    AgentTaskTree,
    ManagedAgentTask,
)
from .runtime import ToolAllowlistDecision, ToolAllowlistMiddleware, ToolPolicyError

__all__ = [
    "AgentBase",
    "AgentControlPlaneOrchestrator",
    "AgentControlPlaneResult",
    "AgentDescriptor",
    "AgentRegistry",
    "AgentRunResult",
    "AgentTaskManager",
    "AgentTaskTransitionError",
    "AgentTaskTree",
    "AgentToolPermissionDecision",
    "AgentToolPermissionError",
    "AgentToolPermissionService",
    "ManagedAgentTask",
    "ToolAllowlistDecision",
    "ToolAllowlistMiddleware",
    "ToolPolicyError",
]
