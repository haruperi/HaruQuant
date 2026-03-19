"""Canonical symbol specification state for risk processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SymbolState:
    """Normalized symbol specification snapshot used by risk math."""

    symbol: str
    contract_size: Optional[float] = None
    tick_value: Optional[float] = None
    tick_size: Optional[float] = None
    volume_min: Optional[float] = None
    volume_max: Optional[float] = None
    volume_step: Optional[float] = None
    currency_base: Optional[str] = None
    currency_profit: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
