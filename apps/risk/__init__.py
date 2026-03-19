"""HaruQuant Risk Engine package.

Portfolio-First Risk Governance for Algorithmic Trading.

This package provides institutional-grade risk management with:
- GovernanceEngine: Hard constraints (VaR, ES, margin, concentration)
- RiskBudgetAllocator: Risk parity allocation
- RiskRegimeDetector / RegimeEngine: Market regime detection and state-aware risk context
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
from apps.risk.regimes import (
    CrisisRegimeDetector,
    LiquidityRegimeDetector,
    MarketRegimeDetector,
    RegimeEngine,
    RegimeReport,
    RegimeSignal,
    RegimeState,
    RegimeTransition,
    RiskRegimeDetector,
    VolatilityRegimeDetector,
    build_regime_transition,
)
from apps.risk.scenarios import (
    ScenarioRegistry,
    ScenarioResult,
    StressScenario,
    build_default_scenario_registry,
    evaluate_scenarios,
)

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
    "RegimeEngine",
    "RegimeReport",
    "RiskRegimeDetector",
    "RegimeState",
    "RegimeSignal",
    "RegimeTransition",
    "CrisisRegimeDetector",
    "MarketRegimeDetector",
    "VolatilityRegimeDetector",
    "LiquidityRegimeDetector",
    "build_regime_transition",
    "PositionSizer",
    "RiskPolicy",
    "RiskLimits",
    "CorrelationPreference",
    "AccountState",
    "PositionState",
    "SymbolState",
    "MarketState",
    "PortfolioState",
    "ScenarioRegistry",
    "ScenarioResult",
    "StressScenario",
    "build_default_scenario_registry",
    "evaluate_scenarios",
    "validate_position_size",
    "estimate_kelly_parameters",
]
