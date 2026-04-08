"""TradeProposal canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


Direction = Literal["buy", "sell"]
ReadinessState = Literal["draft", "validated", "ready_for_risk", "rejected"]


class TradeProposalPayload(BaseModel):
    """Payload fields for a validated trade proposal moving toward risk review."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    source_hypothesis_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: Direction
    candidate_price_logic: dict[str, Any]
    proposed_size: dict[str, Any]
    operating_envelope: dict[str, Any]
    session_restrictions: dict[str, Any] = Field(default_factory=dict)
    expiry_at: datetime
    transformation_version: str = Field(min_length=1)
    readiness_state: ReadinessState


class TradeProposal(CanonicalEnvelope):
    """Canonical envelope specialization for TradeProposal."""

    contract_type: Literal["TradeProposal"] = "TradeProposal"
    payload: TradeProposalPayload


__all__ = [
    "Direction",
    "Originator",
    "ReadinessState",
    "TradeProposal",
    "TradeProposalPayload",
]
