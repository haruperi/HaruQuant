"""Shared deterministic risk calculators."""

from __future__ import annotations

from typing import Any


def stop_loss_distance(proposal: dict[str, Any]) -> float:
    price = float(proposal.get("requested_price", proposal.get("price", 0.0)) or 0.0)
    stop = proposal.get("stop_loss")
    if stop is None:
        return 0.0
    return abs(price - float(stop))


def pip_value(symbol: str, volume: float) -> float:
    return max(0.0, float(volume)) * (10.0 if symbol.endswith("USD") or symbol.startswith("USD") else 1.0)


def proposed_trade_risk(proposal: dict[str, Any], account_equity: float) -> float:
    expected = proposal.get("expected_risk", {})
    if isinstance(expected, dict) and "amount" in expected:
        risk_amount = float(expected["amount"])
    else:
        distance = stop_loss_distance(proposal)
        risk_amount = distance * pip_value(str(proposal.get("symbol", "")), float(proposal.get("requested_volume", proposal.get("requested_size", 0.0)) or 0.0))
    return risk_amount / max(float(account_equity), 1.0)


def notional_exposure(proposal: dict[str, Any]) -> float:
    volume = float(proposal.get("requested_volume", proposal.get("requested_size", 0.0)) or 0.0)
    price = float(proposal.get("requested_price", proposal.get("price", 1.0)) or 1.0)
    contract_size = float(proposal.get("contract_size", 100000.0))
    return abs(volume * price * contract_size)


def risk_reward_value(proposal: dict[str, Any]) -> float:
    entry = float(proposal.get("requested_price", proposal.get("price", 0.0)) or 0.0)
    stop = proposal.get("stop_loss")
    target = proposal.get("take_profit")
    if stop is None or target is None:
        return 0.0
    risk = abs(entry - float(stop))
    reward = abs(float(target) - entry)
    return reward / risk if risk else 0.0
