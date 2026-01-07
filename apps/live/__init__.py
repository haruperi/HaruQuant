"""Live Trading Module.

This module provides automated live trading capabilities with signal detection,
trade execution, safety checks, and monitoring.

Unified engine supporting single or multiple strategies with portfolio management:
- MultiStrategyEngine: Unified engine for one or more strategies
  - Supports dynamic strategy type loading (TrendFollowing, CloseBreakout, custom)
  - Portfolio-level risk management
  - Correlation checks
  - Dashboard monitoring
"""

from apps.live.bar_monitor import BarMonitor
from apps.live.config import Config
from apps.live.engine import MultiStrategyEngine
from apps.live.notification_adapter import LiveTradingNotifier
from apps.live.portfolio_manager import PortfolioManager
from apps.live.position_manager import PositionManager
from apps.live.safety_checks import SafetyChecker
from apps.live.signal_processor import SignalProcessor
from apps.live.state_manager import StateManager
from apps.live.trade_executor import TradeExecutor

# For backward compatibility
EmailNotifier = LiveTradingNotifier

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
]
