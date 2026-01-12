"""
Base Engine.

Abstract base class for all backtest engines.
Defines common interface and shared functionality.
"""

import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from apps.logger import logger
from apps.strategy import BaseStrategy

from ..result import BacktestResult, EquityPoint, TradeRecord


class BaseEngine(ABC):
    """
    Abstract base class for backtest engines.

    Defines the contract that all engines must implement and provides
    common functionality for configuration, validation, and result tracking.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 0.0,
        slippage_points: float = 0.0,
        slippage_config: Optional[Dict[str, Any]] = None,
        spread_config: Optional[Dict[str, Any]] = None,
        leverage: int = 100,
        backtest_start_date: Optional[datetime] = None,
        backtest_end_date: Optional[datetime] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base engine.

        Args:
            strategy: Strategy instance to backtest
            data: OHLCV DataFrame with DatetimeIndex
            initial_balance: Starting account balance
            commission: Commission per trade (in account currency)
            slippage_points: Slippage in points per trade (legacy, use slippage_config)
            slippage_config: Slippage configuration dict with keys:
                - type: "fixed" or "variable"
                - fixed: Fixed slippage value
                - min: Minimum slippage for variable mode
                - max: Maximum slippage for variable mode
            spread_config: Spread configuration dict with keys:
                - type: "use-broker", "fixed", or "variable"
                - fixed: Fixed spread value
                - min: Minimum spread for variable mode
                - max: Maximum spread for variable mode
            leverage: Account leverage (e.g., 100 for 1:100)
            backtest_start_date: Start date for backtest execution (trades before this are ignored)
            backtest_end_date: End date for backtest execution (trades after this are ignored)
            config: Additional configuration
        """
        self.strategy = strategy
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage_points = slippage_points
        self.slippage_config = slippage_config or {
            "type": "fixed",
            "fixed": slippage_points,
            "min": 0.0,
            "max": 0.0001,
        }
        self.spread_config = spread_config or {
            "type": "use-broker",
            "fixed": 0.0002,
            "min": 0.0001,
            "max": 0.0005,
        }
        self.leverage = leverage
        self.config = config or {}

        # Fractional volume support (for crypto, fractional shares)
        # When True, position sizes are not rounded to lot_step
        self.allow_fractional_volumes = self.config.get(
            "allow_fractional_volumes", False
        )

        # Backtest date range (defaults to data range if not specified)
        self.backtest_start_date = backtest_start_date or data.index[0]
        self.backtest_end_date = backtest_end_date or data.index[-1]

        # Convert to datetime if needed
        if isinstance(self.backtest_start_date, pd.Timestamp):
            self.backtest_start_date = self.backtest_start_date.to_pydatetime()
        if isinstance(self.backtest_end_date, pd.Timestamp):
            self.backtest_end_date = self.backtest_end_date.to_pydatetime()

        # Validate data
        self._validate_data()

        # Result tracking
        self.result: Optional[BacktestResult] = None
        self._trade_records: list[TradeRecord] = []
        self._equity_points: list[EquityPoint] = []
        self._peak_equity = initial_balance

        # Margin tracking
        self._used_margin = 0.0

        # State
        self._running = False
        self._current_bar_index = 0

    def calculate_required_margin(
        self, position_size: float, entry_price: float, contract_size: float
    ) -> float:
        """
        Calculate required margin for a position.

        Margin = (position_size * contract_size * entry_price) / leverage

        Args:
            position_size: Position size in lots
            entry_price: Entry price of the position
            contract_size: Contract size (e.g., 100000 for forex)

        Returns:
            Required margin in account currency
        """
        position_value = position_size * contract_size * entry_price
        required_margin = position_value / self.leverage
        return required_margin

    def get_free_margin(self, current_balance: float) -> float:
        """
        Calculate free margin available for new positions.

        Args:
            current_balance: Current account balance

        Returns:
            Free margin available
        """
        return current_balance - self._used_margin

    def has_sufficient_margin(
        self,
        position_size: float,
        entry_price: float,
        contract_size: float,
        current_balance: float,
    ) -> bool:
        """
        Check if there's sufficient margin for a new position.

        Args:
            position_size: Proposed position size
            entry_price: Entry price
            contract_size: Contract size
            current_balance: Current account balance

        Returns:
            True if sufficient margin available
        """
        required = self.calculate_required_margin(
            position_size, entry_price, contract_size
        )
        free = self.get_free_margin(current_balance)
        return free >= required

    def get_slippage(self) -> float:
        """
        Get slippage value based on configuration.

        For fixed mode, returns the fixed slippage value.
        For variable mode, returns a random value between min and max.

        Returns:
            Slippage value in points
        """
        if self.slippage_config.get("type") == "variable":
            min_slip = float(self.slippage_config.get("min", 0.0))
            max_slip = float(self.slippage_config.get("max", 0.0001))
            return random.uniform(min_slip, max_slip)
        else:
            return float(self.slippage_config.get("fixed", self.slippage_points))

    def get_spread(self, bar: Optional[pd.Series] = None) -> float:
        """
        Get spread value based on configuration.

        For use-broker mode, returns the spread from the bar's "spread" column.
        For fixed mode, returns the fixed spread value.
        For variable mode, returns a random value between min and max.

        Args:
            bar: Current bar data (required for use-broker mode)

        Returns:
            Spread value in points
        """
        spread_type = str(self.spread_config.get("type", "use-broker"))

        if spread_type == "use-broker":
            # Try to get spread from bar data
            if bar is not None and "spread" in bar.index:
                spread_value = bar.get("spread", 0.0)
                if pd.notna(spread_value):
                    return float(spread_value)
            # Fallback to fixed if no spread in data
            return float(self.spread_config.get("fixed", 0.0002))
        elif spread_type == "variable":
            min_spread = float(self.spread_config.get("min", 0.0001))
            max_spread = float(self.spread_config.get("max", 0.0005))
            return random.uniform(min_spread, max_spread)
        else:  # fixed
            return float(self.spread_config.get("fixed", 0.0002))

    def _validate_data(self) -> None:
        """
        Validate input data.

        Raises:
            ValueError: If data is invalid
        """
        if self.data.empty:
            raise ValueError("Data cannot be empty")

        required_columns = ["open", "high", "low", "close"]
        missing = [col for col in required_columns if col not in self.data.columns]

        if missing:
            raise ValueError(f"Data missing required columns: {missing}")

        if not isinstance(self.data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex")

        if self.data.index.duplicated().any():
            raise ValueError("Data index contains duplicates")

        if not self.data.index.is_monotonic_increasing:
            raise ValueError("Data index must be sorted in ascending order")

        logger.debug(f"Data validation passed: {len(self.data)} bars")

    def _record_equity_point(
        self, timestamp: datetime, balance: float, equity: float
    ) -> None:
        """
        Record an equity curve point.

        Args:
            timestamp: Current timestamp
            balance: Current balance
            equity: Current equity
        """
        # Update peak
        if equity > self._peak_equity:
            self._peak_equity = equity

        # Calculate drawdown
        drawdown = self._peak_equity - equity
        drawdown_percent = (
            (drawdown / self._peak_equity * 100) if self._peak_equity > 0 else 0.0
        )

        point = EquityPoint(
            timestamp=timestamp,
            balance=balance,
            equity=equity,
            drawdown=drawdown,
            drawdown_percent=drawdown_percent,
        )

        self._equity_points.append(point)

    def _record_trade(self, trade: TradeRecord) -> None:
        """
        Record a completed trade.

        Args:
            trade: TradeRecord instance
        """
        self._trade_records.append(trade)
        logger.debug(
            f"Trade recorded: {trade.type} {trade.symbol}, P&L: {trade.profit_loss:.2f}"
        )

    def _build_result(
        self, final_balance: float, final_equity: float
    ) -> BacktestResult:
        """
        Build final backtest result.

        Args:
            final_balance: Final account balance
            final_equity: Final account equity

        Returns:
            BacktestResult instance
        """
        result = BacktestResult(
            strategy_name=self.strategy.__class__.__name__,
            symbol=self.strategy.symbol,
            timeframe=self.config.get("timeframe", "unknown"),
            start_date=self.data.index[0].to_pydatetime(),
            end_date=self.data.index[-1].to_pydatetime(),
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            final_equity=final_equity,
            backtest_mode=self.get_backtest_mode(),
            data_step_mode=self.config.get("data_step_mode", "trading_timeframe"),
            trades=self._trade_records,
            equity_curve=self._equity_points,
            metadata=self.config,
        )

        return result

    @abstractmethod
    def get_backtest_mode(self) -> str:
        """
        Return the backtest mode identifier.

        Returns:
            "event_driven" or "vectorized"
        """
        pass

    @abstractmethod
    def run(self) -> BacktestResult:
        """
        Run the backtest.

        This is the main entry point for executing the backtest.
        Must be implemented by subclasses.

        Returns:
            BacktestResult with complete backtest data

        Raises:
            RuntimeError: If backtest fails
        """
        pass

    def __repr__(self) -> str:
        """Return human-readable representation."""
        return (
            f"{self.__class__.__name__}("
            f"{self.strategy.__class__.__name__}, "
            f"{len(self.data)} bars, "
            f"balance=${self.initial_balance})"
        )
