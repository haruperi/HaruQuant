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
        from backend.services.live_trading.config import Config

        return Config
    if name == "StateManager":
        from backend.services.live_trading.state_manager import StateManager

        return StateManager
    if name == "BarMonitor":
        from backend.services.live_trading.bar_monitor import BarMonitor

        return BarMonitor
    if name == "SignalProcessor":
        from backend.services.live_trading.signal_processor import SignalProcessor

        return SignalProcessor
    if name == "PositionManager":
        from backend.services.live_trading.position_manager import PositionManager

        return PositionManager
    if name == "SafetyChecker":
        from backend.services.live_trading.safety_checks import SafetyChecker

        return SafetyChecker
    if name == "TradeExecutor":
        from backend.services.live_trading.trade_executor import TradeExecutor

        return TradeExecutor
    if name in {"EmailNotifier", "LiveTradingNotifier"}:
        from backend.services.live_trading.notification_adapter import LiveTradingNotifier

        return LiveTradingNotifier
    if name == "PortfolioManager":
        from backend.services.live_trading.portfolio_manager import PortfolioManager

        return PortfolioManager
    if name == "MultiStrategyEngine":
        from backend.services.live_trading.engine import MultiStrategyEngine

        return MultiStrategyEngine
    if name == "RiskIntegratedEngine":
        from backend.services.live_trading.risk_engine import RiskIntegratedEngine

        return RiskIntegratedEngine
    raise AttributeError(f"module 'apps.live' has no attribute '{name}'")
