"""Canonical agent package."""

from __future__ import annotations

import os

from ._shared import AgentBase, AgentRunContext, AgentRunResult
from ._shared.permissions import (
    AgentToolPermissionDecision,
    AgentToolPermissionError,
    AgentToolPermissionService,
)

if os.getenv("HARUQUANT_LIGHT_AGENT_IMPORTS") == "1":
    AgentDescriptor = AgentRegistry = None
    AgentControlPlaneOrchestrator = AgentControlPlaneResult = None
    AgentTaskManager = AgentTaskTransitionError = AgentTaskTree = ManagedAgentTask = None
    CEOAgent = PlannerAgent = None
    ToolAllowlistDecision = ToolAllowlistMiddleware = ToolPolicyError = None
else:
    from .control_plane.agent_registry import AgentDescriptor, AgentRegistry
    from .control_plane.orchestrator import (
        AgentControlPlaneOrchestrator,
        AgentControlPlaneResult,
    )
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
