"""RefinementReport canonical contract model.

Output contract for the refinement/evaluation stage of the AI trading
workflow. Contains comparative analysis across multiple strategy
configurations and a verdict on baseline viability.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope


class FinalVerdict(BaseModel):
    """Overall verdict on strategy viability."""

    model_config = ConfigDict(extra="allow")

    viable_baseline: bool = False
    average_excess_return_vs_bh: str = ""
    proceed_to_ml: bool = False
    key_weaknesses: list[str] = Field(default_factory=list)
    next_tests: list[str] = Field(default_factory=list)
    rationale: str = ""


class RefinementReportPayload(BaseModel):
    """Payload for a refinement/evaluation report.

    Uses flexible dict types for analysis sections since LLM output
    varies in structure. Only the final verdict is strictly typed.
    """

    model_config = ConfigDict(extra="allow")

    threshold_comparison: dict[str, Any] = Field(default_factory=dict)
    ma_filter_impact: dict[str, Any] = Field(default_factory=dict)
    cross_market_robustness: dict[str, Any] = Field(default_factory=dict)
    strategy_vs_buy_hold: dict[str, Any] = Field(default_factory=dict)
    conclusion: FinalVerdict = Field(default_factory=FinalVerdict)


class RefinementReport(CanonicalEnvelope):
    """Canonical envelope for a refinement/evaluation report."""

    contract_type: Literal["RefinementReport"] = "RefinementReport"
    payload: RefinementReportPayload
