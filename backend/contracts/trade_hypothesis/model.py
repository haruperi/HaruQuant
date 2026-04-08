"""TradeHypothesis canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


Direction = Literal["buy", "sell"]
HoldingHorizon = Literal["intraday", "swing", "position"]


class EvidenceItem(BaseModel):
    """Minimal typed evidence item referenced by a trade hypothesis."""

    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(min_length=1)
    ref_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    freshness_class: str | None = None


class TradeHypothesisPayload(BaseModel):
    """Payload fields for a non-executable trade hypothesis."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: Direction
    thesis: str = Field(min_length=1)
    entry_rationale: str = Field(min_length=1)
    invalidation_rationale: str = Field(min_length=1)
    stop_loss_logic: dict[str, Any]
    take_profit_logic: dict[str, Any] | None = None
    holding_horizon: HoldingHorizon
    confidence: float = Field(ge=0.0, le=1.0)
    calibration_note: str = Field(min_length=1)
    evidence: list[EvidenceItem]
    required_validation_data: list[str] = Field(default_factory=list)
    strategy_family: str = Field(min_length=1)
    feature_version: str = Field(min_length=1)
    strategy_code_hash: str = Field(min_length=1)


class TradeHypothesis(CanonicalEnvelope):
    """Canonical envelope specialization for TradeHypothesis."""

    contract_type: Literal["TradeHypothesis"] = "TradeHypothesis"
    payload: TradeHypothesisPayload


__all__ = [
    "Direction",
    "EvidenceItem",
    "HoldingHorizon",
    "Originator",
    "TradeHypothesis",
    "TradeHypothesisPayload",
]
