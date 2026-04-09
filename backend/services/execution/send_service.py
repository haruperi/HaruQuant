"""Execution send service over the MT5 MCP boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from backend.contracts.execution_intent.model import ExecutionIntent


class BrokerSendGateway(Protocol):
    """Minimal mutating MT5 MCP gateway surface used by the send service."""

    def place_order(self, request: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class BrokerSendResult:
    """Raw broker send result with the submitted payload echo."""

    request_payload: dict[str, Any]
    broker_response: Any


class ExecutionSendService:
    """Submit execution intents through the MT5 MCP mutating tool boundary."""

    def __init__(self, gateway: BrokerSendGateway) -> None:
        self._gateway = gateway

    def send(self, intent: ExecutionIntent) -> BrokerSendResult:
        if intent.payload.broker_action_type != "submit_order":
            raise ValueError("unsupported broker_action_type for send service")

        request_payload = {
            "action": intent.payload.broker_action_type,
            "symbol": intent.payload.symbol,
            "side": intent.payload.side,
            "order_type": intent.payload.order_type,
            "size": dict(intent.payload.size),
            "price_params": dict(intent.payload.price_params),
            "sl_tp_params": dict(intent.payload.sl_tp_params),
            "idempotency_key": intent.payload.idempotency_key,
        }
        broker_response = self._gateway.place_order(request_payload)
        return BrokerSendResult(
            request_payload=request_payload,
            broker_response=broker_response,
        )
