"""Metadata-only tools for the internal Planner Agent."""

from __future__ import annotations

from agents.executive.ceo_agent.shared.evidence_requirements import WORKFLOW_EVIDENCE_REQUIREMENTS, required_evidence_for
from agents.executive.ceo_agent.shared.escalation_rules import BOARD_ESCALATION_TERMS
from agents.executive.ceo_agent.shared.permission_profiles import PLANNER_AGENT_PERMISSIONS
from agents.executive.ceo_agent.shared.refusal_rules import REFUSAL_RULES
from agents.executive.ceo_agent.shared.routing import KNOWN_EXECUTIVE_WORKFLOWS


def get_available_departments() -> list[str]:
    return ["research", "strategy_creation", "simulation", "risk", "portfolio", "audit", "executive"]


def get_available_agent_capabilities() -> dict[str, list[str]]:
    return {
        "ceo": ["synthesize", "delegate", "escalate", "refuse"],
        "planner": ["classify_intent", "identify_missing_inputs", "select_workflow_type"],
    }


def get_workflow_requirements(workflow_type: str) -> dict:
    return {"workflow_type": workflow_type, "evidence": required_evidence_for(workflow_type)}


def get_evidence_requirements() -> dict[str, list[str]]:
    return WORKFLOW_EVIDENCE_REQUIREMENTS


def get_board_escalation_rules() -> dict:
    return BOARD_ESCALATION_TERMS


def get_refusal_rules() -> dict:
    return REFUSAL_RULES


def get_permission_profile() -> dict:
    return PLANNER_AGENT_PERMISSIONS


def get_current_workflow_state() -> dict:
    return {"state": "planning", "known_workflows": sorted(KNOWN_EXECUTIVE_WORKFLOWS)}


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
