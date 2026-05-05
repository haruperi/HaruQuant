"""cTrader bridge preparation with normalized metadata and fail-closed mutations."""

from __future__ import annotations

from typing import Any

from execution.mt5_bridge import MT5Bridge


class CTraderBridge(MT5Bridge):
    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        info = super().get_symbol_info(symbol)
        return {
            **info,
            "bridge": "ctrader",
            "normalized_symbol": symbol.upper(),
            "normalized_pip_value": info["pip_size"],
            "normalized_tick_value": info["tick_size"],
        }

    def normalize_order_status(self, status: str) -> str:
        return {"FILLED": "filled", "PARTIAL": "partial", "REJECTED": "rejected"}.get(status.upper(), status.lower())

    def normalize_position_status(self, status: str) -> str:
        return {"OPEN": "open", "CLOSED": "closed"}.get(status.upper(), status.lower())

    def _audit(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = super()._audit(action, payload)
        result["bridge"] = "ctrader"
        return result


__all__ = ["CTraderBridge"]
