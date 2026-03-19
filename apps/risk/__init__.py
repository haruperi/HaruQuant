"""HaruQuant Risk Engine package.

Portfolio-First Risk Governance for Algorithmic Trading.

This package provides institutional-grade risk management with:
- GovernanceEngine: Hard constraints (VaR, ES, margin, concentration)
- RiskBudgetAllocator: Risk parity allocation
- RiskRegimeDetector: Market regime detection (NORMAL vs STRESS)
- PositionSizer: Dynamic position sizing (multiple methods)
- RiskLimits: Configuration for risk parameters
"""

from apps.risk.allocator import RiskBudgetAllocator
from apps.risk.core import (
    GovernanceEngine,
    GovernanceReport,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    RiskSnapshotEngine,
)
from apps.risk.limits import (
    BudgetUtilization,
    CircuitBreakerState,
    CorrelationPreference,
    GovernanceState,
    LimitEvent,
    OverrideRecord,
    PolicyDecision,
    PolicyEngine,
    RiskLimits,
    RiskPolicy,
)
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

__all__ = [
    "PolicyEngine",
    "PolicyDecision",
    "LimitEvent",
    "GovernanceState",
    "OverrideRecord",
    "BudgetUtilization",
    "CircuitBreakerState",
    "GovernanceEngine",
    "GovernanceReport",
    "PortfolioRiskEngine",
    "RiskBudgetAllocator",
    "PortfolioStateEngine",
    "RiskSnapshotEngine",
    "RiskRegimeDetector",
    "RegimeState",
    "PositionSizer",
    "RiskPolicy",
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
