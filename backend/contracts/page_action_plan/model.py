"""PageActionPlan canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope


RiskLevel = Literal["view_only", "local_ui", "backend_safe", "backend_risk"]


class PageActionPlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    description: str | None = None
    risk_level: RiskLevel
    parameters: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(min_length=1)


class PageActionPlan(CanonicalEnvelope):
    """Canonical envelope specialization for UI page actions."""

    contract_type: Literal["PageActionPlan"] = "PageActionPlan"
    payload: PageActionPlanPayload


__all__ = [
    "PageActionPlan",
    "PageActionPlanPayload",
    "RiskLevel",
]
