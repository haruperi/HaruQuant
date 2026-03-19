"""HaruQuant Risk Engine package.

Portfolio-First Risk Governance for Algorithmic Trading.

This package provides institutional-grade risk management with:
- RiskGovernor: Hard constraints (VaR, ES, margin, concentration)
- RiskBudgetAllocator: Risk parity allocation
- RiskRegimeDetector: Market regime detection (NORMAL vs STRESS)
- PositionSizer: Dynamic position sizing (multiple methods)
- RiskLimits: Configuration for risk parameters
"""

from apps.risk.allocator import RiskBudgetAllocator
from apps.risk.core import PortfolioStateEngine, RiskSnapshotEngine
from apps.risk.governor import RiskGovernor, RiskReport
from apps.risk.models import (
    AccountState,
    MarketState,
    PortfolioState,
    PositionState,
    SymbolState,
)
from apps.risk.position_sizing import (
    PositionSizer,
    estimate_kelly_parameters,
    validate_position_size,
)
from apps.risk.regime import RegimeState, RiskRegimeDetector
from apps.risk.risk_limits import CorrelationPreference, RiskLimits

__all__ = [
    "RiskGovernor",
    "RiskReport",
    "RiskBudgetAllocator",
    "PortfolioStateEngine",
    "RiskSnapshotEngine",
    "RiskRegimeDetector",
    "RegimeState",
    "PositionSizer",
    "RiskLimits",
    "CorrelationPreference",
    "AccountState",
    "PositionState",
    "SymbolState",
    "MarketState",
    "PortfolioState",
    "validate_position_size",
    "estimate_kelly_parameters",
]
