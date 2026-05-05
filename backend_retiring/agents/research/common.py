"""Shared helpers for read-only research department agents."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any
from uuid import uuid4

from backend_retiring.agents.schemas import EvidenceRef, ResearchReport

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_MEMORY_ROOT = PROJECT_ROOT / "memory" / "evidence"


def normalize_ohlcv(raw: Any) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    if raw is None:
        return rows
    records: Any
    if hasattr(raw, "to_dict"):
        records = raw.to_dict(orient="records")
    else:
        records = raw
    if not isinstance(records, list):
        return rows
    for item in records:
        if not isinstance(item, dict):
            continue
        try:
            close = float(item.get("close"))
            high = float(item.get("high", close))
            low = float(item.get("low", close))
            open_ = float(item.get("open", close))
        except (TypeError, ValueError):
            continue
        rows.append({"open": open_, "high": high, "low": low, "close": close})
    return rows


def close_prices(rows: list[dict[str, float]]) -> list[float]:
    return [row["close"] for row in rows]


def pct_returns(prices: list[float]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(prices, prices[1:]):
        if previous:
            returns.append((current - previous) / previous)
    return returns


def infer_trend(prices: list[float]) -> str:
    if len(prices) < 5:
        return "unknown"
    change = (prices[-1] - prices[0]) / prices[0] if prices[0] else 0.0
    if change > 0.01:
        return "trending_up"
    if change < -0.01:
        return "trending_down"
    return "ranging"


def infer_volatility_regime(returns: list[float]) -> str:
    if len(returns) < 5:
        return "unknown"
    volatility = pstdev(returns)
    if volatility >= 0.015:
        return "high"
    if volatility <= 0.003:
        return "low"
    return "normal"


def simple_rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(prices[-period - 1 :], prices[-period:]):
        change = current - previous
        if change >= 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def save_research_report(report: ResearchReport) -> EvidenceRef:
    EVIDENCE_MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{report.report_id}.json"
    path = EVIDENCE_MEMORY_ROOT / filename
    payload = report.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return EvidenceRef(
        evidence_id=report.report_id,
        evidence_type="research_report",
        uri=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        summary=f"{report.source_agent} research report",
        source_agent=report.source_agent,
    )


def new_report_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


__all__ = [
    "close_prices",
    "infer_trend",
    "infer_volatility_regime",
    "new_report_id",
    "normalize_ohlcv",
    "pct_returns",
    "save_research_report",
    "simple_rsi",
]
