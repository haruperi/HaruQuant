"""Canonical agent package."""

from .agent_registry import AgentDescriptor, AgentRegistry
from .base import AgentBase, AgentRunContext, AgentRunResult
from .ceo import CEOAgent
from .orchestrator import AgentControlPlaneOrchestrator, AgentControlPlaneResult
from .planner import PlannerAgent
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
    "AgentRunContext",
    "AgentTaskManager",
    "AgentTaskTransitionError",
    "AgentTaskTree",
    "AgentToolPermissionDecision",
    "AgentToolPermissionError",
    "AgentToolPermissionService",
    "CEOAgent",
    "ManagedAgentTask",
    "PlannerAgent",
    "ToolAllowlistDecision",
    "ToolAllowlistMiddleware",
    "ToolPolicyError",
]
