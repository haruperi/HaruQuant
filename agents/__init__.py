"""Canonical agent package."""

from ._shared import AgentBase, AgentRunContext, AgentRunResult
from ._shared.permissions import (
    AgentToolPermissionDecision,
    AgentToolPermissionError,
    AgentToolPermissionService,
)
from .control_plane.agent_registry import AgentDescriptor, AgentRegistry
from .control_plane.orchestrator import AgentControlPlaneOrchestrator, AgentControlPlaneResult
from .control_plane.task_manager import (
    AgentTaskManager,
    AgentTaskTransitionError,
    AgentTaskTree,
    ManagedAgentTask,
)
from .executive.ceo_agent import CEOAgent
from .executive.planner_agent import PlannerAgent
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
