"""Canonical account state for risk processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AccountState:
    """Normalized account inputs used by the risk subsystem."""

    equity: float
    balance: Optional[float] = None
    free_margin: Optional[float] = None
    margin_used: Optional[float] = None
    currency: Optional[str] = None
    account_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
