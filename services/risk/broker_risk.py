"""Broker and execution-environment risk checks."""

from __future__ import annotations

from typing import Any


def broker_risk_state(market_state: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    spread = float(market_state.get("spread", 0.0))
    slippage = float(market_state.get("slippage", 0.0))
    failures: list[str] = []
    if market_state.get("broker_connection") in {"disconnected", "down"} or market_state.get("broker_anomaly", False):
        failures.append("broker_anomaly")
    if market_state.get("price_feed_stale", False):
        failures.append("stale_price_feed")
    if spread > float(thresholds["max_spread_pips_default"]):
        failures.append("max_spread")
    if slippage > float(thresholds["max_slippage_pips_default"]):
        failures.append("max_slippage")
    return {"spread": spread, "slippage": slippage, "failures": failures}
