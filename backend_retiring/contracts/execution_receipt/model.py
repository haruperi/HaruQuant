"""ExecutionReceipt canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


ReceiptStatus = Literal[
    "accepted",
    "queued",
    "partially_filled",
    "filled",
    "cancelled",
    "rejected",
    "expired",
    "failed",
]


class ExecutionReceiptPayload(BaseModel):
    """Payload fields for a normalized broker execution response."""

    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(min_length=1)
    execution_intent_id: str = Field(min_length=1)
    broker: str = Field(min_length=1)
    broker_order_id: str | None = None
    broker_deal_id: str | None = None
    status: ReceiptStatus
    requested_price: float | None = None
    fill_price: float | None = None
    fill_qty: float | None = None
    spread_points: float | None = None
    slippage_points: float | None = None
    slippage_bps: float | None = None
    broker_message: str | None = None
    broker_retcode: str | None = None
    receipt_hash: str = Field(min_length=1)
    authoritative_state: dict[str, Any]


class ExecutionReceipt(CanonicalEnvelope):
    """Canonical envelope specialization for ExecutionReceipt."""

    contract_type: Literal["ExecutionReceipt"] = "ExecutionReceipt"
    payload: ExecutionReceiptPayload


__all__ = [
    "ExecutionReceipt",
    "ExecutionReceiptPayload",
    "Originator",
    "ReceiptStatus",
]
