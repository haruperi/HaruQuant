"""Live Trading Module.

This module provides automated live trading capabilities with signal detection,
trade execution, safety checks, and monitoring.

Unified engine supporting single or multiple strategies with portfolio management:
- MultiStrategyEngine: Unified engine for one or more strategies
  - Supports dynamic strategy type loading (TrendFollowing, CloseBreakout, custom)
  - Portfolio-level risk management
  - Correlation checks
  - Dashboard monitoring
- RiskIntegratedEngine: Advanced engine with institutional-grade risk management
  - Dynamic position sizing (fixed_risk, Kelly, volatility, etc.)
  - Regime detection (NORMAL vs STRESS)
  - Risk budget allocation (risk parity)
  - Hard risk constraints (VaR, ES, margin, concentration)
  - Cluster limits per asset class
"""

__all__ = [
    "Config",
    "StateManager",
    "BarMonitor",
    "SignalProcessor",
    "PositionManager",
    "SafetyChecker",
    "TradeExecutor",
    "EmailNotifier",
    "LiveTradingNotifier",
    "PortfolioManager",
    "MultiStrategyEngine",
    "RiskIntegratedEngine",
]


def __getattr__(name: str):
    # Lazy imports avoid heavy dependency loading during config-only workflows/tests.
    if name == "Config":
        from apps.live.config import Config

        return Config
    if name == "StateManager":
        from apps.live.state_manager import StateManager

        return StateManager
    if name == "BarMonitor":
        from apps.live.bar_monitor import BarMonitor

        return BarMonitor
    if name == "SignalProcessor":
        from apps.live.signal_processor import SignalProcessor

        return SignalProcessor
    if name == "PositionManager":
        from apps.live.position_manager import PositionManager

        return PositionManager
    if name == "SafetyChecker":
        from apps.live.safety_checks import SafetyChecker

        return SafetyChecker
    if name == "TradeExecutor":
        from apps.live.trade_executor import TradeExecutor

        return TradeExecutor
    if name in {"EmailNotifier", "LiveTradingNotifier"}:
        from apps.live.notification_adapter import LiveTradingNotifier

        return LiveTradingNotifier
    if name == "PortfolioManager":
        from apps.live.portfolio_manager import PortfolioManager

        return PortfolioManager
    if name == "MultiStrategyEngine":
        from apps.live.engine import MultiStrategyEngine

        return MultiStrategyEngine
    if name == "RiskIntegratedEngine":
        from apps.live.risk_engine import RiskIntegratedEngine

        return RiskIntegratedEngine
    raise AttributeError(f"module 'apps.live' has no attribute '{name}'")
