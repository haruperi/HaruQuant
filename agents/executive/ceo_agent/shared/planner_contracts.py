"""Internal planner output contracts for CEO validation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PlannerOutput(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"planner-output-{uuid4()}")
    request_id: str
    intent: str
    workflow_type: str
    task_summary: str
    missing_inputs: list[str] = Field(default_factory=list)
    context_needed: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    departments_to_call: list[str] = Field(default_factory=list)
    agents_to_call: list[str] = Field(default_factory=list)
    backend_tools_to_run: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    requires_risk_governor: bool = False
    requires_board_approval: bool = False
    requires_human_confirmation: bool = False
    execution_order: list[str] = Field(default_factory=list)
    final_response_template: str = "executive_memo"
    confidence: str = "medium"
    audit_tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_agent_plan(cls, plan: Any) -> "PlannerOutput":
        data = plan.model_dump() if hasattr(plan, "model_dump") else dict(plan)
        return cls(
            request_id=str(data.get("conversation_plan_id", "planner-request")),
            intent=str(data.get("intent")),
            workflow_type=str(data.get("task_class") or data.get("intent")),
            task_summary=str(data.get("user_goal")),
            missing_inputs=list(data.get("missing_inputs") or []),
            context_needed=list(data.get("context_needed") or []),
            evidence_required=list(data.get("evidence_requirements") or []),
            departments_to_call=_departments_from_agents(list(data.get("allowed_agents") or [])),
            agents_to_call=list(data.get("allowed_agents") or []),
            backend_tools_to_run=list(data.get("backend_tools_to_run") or []),
            risk_level=str(data.get("risk_level", "low")),
            requires_risk_governor=bool(data.get("requires_risk_governor")),
            requires_board_approval=bool(data.get("requires_board_approval")),
            requires_human_confirmation=bool(data.get("requires_board_approval")),
            execution_order=list(data.get("allowed_agents") or []),
            final_response_template=str(data.get("response_mode") or "executive_memo"),
            confidence="high" if data.get("intent") else "low",
            audit_tags=["internal_planner", str(data.get("planner_source", "planner"))],
        )


def _departments_from_agents(agent_names: list[str]) -> list[str]:
    departments: list[str] = []
    mapping = {
        "research": "research",
        "strategy": "strategy_creation",
        "simulation": "simulation",
        "backtest": "simulation",
        "risk": "risk",
        "portfolio": "portfolio",
        "execution": "portfolio",
        "audit": "audit",
        "cost": "portfolio",
        "performance": "portfolio",
        "ceo": "executive",
    }
    for name in agent_names:
        for token, department in mapping.items():
            if token in name:
                departments.append(department)
                break
    return list(dict.fromkeys(departments))
