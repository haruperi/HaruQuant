"""Metadata-only tools for Planner Agent."""

from __future__ import annotations

from agents.executive.ceo_agent.internal.planner_agent.tools import (
    get_available_agent_capabilities,
    get_available_departments,
    get_board_escalation_rules,
    get_current_workflow_state,
    get_evidence_requirements,
    get_permission_profile,
    get_refusal_rules,
    get_workflow_requirements,
)


TOOLS = [
    get_available_departments,
    get_available_agent_capabilities,
    get_workflow_requirements,
    get_evidence_requirements,
    get_board_escalation_rules,
    get_refusal_rules,
    get_permission_profile,
    get_current_workflow_state,
]


__all__ = [
    "TOOLS",
    "get_available_agent_capabilities",
    "get_available_departments",
    "get_board_escalation_rules",
    "get_current_workflow_state",
    "get_evidence_requirements",
    "get_permission_profile",
    "get_refusal_rules",
    "get_workflow_requirements",
]
