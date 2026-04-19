"""Deterministic defaults for Hypothesis Designer blueprints."""

from __future__ import annotations

import re
from typing import Any


DEFAULT_SINGLE_ASSET = "SPY"
DEFAULT_TIMEFRAME = "1D"
DEFAULT_PORTFOLIO_ASSETS = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOG", "AVGO", "META", "TSLA", "JPM", "LLY",
    "WMT", "ORCL", "V", "MA", "XOM", "NFLX", "JNJ", "PLTR", "COST",
]


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return text or "strategy-blueprint"


def title_case_idea(idea: str) -> str:
    words = [part for part in re.split(r"[^a-zA-Z0-9]+", idea.strip()) if part]
    preview = " ".join(words[:5]) or "Strategy Blueprint"
    return preview.title()


def infer_strategy_type(candidate: dict[str, Any], source_idea: str) -> str:
    if candidate.get("strategy_type"):
        return str(candidate["strategy_type"])
    lowered = source_idea.lower()
    if any(token in lowered for token in ("hrp", "risk parity", "portfolio", "rebalance", "allocation", "rotation")):
        if "rotation" in lowered:
            return "rotation"
        if "allocation" in lowered:
            return "allocation"
        return "portfolio"
    if any(token in lowered for token in ("decision tree", "classifier", "predict", "forecast", "model", "xgboost", "random forest")):
        return "ml"
    if any(token in lowered for token in ("pair trade", "pairs trading", "cointegration", "spread")):
        return "stat_arb"
    if any(token in lowered for token in ("factor", "value", "quality", "momentum basket")):
        return "factor"
    return "technical"


def default_assets(strategy_type: str) -> list[str]:
    if strategy_type in {"portfolio", "allocation", "rotation"}:
        return list(DEFAULT_PORTFOLIO_ASSETS)
    return [DEFAULT_SINGLE_ASSET]
