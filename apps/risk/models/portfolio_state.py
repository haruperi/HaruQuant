"""Canonical portfolio state for risk processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apps.risk.models.account_state import AccountState
from apps.risk.models.market_state import MarketState
from apps.risk.models.position_state import PositionState
from apps.risk.models.symbol_state import SymbolState
from apps.risk.limits import RiskLimits
from apps.risk.validators.common import ValidationSummary


@dataclass(frozen=True)
class PortfolioState:
    """Validated point-in-time portfolio snapshot used by risk modules."""

    account: AccountState
    positions: List[PositionState]
    symbols: Dict[str, SymbolState]
    markets: Dict[str, MarketState]
    limits: Optional[RiskLimits] = None
    symbol_to_cluster: Dict[str, str] = field(default_factory=dict)
    validation_summary: ValidationSummary = field(default_factory=ValidationSummary)
    exposures: Dict[str, float] = field(default_factory=dict)
    as_of: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def active_symbols(self) -> List[str]:
        return [position.symbol for position in self.positions]

    @property
    def position_map(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for position in self.positions:
            symbol = str(position.symbol)
            totals[symbol] = float(totals.get(symbol, 0.0) + float(position.lots))
        return totals
