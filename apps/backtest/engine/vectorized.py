"""
Vectorized Backtest Engine.

Fast bulk evaluation for research and parameter optimization.
Trades accuracy for speed - uses simplified execution model.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from apps.logger import logger
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict

from ..result import BacktestResult, TradeRecord
from .base import BaseEngine


class VectorizedEngine(BaseEngine):
    """
    Vectorized Backtest Engine.

    Characteristics:
    - Processes entire DataFrame at once
    - Uses vectorized pandas/numpy operations
    - Simplified execution model (close-based)
    - No intra-bar SL/TP checking
    - Fast but less accurate

    Trade-offs:
    - 10-100x faster than event-driven
    - Close-based entry/exit (no high/low consideration)
    - Simplified position tracking
    - No mark-to-market updates

    Use for:
    - Research and experimentation
    - Parameter optimization
    - Initial strategy testing
    - High-level strategy comparison

    NOT for:
    - Final strategy validation
    - Pre-live testing
    - Precise execution modeling
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
        timeframe: str = "H1",
        config: Optional[Dict[str, Any]] = None,
        position_sizer: Optional[Any] = None,
        mt5_client: Optional[Any] = None,
    ):
        """
        Initialize vectorized engine.

        Args:
            strategy: Strategy to backtest
            data: OHLCV DataFrame
            initial_balance: Starting balance
            commission: Commission per trade
            slippage_points: Slippage in points (legacy)
            slippage_config: Slippage configuration dict
            spread_config: Spread configuration dict
            leverage: Account leverage
            timeframe: Bar timeframe
            config: Additional config
            position_sizer: Optional PositionSizer for dynamic position sizing
            mt5_client: Optional MT5Client for fetching real symbol info (swap rates, etc.)
        """
        config = config or {}
        config["timeframe"] = timeframe

        super().__init__(
            strategy,
            data,
            initial_balance,
            commission,
            slippage_points,
            slippage_config,
            spread_config,
            leverage,
            backtest_start_date,
            backtest_end_date,
            config,
        )

        self.timeframe = timeframe
        self.position_sizer = position_sizer

        # Initialize SymbolProvider for accurate pip calculations
        # Use provided MT5 client if available, otherwise use defaults
        from apps.trading.symbol_info import BacktestSymbolProvider

        # Use the passed mt5_client if provided
        self._symbol_provider = BacktestSymbolProvider(
            mt5_client=mt5_client, symbol_name=strategy.symbol or "EURUSD"
        )

        # But & Hold Baseline
        self._first_trade_open: Optional[float] = None
        self._first_trade_size: Optional[float] = None

    def _get_contract_size(self) -> float:
        """Get contract size from symbol provider."""
        try:
            return float(self._symbol_provider.get_contract_size())
        except Exception:
            return 100000.0  # Default forex contract size

    def _get_point(self) -> float:
        """Get point value from symbol provider."""
        try:
            return float(self._symbol_provider.get_point())
        except Exception:
            return 0.00001  # Default forex 5-digit point

    def _calculate_commission(self, volume: float) -> float:
        """
        Calculate commission for a trade based on volume.

        Commission is per lot, so total commission = commission_per_lot * volume.
        For example, if commission is $7 per lot and volume is 0.1 lots,
        the commission will be $0.70.

        Args:
            volume: Position size in lots

        Returns:
            Total commission in account currency (negative value representing cost)
        """
        return -self.commission * volume

    def _count_swap_days(
        self, entry_time: datetime, exit_time: datetime, triple_swap_day_mt5: int = 3
    ) -> int:
        """
        Count the number of swap charges between entry and exit time.

        Swap is charged at midnight rollover on trading days (Mon-Fri only).
        Weekends (Sat/Sun) and major holidays are excluded since forex market is closed.
        To be charged swap for a day, you must hold the position THROUGH
        that day's midnight (into the next day).
        The last day (exit day) doesn't count because you exit before the next midnight.

        Example: Trade from Dec 10 Wed 20:00 to Dec 17 Wed 09:00
        - Dec 10 Wed night -> Dec 11: charged 3x (triple swap)
        - Dec 11 Thu night -> Dec 12: charged 1x
        - Dec 12 Fri night -> Dec 13: charged 1x
        - Dec 13 Sat night -> Dec 14: NOT charged (weekend)
        - Dec 14 Sun night -> Dec 15: NOT charged (weekend)
        - Dec 15 Mon night -> Dec 16: charged 1x
        - Dec 16 Tue night -> Dec 17: charged 1x
        - Dec 17 Wed: NOT charged (exit day, didn't hold through midnight)
        Total: 3 + 1 + 1 + 1 + 1 = 7 swap charges

        Args:
            entry_time: Position entry timestamp
            exit_time: Position exit timestamp
            triple_swap_day_mt5: Day of week with triple swap in MT5 format
                                 (0=Sunday, 1=Monday, ..., 6=Saturday)
                                 Default is 3 (Wednesday)

        Returns:
            Total swap days (including triple swap multiplier)
        """
        if exit_time <= entry_time:
            return 0

        # Convert MT5 day format (0=Sunday) to Python weekday format (0=Monday)
        # MT5: Sunday=0, Monday=1, Tuesday=2, Wednesday=3, ...
        # Python: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, ..., Sunday=6
        triple_swap_day_python = (triple_swap_day_mt5 + 6) % 7

        swap_days = 0
        current_date = entry_time.date()
        exit_date = exit_time.date()

        # Count each midnight crossing from entry date up to (but not including) exit date
        # Skip weekends (Saturday=5, Sunday=6) and holidays since forex market is closed
        while current_date < exit_date:
            weekday = current_date.weekday()

            # Check if this is a market holiday (New Year's Day or Christmas Day)
            is_holiday = (current_date.month == 1 and current_date.day == 1) or (
                current_date.month == 12 and current_date.day == 25
            )

            # Skip Saturday (5), Sunday (6), and holidays
            if weekday not in [5, 6] and not is_holiday:
                # Check if this night is the triple swap night
                # Triple swap is charged on the specified day (typically Wednesday)
                if weekday == triple_swap_day_python:
                    swap_days += 3  # Triple swap for weekend
                else:
                    swap_days += 1

            current_date += timedelta(days=1)

        return swap_days

    def _calculate_swap(
        self,
        position_type: int,
        volume: float,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        current_price: float,
    ) -> float:
        """
        Calculate swap fees for a position based on symbol info.

        Swap calculation depends on the swap_mode from symbol specifications:
        - POINTS: swap_value * volume * contract_size * point
        - CURRENCY_*: swap_value * volume
        - INTEREST: swap_value * price * volume * contract_size / 360

        Args:
            position_type: 1 for long, -1 for short (vectorized convention)
            volume: Position size in lots
            entry_time: Position entry timestamp
            exit_time: Position exit timestamp
            entry_price: Entry price of the position
            current_price: Current/exit price of the position

        Returns:
            Total swap fee in account currency (positive = cost, negative = credit)
        """
        from apps.trading.symbol_info import SymbolSwapMode

        try:
            swap_mode = self._symbol_provider.get_swap_mode()
            swap_long = self._symbol_provider.get_swap_long()
            swap_short = self._symbol_provider.get_swap_short()
            contract_size = self._get_contract_size()
            point = self._get_point()

            # Get triple swap day from symbol info (default Wednesday = 3 in MT5 format)
            try:
                triple_swap_day_enum = self._symbol_provider.get_swap_rollover3days()
                # DayOfWeek enum has .value property for the integer
                triple_swap_day = (
                    triple_swap_day_enum.value
                    if hasattr(triple_swap_day_enum, "value")
                    else int(triple_swap_day_enum)  # type: ignore
                )
            except Exception:
                triple_swap_day = 3  # Default to Wednesday (MT5 format)

            # Get the appropriate swap value based on position type
            # In vectorized engine: 1 = long, -1 = short
            swap_value = swap_long if position_type == 1 else swap_short

            # Count swap days (including triple swap multiplier)
            swap_days = self._count_swap_days(entry_time, exit_time, triple_swap_day)

            # If no swap days or swap is disabled, no swap
            if swap_days <= 0 or swap_mode == SymbolSwapMode.DISABLED:
                return 0.0

            # Calculate daily swap based on mode
            if swap_mode == SymbolSwapMode.POINTS:
                # Swap in points: swap_value * volume * contract_size * point
                daily_swap = swap_value * volume * contract_size * point
            elif swap_mode in (
                SymbolSwapMode.CURRENCY_SYMBOL,
                SymbolSwapMode.CURRENCY_MARGIN,
                SymbolSwapMode.CURRENCY_DEPOSIT,
            ):
                # Swap in currency: swap_value * volume
                daily_swap = swap_value * volume
            elif swap_mode == SymbolSwapMode.INTEREST_CURRENT:
                # Annual interest using current price
                # swap_value is annual %, daily = value * price * volume * contract / 360
                daily_swap = (
                    (swap_value / 100) * current_price * volume * contract_size / 360
                )
            elif swap_mode == SymbolSwapMode.INTEREST_OPEN:
                # Annual interest using open price
                daily_swap = (
                    (swap_value / 100) * entry_price * volume * contract_size / 360
                )
            else:
                # Default fallback: treat as points
                daily_swap = swap_value * volume * contract_size * point

            # Multiply by swap days (already includes triple swap multiplier)
            total_swap = daily_swap * swap_days

            return total_swap

        except Exception as e:
            logger.warning(f"Error calculating swap: {e}, returning 0.0")
            return 0.0

    def get_slippage(self) -> float:
        """
        Get slippage value in price units (points * symbol point value).

        Returns:
            Slippage value in price units
        """
        # Get raw points from base class logic
        slippage_points = super().get_slippage()
        # Multiply by symbol point to get price offset
        return slippage_points * self._get_point()

    def get_spread(self, bar: Optional[pd.Series] = None) -> float:
        """
        Get spread value in price units (points * symbol point value).

        All spread values (broker, fixed, variable) are in points.

        Args:
            bar: Current bar data

        Returns:
            Spread value in price units
        """
        # Get spread in points from base class
        spread_points = super().get_spread(bar)
        # Convert points to price units
        return spread_points * self._get_point()

    def get_backtest_mode(self) -> str:
        """Return backtest mode."""
        return "vectorized"

    def run(self) -> BacktestResult:
        """
        Run vectorized backtest.

        Returns:
            BacktestResult with backtest data
        """
        logger.info(f"Starting vectorized backtest: {self.strategy.__class__.__name__}")
        logger.info(f"Period: {self.data.index[0]} to {self.data.index[-1]}")
        logger.info(f"Bars: {len(self.data)}, Initial balance: ${self.initial_balance}")

        try:
            self._running = True

            # Phase 1: Initialize strategy
            self.strategy.on_init()

            # Phase 2: Calculate indicators and generate signals (vectorized)
            logger.info("Calculating indicators and signals (vectorized)...")
            self.data = self.strategy.on_bar(self.data)

            # Phase 3: Extract signals from signal column
            self._extract_signals()

            # Phase 4: Simulate trades (vectorized)
            self._simulate_trades()

            # Phase 5: Build result
            final_balance = self._calculate_final_balance()
            final_equity = final_balance
            self.result = self._build_result(final_balance, final_equity)

            logger.info(f"Backtest complete: {len(self._trade_records)} trades")
            logger.info(
                f"Final balance: ${final_balance:.2f} ({((final_balance - self.initial_balance) / self.initial_balance * 100):.2f}%)"
            )

            return self.result

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise RuntimeError(f"Backtest execution failed: {e}") from e
        finally:
            self._running = False

    def _extract_signals(self) -> None:
        """Extract signals from signal columns."""
        logger.info("Extracting signals...")

        # Check for signal columns
        has_entry = "entry_signal" in self.data.columns
        has_exit = "exit_signal" in self.data.columns
        has_pending = "pending_signal" in self.data.columns
        has_cancel = "cancel_pending_signal" in self.data.columns
        has_legacy_signal = "signal" in self.data.columns

        if not (
            has_entry or has_exit or has_pending or has_cancel or has_legacy_signal
        ):
            logger.warning("No signal columns found in data")
            self._signals = []
            return

        signals = []
        for i in range(len(self.data)):
            sig = self._process_signal_row(
                i, has_entry, has_exit, has_pending, has_cancel, has_legacy_signal
            )
            if sig:
                signals.append(sig)

        self._signals = signals
        logger.info(f"Extracted {len(signals)} signals")

    def _process_signal_row(
        self,
        i: int,
        has_entry: bool,
        has_exit: bool,
        has_pending: bool,
        has_cancel: bool,
        has_legacy_signal: bool,
    ) -> Optional[Dict[str, Any]]:
        """Process a single row for signals."""
        if not self._is_signal_present(
            i, has_entry, has_exit, has_pending, has_cancel, has_legacy_signal
        ):
            return None

        # Get signal details from strategy
        signal_info = self.strategy.get_signal(self.data, i)

        if not signal_info:
            return None

        price: Any = signal_info.get("price")
        if price is None:
            price = signal_info.get("entry_price")
        if price is None:
            price = float(self.data.iloc[i]["open"])

        return {
            "timestamp": self.data.index[i],
            "bar_index": i,
            "signal": self._derive_signal_type(signal_info),
            "signal_info": signal_info,
            "price": float(price),
            "stop_loss": signal_info.get("stop_loss"),
            "take_profit": signal_info.get("take_profit"),
            "reason": signal_info.get("reason", "Signal detected"),
        }

    def _is_signal_present(
        self,
        i: int,
        has_entry: bool,
        has_exit: bool,
        has_pending: bool,
        has_cancel: bool,
        has_legacy_signal: bool,
    ) -> bool:
        """Check if any signal column indicates a signal."""
        # Check new columns first
        if (
            (has_entry and self.data.iloc[i].get("entry_signal", 0) != 0)
            or (has_exit and self.data.iloc[i].get("exit_signal", 0) != 0)
            or (has_pending and self.data.iloc[i].get("pending_signal", 0) != 0)
            or (has_cancel and self.data.iloc[i].get("cancel_pending_signal", 0) != 0)
        ):
            return True

        # Fallback to legacy
        if has_legacy_signal:
            sig_val = self.data.iloc[i].get("signal")
            if pd.notna(sig_val) and sig_val:
                return True

        return False

    def _derive_signal_type(self, signal_info: SignalDict) -> Optional[str]:
        """Derive legacy signal string from signal info."""
        s_type = signal_info.get("signal")  # Legacy key
        if s_type:
            return str(s_type)

        entry = signal_info.get("entry_signal", 0)
        exit_sig = signal_info.get("exit_signal", 0)

        if entry == 1:
            return "buy"
        elif entry == -1:
            return "sell"
        elif exit_sig == 1:
            return "exit buy"
        elif exit_sig == -1:
            return "exit sell"
        return None

    def _calculate_position_size(
        self, signal: Dict[str, Any], bar_index: int, current_balance: float
    ) -> float:
        """
        Calculate position size using PositionSizer if configured.

        Args:
            signal: Signal dictionary with price, stop_loss
            bar_index: Index of current bar
            current_balance: Current account balance

        Returns:
            Position size in lots
        """
        if self.position_sizer:
            # Build context for sizing calculation
            context = {}

            # Get the bar data for this signal
            bar = self.data.iloc[bar_index]

            # Add ATR if available in data
            atr_period = self.config.get("atr_period", 14)
            atr_col = f"atr_{atr_period}"
            if atr_col in bar.index:
                context["atr"] = bar[atr_col]

            # Calculate position size
            volume = self.position_sizer.calculate_size(
                account_balance=current_balance,
                entry_price=signal["price"],
                stop_loss=signal["stop_loss"],
                symbol_info=None,  # VectorizedEngine doesn't have symbol_info
                context=context,
            )
        else:
            # Fixed position size for consistent backtesting/optimization
            # Using 0.01 lots (minimum size) to work with small accounts
            volume = 0.01

        return float(volume)

    def _calculate_pip_value(self) -> float:
        """
        Calculate pip value using SymbolProvider (MT5 specs preferred).

        Falls back to pattern matching if provider data unavailable.

        Returns:
            Pip value for the symbol
        """
        try:
            # Try to get from SymbolProvider (MT5 or defaults)
            point = float(self._symbol_provider.get_point())
            digits = int(self._symbol_provider.get_digits())

            # Calculate pip value based on digits
            # Calculate pip value based on digits
            if digits >= 2:
                # 5-digit forex (0.00001) -> 0.0001
                # 3-digit JPY pairs (0.001) -> 0.01
                # 2-digit indices: 0.01 * 10 = 0.1
                return point * 10

            return 1.0  # Default for indices/commodities
        except Exception:
            # Fallback to pattern matching if provider fails
            return self._fallback_pip_calculation()

    def _fallback_pip_calculation(self) -> float:
        """
        Fallback pip value calculation using pattern matching.

        Used when SymbolProvider is unavailable or fails.

        Returns:
            Pip value for the symbol
        """
        symbol_upper = self.strategy.symbol.upper()

        # JPY pairs use 2 decimal places for pip (0.01)
        if "JPY" in symbol_upper:
            return 0.01

        # Forex pairs are 6 characters with major currencies
        # e.g., EURUSD, GBPUSD, AUDUSD, etc.
        forex_currencies = ["EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "USD"]
        if len(self.strategy.symbol) == 6:
            base = symbol_upper[:3]
            quote = symbol_upper[3:6]
            if base in forex_currencies and quote in forex_currencies:
                return 0.0001

        # Indices and commodities (XAU, BTC, SPX, NAS, etc.) use whole numbers
        return 1.0

    def _create_trade_record(
        self,
        trade_id: int,
        entry_time: datetime,
        exit_time: datetime,
        position_direction: int,
        position_entry_price: float,
        exit_price: float,
        position_size: float,
        exit_reason: str,
        balance: float,
        position_entry_idx: int,
        exit_idx: int,
        slippage_usd: float = 0.0,
        position_sl: Optional[float] = None,
        position_tp: Optional[float] = None,
        margin_used: float = 0.0,
        equity_at_entry: float = 0.0,
        spread_at_entry: float = 0.0,
        drawdown: float = 0.0,
    ) -> TradeRecord:
        """
        Create a TradeRecord with all calculated fields.

        Args:
            trade_id: Unique trade ID
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            position_direction: 1 for long, -1 for short
            position_entry_price: Entry price (after slippage applied)
            exit_price: Exit price (after slippage applied)
            position_size: Position size in lots
            exit_reason: Exit reason
            balance: Current balance after trade
            position_entry_idx: Bar index where position was opened
            exit_idx: Bar index where position was closed
            slippage_usd: Total slippage cost in USD for this trade
            position_sl: Stop loss price (for R-multiple calculation)
            position_tp: Take profit price
            margin_used: Margin required for this position
            equity_at_entry: Account equity when position opened
            spread_at_entry: Spread in points when position opened
            drawdown: Current account drawdown at trade exit

        Returns:
            TradeRecord instance
        """
        # Calculate P&L
        if position_direction == 1:  # Long
            gross_pnl = (
                (exit_price - position_entry_price)
                * position_size
                * self._get_contract_size()
            )
        else:  # Short
            gross_pnl = (
                (position_entry_price - exit_price)
                * position_size
                * self._get_contract_size()
            )

        # Calculate trade bars and duration
        trade_bars = exit_idx - position_entry_idx
        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        # Calculate commission (per lot * volume)
        trade_commission = self._calculate_commission(position_size)

        # Calculate swap fees based on overnight rollovers
        trade_swap = self._calculate_swap(
            position_type=position_direction,
            volume=position_size,
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=position_entry_price,
            current_price=exit_price,
        )

        # Calculate net P&L (commission and swap are already negative values)
        net_pnl = gross_pnl + trade_commission + trade_swap

        # Calculate profit in pips dynamically based on symbol
        pip_value = self._calculate_pip_value()
        price_diff = (
            exit_price - position_entry_price
            if position_direction == 1
            else position_entry_price - exit_price
        )
        profit_pips = price_diff / pip_value

        # Calculate cumulative pips
        cumulative_pips = (
            sum(t.profit_loss_pips for t in self._trade_records) + profit_pips
        )

        # Calculate MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)
        # Find the highest and lowest prices during the trade
        trade_slice = self.data.iloc[position_entry_idx : exit_idx + 1]
        highest_price = trade_slice["high"].max()
        lowest_price = trade_slice["low"].min()

        if position_direction == 1:  # Long
            # For long: MAE is how far price went down, MFE is how far it went up
            mae = (position_entry_price - lowest_price) / pip_value
            mfe = (highest_price - position_entry_price) / pip_value
        else:  # Short
            # For short: MAE is how far price went up, MFE is how far it went down
            mae = (highest_price - position_entry_price) / pip_value
            mfe = (position_entry_price - lowest_price) / pip_value

        # Calculate R-multiple (profit relative to initial risk)
        r_multiple = 0.0
        sl_distance = 0.0
        initial_risk_pips = 0.0
        initial_risk_usd = 0.0
        if position_sl is not None and position_sl > 0:
            sl_distance = abs(position_entry_price - position_sl)
            initial_risk_pips = sl_distance / pip_value
            initial_risk_usd = sl_distance * position_size * self._get_contract_size()
            if initial_risk_usd > 0:
                r_multiple = gross_pnl / initial_risk_usd

        # Get magic number from strategy variables
        magic_number = 0
        if hasattr(self.strategy, "params") and self.strategy.params:
            variables = self.strategy.params.get("variables", {})
            magic_number = variables.get("magic", 0)

        # Calculate Buy & Hold Return
        buy_hold_val = 0.0
        buy_hold_pips = 0.0

        if self._first_trade_open is not None and self._first_trade_size is not None:
            # Pips: (Close - First_Open) / PipValue
            # Note: Buy & Hold is implicitly a LONG position from the start.
            # So we strictly use (Exit - First_Open).
            price_delta = exit_price - self._first_trade_open
            buy_hold_pips = price_delta / pip_value

            # Value: (Exit - First_Open) * First_Size * Contract_Size
            buy_hold_val = (
                price_delta * self._first_trade_size * self._get_contract_size()
            )

        return TradeRecord(
            # 1️⃣ Trade Identification & Attribution
            trade_id=None,
            ticket=trade_id,
            symbol=self.strategy.symbol,
            type="buy" if position_direction == 1 else "sell",
            magic_number=magic_number,
            strategy_name=self.strategy.__class__.__name__,
            setup=None,
            sample_type=None,
            comment="",
            # 2️⃣ Strategy Context
            signal_timeframe=self.timeframe,
            execution_timeframe=self.timeframe,
            session=None,
            day_of_week=entry_time.weekday() if entry_time else None,
            hour_of_day=entry_time.hour if entry_time else None,
            # 3️⃣ Trade Timing
            open_time=entry_time,
            close_time=exit_time,
            time_in_trade=duration_hours,
            bars_in_trade=trade_bars,
            # 4️⃣ Entry Definition
            open_price=position_entry_price,
            requested_entry_price=position_entry_price,
            spread_at_entry=spread_at_entry,
            size=position_size,
            # 5️⃣ Exit Definition
            close_price=exit_price,
            requested_exit_price=exit_price,
            close_type=exit_reason.upper() if exit_reason else "UNKNOWN",
            exit_reason=exit_reason.upper() if exit_reason else "UNKNOWN",
            # 6️⃣ Trade Plan & Risk
            stop_loss_price_level=position_sl or 0.0,
            profit_target_price_level=position_tp or 0.0,
            initial_risk_pips=initial_risk_pips,
            initial_risk_usd=initial_risk_usd,
            # 7️⃣ Account State
            balance_at_entry=balance - net_pnl,  # Balance before this trade
            equity_at_entry=equity_at_entry,
            margin_used=margin_used,
            free_margin=equity_at_entry - margin_used if equity_at_entry > 0 else 0.0,
            balance_pips=cumulative_pips,
            # 8️⃣ Trade Management
            max_position_size_reached=position_size,
            partial_close_count=0,
            trailing_stop_used=False,
            breakeven_triggered=False,
            # 9️⃣ Execution Quality
            slippage_usd=slippage_usd,
            fill_price_deviation=0.0,
            execution_latency_ms=0.0,
            # 🔟 Performance Results
            profit_loss=net_pnl,
            profit_loss_pips=profit_pips,
            commission=trade_commission,
            swap=trade_swap,
            r_multiple=r_multiple,
            buy_hold=buy_hold_val,
            buy_hold_pips=buy_hold_pips,
            # 1️⃣1️⃣ Excursion & Drawdown Analytics
            mae_usd=mae * position_size * self._get_contract_size() * pip_value,
            mae_pips=mae,
            mfe_usd=mfe * position_size * self._get_contract_size() * pip_value,
            mfe_pips=mfe,
            drawdown=drawdown,
            # 1️⃣2️⃣ Regime & Research Tags
            market_regime=None,
            volatility_bucket=None,
            correlation_cluster=None,
            # 1️⃣3️⃣ Compliance & Audit
            rule_violation_flag=False,
            manual_intervention=False,
        )

    def _check_sl_tp_hit(
        self,
        bar: pd.Series,
        direction: int,
        sl: Optional[float],
        tp: Optional[float],
    ) -> Tuple[Optional[float], Optional[str]]:
        """Check if SL or TP is hit based on current bar close."""
        if direction == 1:  # Long
            if sl and bar["close"] <= sl:
                return float(sl), "sl"
            if tp and bar["close"] >= tp:
                return float(tp), "tp"
        elif direction == -1:  # Short
            if sl and bar["close"] >= sl:
                return float(sl), "sl"
            if tp and bar["close"] <= tp:
                return float(tp), "tp"
        return None, None

    def _handle_position_close(
        self,
        exit_price: float,
        exit_reason: str,
        state: Dict[str, Any],
        exit_idx: int,
        timestamp: pd.Timestamp,
    ) -> None:
        """Handle position closing logic."""
        # Calculate exit slippage
        exit_slippage = self.get_slippage()
        if state["position_direction"] == 1:  # Long closing (selling)
            final_exit_price = exit_price - exit_slippage
        else:  # Short closing (buying)
            final_exit_price = exit_price + exit_slippage

        # Calculate total slippage
        total_slippage = state["position_entry_slippage"] + exit_slippage
        slippage_usd = (
            total_slippage * state["position_size"] * self._get_contract_size()
        )

        # Calculate gross P&L
        if state["position_direction"] == 1:  # Long
            gross_pnl = (
                (final_exit_price - state["position_entry_price"])
                * state["position_size"]
                * self._get_contract_size()
            )
        else:  # Short
            gross_pnl = (
                (state["position_entry_price"] - final_exit_price)
                * state["position_size"]
                * self._get_contract_size()
            )

        # Calculate commission (per lot * volume)
        trade_commission = self._calculate_commission(state["position_size"])

        # Calculate swap fees based on overnight rollovers
        entry_time = self.data.index[state["position_entry_idx"]]
        trade_swap = self._calculate_swap(
            position_type=state["position_direction"],
            volume=state["position_size"],
            entry_time=entry_time.to_pydatetime(),
            exit_time=timestamp.to_pydatetime(),
            entry_price=state["position_entry_price"],
            current_price=final_exit_price,
        )

        # Calculate net P&L (commission and swap are already negative values)
        pnl = gross_pnl + trade_commission + trade_swap
        state["balance"] += pnl

        if state["balance"] > state["peak_balance"]:
            state["peak_balance"] = state["balance"]
        current_drawdown = state["peak_balance"] - state["balance"]

        # Record trade
        entry_time = self.data.index[state["position_entry_idx"]]

        trade = self._create_trade_record(
            trade_id=state["trade_id"],
            entry_time=entry_time.to_pydatetime(),
            exit_time=timestamp.to_pydatetime(),
            position_direction=state["position_direction"],
            position_entry_price=state["position_entry_price"],
            exit_price=final_exit_price,
            position_size=state["position_size"],
            exit_reason=exit_reason,
            balance=state["balance"],
            position_entry_idx=state["position_entry_idx"],
            exit_idx=exit_idx,
            slippage_usd=slippage_usd,
            position_sl=state["position_sl"],
            position_tp=state["position_tp"],
            margin_used=state["position_entry_margin"],
            equity_at_entry=state["position_entry_equity"],
            spread_at_entry=state["position_entry_spread"],
            drawdown=current_drawdown,
        )

        self._record_trade(trade)
        state["trade_id"] += 1

        # Release margin
        contract_size = self._get_contract_size()
        self._used_margin -= self.calculate_required_margin(
            state["position_size"], state["position_entry_price"], contract_size
        )
        self._used_margin = max(0.0, self._used_margin)

        # Reset position state
        state["in_position"] = False
        state["position_entry_idx"] = -1
        state["position_direction"] = 0
        state["position_entry_price"] = 0.0

    def _handle_position_open(
        self,
        entry_price: float,
        direction: int,
        size: float,
        sl: Optional[float],
        tp: Optional[float],
        state: Dict[str, Any],
        current_idx: int,
        entry_slippage: float,
        bar: pd.Series,
    ) -> bool:
        """
        Handle position opening logic.

        Returns check execution status (True if opened, False if failed).
        """
        contract_size = self._get_contract_size()

        # Check margin before opening position
        if not self.has_sufficient_margin(
            size, entry_price, contract_size, state["balance"]
        ):
            logger.warning(
                f"Insufficient margin to open position at {entry_price:.5f}. "
            )
            return False

        state["in_position"] = True
        state["position_entry_idx"] = current_idx
        state["position_direction"] = direction
        state["position_entry_price"] = entry_price
        state["position_size"] = size
        state["position_sl"] = sl
        state["position_tp"] = tp
        state["position_entry_slippage"] = entry_slippage

        # Track margin and equity at entry
        state["position_entry_margin"] = self.calculate_required_margin(
            size, entry_price, contract_size
        )
        state["position_entry_equity"] = state["balance"]
        state["position_entry_spread"] = self.get_spread(bar)

        # Capture Buy & Hold baseline
        if self._first_trade_open is None:
            self._first_trade_open = entry_price
            self._first_trade_size = size

        # Update used margin
        self._used_margin += state["position_entry_margin"]
        return True

    def _simulate_trades(self) -> None:
        """
        Simulate trades from signals using vectorized operations.

        Simplified execution:
        - Entry at signal close price
        - Exit at SL/TP hit (close-based) or opposite signal
        - No intra-bar execution
        """
        logger.info("Simulating trades (vectorized)...")

        if (
            not self._signals
            and "buy_stop" not in self.data.columns
            and "sell_stop" not in self.data.columns
        ):
            logger.warning("No signals to simulate")
            return

        # Initialize state dictionary
        state: Dict[str, Any] = {
            "balance": self.initial_balance,
            "peak_balance": self.initial_balance,
            "in_position": False,
            "position_entry_idx": -1,
            "position_direction": 0,
            "position_entry_price": 0.0,
            "position_size": 0.01,
            "position_sl": None,
            "position_tp": None,
            "position_entry_slippage": 0.0,
            "position_entry_margin": 0.0,
            "position_entry_equity": 0.0,
            "position_entry_spread": 0.0,
            "trade_id": 1,
            "pending_orders": [],  # List of pending orders
        }

        # Process each bar
        for i in range(len(self.data)):
            timestamp = self.data.index[i]
            bar = self.data.iloc[i]

            # 1. Check if position hits SL/TP
            if state["in_position"]:
                exit_price, exit_reason = self._check_sl_tp_hit(
                    bar,
                    int(state["position_direction"] or 0),
                    state["position_sl"],
                    state["position_tp"],
                )

                if exit_price is not None and exit_reason:
                    self._handle_position_close(
                        exit_price, exit_reason, state, i, timestamp
                    )

            # 2. Check for signals at this bar
            self._process_bar_signals(i, timestamp, bar, state)

            # 3. Check Pending Orders (only if not in position)
            if not state["in_position"]:
                self._process_pending_orders(i, bar, state)

            # Record equity point
            self._record_equity_point(
                timestamp.to_pydatetime(),
                float(state["balance"] or 0.0),
                float(state["balance"] or 0.0),
            )

        # Close any remaining position at end
        if state["in_position"]:
            exit_price = float(self.data.iloc[-1]["close"])
            self._handle_position_close(
                exit_price,
                "end_of_data",
                state,
                len(self.data) - 1,
                self.data.index[-1],
            )

    def _process_bar_signals(
        self, i: int, timestamp: pd.Timestamp, bar: pd.Series, state: Dict[str, Any]
    ) -> None:
        """Process signals for a specific bar."""
        # Convert timestamp to datetime for comparison
        current_time = (
            timestamp.to_pydatetime()
            if isinstance(timestamp, pd.Timestamp)
            else timestamp
        )

        # Skip signal processing if outside backtest date range
        if (
            current_time < self.backtest_start_date
            or current_time > self.backtest_end_date
        ):
            return

        bar_signals = [s for s in self._signals if s["bar_index"] == i]

        for signal in bar_signals:
            raw_signal = str(signal["signal"]).lower().strip()
            is_exit_buy = raw_signal in ["exit buy", "close buy", "close_buy"]
            is_exit_sell = raw_signal in ["exit sell", "close sell", "close_sell"]

            if state["in_position"]:
                should_close = (state["position_direction"] == 1 and is_exit_buy) or (
                    state["position_direction"] == -1 and is_exit_sell
                )

                if should_close:
                    self._handle_position_close(
                        float(signal["price"]), "signal", state, i, timestamp
                    )
                    self._handle_position_close(
                        float(signal["price"]), "signal", state, i, timestamp
                    )
                    continue

            # Handle Pending Signals
            # 1: Buy Stop, -1: Sell Stop, 2: Buy Limit, -2: Sell Limit
            pending_val = signal["signal_info"].get("pending_signal", 0)
            cancel_val = signal["signal_info"].get("cancel_pending_signal", 0)

            if cancel_val != 0:
                # Cancel all pending orders for now (simplistic)
                state["pending_orders"] = []

            # Handle entry signals
            signal_is_buy = raw_signal == "buy"
            signal_direction = 1 if signal_is_buy else -1

            # Close opposite position if signal reverses
            if state["in_position"] and signal_direction != state["position_direction"]:
                self._handle_position_close(
                    float(signal["price"]), "signal", state, i, timestamp
                )

            # Enter new position from Signal
            if not state["in_position"]:
                entry_slippage = self.get_slippage()
                if signal_is_buy:
                    proposed_entry_price = signal["price"] + entry_slippage
                else:
                    proposed_entry_price = signal["price"] - entry_slippage

                proposed_size = self._calculate_position_size(
                    signal, i, float(state["balance"] or 0.0)
                )

                self._handle_position_open(
                    proposed_entry_price,
                    signal_direction,
                    proposed_size,
                    signal["stop_loss"],
                    signal["take_profit"],
                    state,
                    i,
                    entry_slippage,
                    bar,
                )

            # Handle Pending Signals (Priority 4)
            # 1: Buy Stop, -1: Sell Stop, 2: Buy Limit, -2: Sell Limit
            pending_val = signal["signal_info"].get("pending_signal", 0)

            if pending_val != 0:
                # Add new pending order
                state["pending_orders"].append(
                    {
                        "type": pending_val,
                        "price": float(signal["price"]),
                        "sl": signal["stop_loss"],
                        "tp": signal["take_profit"],
                        "created_at": timestamp,
                    }
                )

    def _process_pending_orders(
        self, i: int, bar: pd.Series, state: Dict[str, Any]
    ) -> None:
        """Process pending orders for a specific bar."""
        if not state["pending_orders"]:
            return

        triggered_idx = -1
        triggered_order = None
        execution_price = 0.0

        # Iterate pending orders
        # Note: simplistic implementation - takes first triggered order and clears others if OCO?
        # For now, just execute first valid one and clear it.

        for idx, order in enumerate(state["pending_orders"]):
            p_type = order["type"]
            price = order["price"]

            triggered = False

            # 1: Buy Stop (High >= Price) or -2: Sell Limit (High >= Price)
            if (p_type == 1 or p_type == -2) and bar["high"] >= price:
                triggered = True
                execution_price = max(bar["open"], price)

            # -1: Sell Stop (Low <= Price) or 2: Buy Limit (Low <= Price)
            elif (p_type == -1 or p_type == 2) and bar["low"] <= price:
                triggered = True
                execution_price = min(bar["open"], price)

            if triggered:
                triggered_idx = idx
                triggered_order = order
                break

        if triggered_order:
            # Remove triggered order
            state["pending_orders"].pop(triggered_idx)

            # Execute trade
            is_buy = triggered_order["type"] > 0
            direction = 1 if is_buy else -1

            # Prepare dummy signal for calculation
            dummy_signal = {
                "signal": "buy" if is_buy else "sell",
                "price": execution_price,
                "stop_loss": triggered_order["sl"],
                "take_profit": triggered_order["tp"],
            }

            entry_slippage = self.get_slippage()
            price_with_slip = execution_price + (
                entry_slippage if is_buy else -entry_slippage
            )

            size = self._calculate_position_size(
                dummy_signal, i, float(state["balance"] or 0.0)
            )

            self._handle_position_open(
                price_with_slip,
                direction,
                size,
                triggered_order["sl"],
                triggered_order["tp"],
                state,
                i,
                entry_slippage,
                bar,
            )

    def _calculate_final_balance(self) -> float:
        """Calculate final balance from trades."""
        balance = self.initial_balance
        for trade in self._trade_records:
            balance += trade.profit_loss
        return balance
