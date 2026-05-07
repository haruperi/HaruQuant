"""Canonical position state for risk processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PositionState:
    """Normalized active position data used by the risk subsystem."""

    symbol: str
    lots: float
    side: str = "LONG"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_id: Optional[str] = None
    cluster: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
