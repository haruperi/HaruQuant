"""Broker truth fetch helpers for reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.mcp.mt5_mcp import MT5ReadOnlyTools

_BROKER_CLIENT_ID_FIELDS: tuple[str, ...] = (
    "client_order_id",
    "external_id",
    "comment",
)


def _matches_client_order_id(payload: dict[str, Any], client_order_id: str) -> bool:
    target = client_order_id.strip()
    if not target:
        return False
    for field_name in _BROKER_CLIENT_ID_FIELDS:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip() == target:
            return True
    return False


@dataclass(frozen=True)
class BrokerTruthSnapshot:
    client_order_id: str
    account_state: dict[str, Any]
    matched_order: dict[str, Any] | None
    matched_position: dict[str, Any] | None


class BrokerTruthFetcher:
    """Fetches current broker truth for a pending client order reference."""

    def __init__(self, read_tools: MT5ReadOnlyTools) -> None:
        self._read_tools = read_tools

    def fetch_for_client_order_id(
        self,
        client_order_id: str,
        *,
        account_state: dict[str, Any] | None = None,
    ) -> BrokerTruthSnapshot:
        resolved_account_state = account_state or self._read_tools.get_account_info()
        matched_order = next(
            (
                order
                for order in self._read_tools.list_orders()
                if _matches_client_order_id(order, client_order_id)
            ),
            None,
        )
        matched_position = next(
            (
                position
                for position in self._read_tools.list_positions()
                if _matches_client_order_id(position, client_order_id)
            ),
            None,
        )
        return BrokerTruthSnapshot(
            client_order_id=client_order_id,
            account_state=resolved_account_state,
            matched_order=matched_order,
            matched_position=matched_position,
        )
