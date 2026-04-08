"""EvaluationReport canonical contract models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator
from typing import Literal


Verdict = Literal["pass", "warning", "fail"]


class EvaluationReportPayload(BaseModel):
    """Payload fields for a workflow or step evaluation result."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    rubric_name: str = Field(min_length=1)
    rubric_scores: dict[str, float]
    overall_score: float
    verdict: Verdict
    issues: list[str] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)
    evaluator_identity: str = Field(min_length=1)
    evaluation_model_id: str = Field(min_length=1)


class EvaluationReport(CanonicalEnvelope):
    """Canonical envelope specialization for EvaluationReport."""

    contract_type: Literal["EvaluationReport"] = "EvaluationReport"
    payload: EvaluationReportPayload


__all__ = [
    "EvaluationReport",
    "EvaluationReportPayload",
    "Originator",
    "Verdict",
]
