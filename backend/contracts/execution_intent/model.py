"""ExecutionIntent canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


BrokerActionType = Literal["submit_order", "modify_order", "cancel_order", "close_position"]
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]


class ExecutionIntentPayload(BaseModel):
    """Payload fields for an approved broker action request."""

    model_config = ConfigDict(extra="forbid")

    execution_intent_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    risk_decision_id: str = Field(min_length=1)
    broker_action_type: BrokerActionType
    symbol: str = Field(min_length=1)
    side: Side
    size: dict[str, Any]
    order_type: OrderType
    price_params: dict[str, Any] = Field(default_factory=dict)
    sl_tp_params: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    expiry_time: datetime
    pre_send_validation_snapshot_ref: str = Field(min_length=1)


class ExecutionIntent(CanonicalEnvelope):
    """Canonical envelope specialization for ExecutionIntent."""

    contract_type: Literal["ExecutionIntent"] = "ExecutionIntent"
    payload: ExecutionIntentPayload


__all__ = [
    "BrokerActionType",
    "ExecutionIntent",
    "ExecutionIntentPayload",
    "OrderType",
    "Originator",
    "Side",
]
