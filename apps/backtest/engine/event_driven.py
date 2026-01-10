"""
Event-Driven Backtest Engine.

High-fidelity bar-by-bar backtest execution.
Aligned with live trading for realistic simulation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, cast

import pandas as pd

from apps.logger import logger
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.trading import AccountInfo, OrderInfo, PositionInfo, SymbolInfo, Trade
from apps.trading.account_info import BacktestAccountProvider
from apps.trading.order_info import BacktestOrderProvider, OrderState, OrderType
from apps.trading.position_info import BacktestPositionProvider, PositionType
from apps.trading.symbol_info import BacktestSymbolProvider
from apps.trading.trade import BacktestTradeProvider

from ..result import BacktestResult, TradeRecord
from .base import BaseEngine


class EventDrivenEngine(BaseEngine):
    """
    Event-Driven Backtest Engine.

    Characteristics:
    - Iterates bar-by-bar (or tick-by-tick)
    - Emits explicit events
    - Uses full broker simulation via BacktestProviders
    - Realistic execution modeling
    - Slower but accurate

    Use for:
    - Strategy validation
    - Risk analysis
    - Live trading alignment testing
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        execution_data: Optional[pd.DataFrame] = None,
        data_step_mode: str = "trading_timeframe",
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
        Initialize event-driven engine.

        Args:
            strategy: Strategy to backtest
            data: OHLCV DataFrame (Signal Data)
            execution_data: Optional OHLCV DataFrame for execution (e.g. M1 bars)
            data_step_mode: 'trading_timeframe', 'm1_bars', or 'tick'
            initial_balance: Starting balance
            commission: Commission per trade
            slippage_points: Slippage in points (legacy)
            slippage_config: Slippage configuration dict
            spread_config: Spread configuration dict
            leverage: Account leverage
            timeframe: Bar timeframe (e.g., "H1", "M15")
            config: Additional config
            position_sizer: Optional PositionSizer for dynamic position sizing
            mt5_client: Optional MT5Client for fetching real symbol info (swap rates, etc.)
        """
        config = config or {}
        config["timeframe"] = timeframe
        config["data_step_mode"] = data_step_mode

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
        self.data_step_mode = data_step_mode
        self.position_sizer = position_sizer

        # Execution data defaults to signal data if not provided
        self.execution_data = (
            execution_data if execution_data is not None else data.copy()
        )

        # Create backtest providers
        self._trade_provider = BacktestTradeProvider(initial_balance)
        self._account_provider = BacktestAccountProvider(
            initial_balance, trade_provider=self._trade_provider
        )
        self._position_provider = BacktestPositionProvider()
        self._order_provider = BacktestOrderProvider()
        self._symbol_provider = BacktestSymbolProvider(
            mt5_client=mt5_client, symbol_name=strategy.symbol
        )

        # Inject trading objects into strategy
        self.strategy.trade = Trade(self._trade_provider)
        self.strategy.account = AccountInfo(self._account_provider)
        self.strategy.position = PositionInfo(self._position_provider)
        self.strategy.order = OrderInfo(self._order_provider)
        self.strategy.symbol_info = SymbolInfo(self._symbol_provider)

        # Configure trade object
        if self.strategy.trade is None:
            raise RuntimeError("trade object must be injected")
        self.strategy.trade.set_expert_magic_number(
            hash(strategy.__class__.__name__) % 10000
        )

        # Track open positions for trade recording
        self._open_positions: Dict[int, Dict[str, Any]] = {}
        self._next_trade_id = 1

        # Store data with signals
        self._data_with_signals: Optional[pd.DataFrame] = None

        # Buy & Hold Baseline
        self._first_trade_open: Optional[float] = None
        self._first_trade_size: Optional[float] = None

    def _get_contract_size(self) -> float:
        """Get contract size from symbol provider."""
        try:
            return self._symbol_provider.get_contract_size()
        except Exception:
            logger.warning(
                "Failed to get contract size from symbol provider, using default"
            )
            return 100000.0  # Default forex contract size

    def _get_point(self) -> float:
        """Get point value from symbol provider."""
        try:
            return self._symbol_provider.get_point()
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
            Total commission in account currency
        """
        return -self.commission * volume

    def _count_swap_days(
        self, entry_time: datetime, exit_time: datetime, triple_swap_day_mt5: int = 3
    ) -> int:
        """
        Count the number of swap charges between entry and exit time.

        Swap is charged at midnight rollover. To be charged swap for a day,
        you must hold the position THROUGH that day's midnight (into the next day).
        The last day before exit doesn't count because you exit before the next midnight.

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
            position_type: 0 for BUY (long), 1 for SELL (short)
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
            swap_value = swap_long if position_type == 0 else swap_short

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
        slippage_points = super().get_slippage()
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
        spread_points = super().get_spread(bar)
        return spread_points * self._get_point()

    def _get_magic_number(self) -> int:
        """Get magic number from strategy trade object or params."""
        # Try to get from strategy.trade._magic first (for live trading)
        if self.strategy.trade is not None and hasattr(self.strategy.trade, "_magic"):
            return int(self.strategy.trade._magic)  # pylint: disable=protected-access
        # Fallback to strategy.params.variables.magic
        if hasattr(self.strategy, "params") and self.strategy.params:
            variables = self.strategy.params.get("variables", {})
            return int(variables.get("magic", 0))
        return 0

    def get_backtest_mode(self) -> str:
        """Return backtest mode."""
        return "event_driven"

    def run(self) -> BacktestResult:
        """
        Run event-driven backtest.

        Returns:
            BacktestResult with complete backtest data
        """
        logger.info(
            f"Starting event-driven backtest: {self.strategy.__class__.__name__}"
        )
        logger.info(f"Period: {self.data.index[0]} to {self.data.index[-1]}")
        logger.info(f"Bars: {len(self.data)}, Initial balance: ${self.initial_balance}")

        try:
            self._running = True
            self._peak_equity = (
                self.initial_balance
            )  # Track peak equity for drawdown calc

            # Phase 1: Initialize strategy
            logger.info("Initializing strategy...")
            self.strategy.on_init()

            # Phase 2: Calculate indicators and signals (vectorized)
            logger.info("Calculating indicators and signals...")
            self._data_with_signals = self.strategy.on_bar(self.data)

            # Phase 3: Main backtest loop
            self._run_backtest_loop()

            # Close all remaining positions
            self._close_all_positions()

            # Phase 4: Build result
            final_balance = self._account_provider.get_balance()
            final_equity = self._account_provider.get_equity()
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

    def _run_backtest_loop(self) -> None:  # noqa: C901
        """Run backtest loop by iterating bar by bar (or tick by tick)."""
        if self._data_with_signals is None:
            raise RuntimeError(
                "Data with signals must be prepared before backtest loop"
            )

        # Use execution_data for the loop
        execution_data = self.execution_data
        total_steps = len(execution_data)
        is_trading_timeframe = self.data_step_mode == "trading_timeframe"

        # Track processed signals to prevent duplicate execution on same signal
        last_processed_signal_idx = -1

        logger.info(
            f"Running backtest loop: {total_steps} steps "
            f"(Mode: {self.data_step_mode})"
        )

        for i in range(total_steps):
            self._current_bar_index = i
            bar = execution_data.iloc[i]
            timestamp = (
                bar.name if isinstance(bar.name, datetime) else bar.name.to_pydatetime()
            )

            # 1. Update providers using execution data
            price_type = "close" if self.data_step_mode == "tick" else "open"
            # For ticks, open/close are same usually. For M1, we update at Open for signal check?
            # Actually, standard behavior:
            # - Update Prcies to Open
            # - Check Signal (decided at prev Close)
            # - Execute
            self._update_prices(bar, price_type=price_type)

            # Track peak equity
            current_equity = self._account_provider.get_equity()
            if current_equity > self._peak_equity:
                self._peak_equity = current_equity

            # 2. Check for Signal
            signal_idx = -1
            signal_bar = None

            if is_trading_timeframe:
                signal_idx = i
                signal_bar = self._data_with_signals.iloc[i]
            else:
                # Find corresponding signal bar (H1) for current execution time (M1/Tick)
                # We want the H1 bar that *started* at or before this timestamp
                # searchsorted(side='right') gives index where timestamp would be inserted
                # index - 1 gives the largest timestamp <= current timestamp
                # Note: signals must be sorted (validated in Base)

                # Check bounds
                if len(self._data_with_signals) > 0:
                    try:
                        idx = (
                            self._data_with_signals.index.searchsorted(
                                timestamp, side="right"
                            )
                            - 1
                        )
                        if 0 <= idx < len(self._data_with_signals):
                            signal_idx = idx
                            signal_bar = self._data_with_signals.iloc[idx]

                            # Additional check: ensure we are within the bar's duration?
                            # If we are 5 hours later, searchsorted still returns the last bar.
                            # We assume data is continuous enough or it doesn't matter (stale signal check?)
                            # Usually signals are only valid for the timeframe period.
                            # But computing timeframe duration dynamically is hard.
                            # We trust 'last_processed_signal_idx' to handle "events".
                    except Exception:
                        pass

            if signal_bar is not None:
                # Check signals (New Multi-Column Schema)
                has_signal = False

                # Check if any signal column is non-zero
                entry_sig = signal_bar.get("entry_signal", 0)
                exit_sig = signal_bar.get("exit_signal", 0)
                pending_sig = signal_bar.get("pending_signal", 0)
                cancel_sig = signal_bar.get("cancel_pending_signal", 0)

                if (
                    (entry_sig and entry_sig != 0)
                    or (exit_sig and exit_sig != 0)
                    or (pending_sig and pending_sig != 0)
                    or (cancel_sig and cancel_sig != 0)
                ):
                    has_signal = True

                if has_signal:
                    if signal_idx == last_processed_signal_idx:
                        pass  # Already processed this signal
                    else:
                        # Get signal details (now returns SignalDict)
                        signal_info = self.strategy.get_signal(
                            self._data_with_signals, signal_idx
                        )

                        if signal_info:
                            # Check if timestamp is within backtest date range
                            # Skip signal execution if outside range (warm-up period or after end)
                            if timestamp < self.backtest_start_date:
                                logger.debug(
                                    f"[{timestamp}] Skipping signal (before backtest start: {self.backtest_start_date})"
                                )
                            elif timestamp > self.backtest_end_date:
                                logger.debug(
                                    f"[{timestamp}] Skipping signal (after backtest end: {self.backtest_end_date})"
                                )
                            else:
                                # For ticks, price is "close" (last). For M1, "open".
                                exec_price = (
                                    bar["close"]
                                    if self.data_step_mode == "tick"
                                    else bar["open"]
                                )

                                entry_type = signal_info.get("entry_signal", 0)
                                exit_type = signal_info.get("exit_signal", 0)
                                sl = signal_info.get("stop_loss")
                                tp = signal_info.get("take_profit")

                                sl_str = f"{sl:.5f}" if sl is not None else "None"
                                tp_str = f"{tp:.5f}" if tp is not None else "None"

                                logger.info(
                                    f"[{timestamp}] Signal detected (Idx: {signal_idx}): "
                                    f"Entry={entry_type}, Exit={exit_type} @ {exec_price:.5f} "
                                    f"(SL: {sl_str}, TP: {tp_str}) - Executing on {self.data_step_mode}"
                                )

                                self._execute_signal(signal_info, bar, price=exec_price)

                            # Mark this signal index as processed
                            last_processed_signal_idx = signal_idx

            # 3. Check Pending Orders
            self._check_pending_orders(bar)

            # 4. Update positions (Mark to Market)
            self._update_prices(bar, price_type="close")
            self._update_positions(bar)

            # 5. Check Stops
            self._check_stops(bar)

            # 6. On Tick
            if hasattr(self.strategy, "on_tick"):
                self.strategy.on_tick(bar)

            # Record equity point
            balance = self._account_provider.get_balance()
            equity = self._account_provider.get_equity()
            self._record_equity_point(timestamp, balance, equity)

            # Progress logging
            if (i + 1) % 1000 == 0 or (i + 1) == total_steps:
                progress = ((i + 1) / total_steps) * 100
                logger.debug(f"Progress: {progress:.1f}% ({i + 1}/{total_steps} steps)")

    def _update_prices(self, bar: pd.Series, price_type: str = "close") -> None:
        """
        Update provider prices from current bar.

        Args:
            bar: Current OHLCV bar
            price_type: 'open' or 'close'
        """
        symbol = self.strategy.symbol
        price = bar[price_type]
        spread = 0.00001  # Simplified 1 pip spread

        bid = price
        ask = price + spread

        self._trade_provider.set_symbol_price(symbol, bid, ask)
        bar_time = (
            bar.name if isinstance(bar.name, datetime) else bar.name.to_pydatetime()
        )
        self._symbol_provider.set_tick(bid=bid, ask=ask, last=price, time=bar_time)

    def _check_pending_orders(self, bar: pd.Series) -> None:
        """
        Check and trigger pending orders (Buy Stop, Sell Stop, etc.).

        Args:
            bar: Current OHLCV bar
        """
        # Iterate over a copy to allow modification
        # pylint: disable=protected-access
        if not hasattr(self._order_provider, "_orders"):
            return

        orders = list(self._order_provider._orders)  # Copy list

        for order in orders:
            ticket = order["ticket"]
            order_type = order["type"]
            price_open = order["price_open"]
            # BacktestTradeProvider uses 'volume_current' for pending orders
            volume = order.get("volume", order.get("volume_current", 0.0))
            sl = order["sl"]
            tp = order["tp"]

            triggered = False
            execution_price = 0.0

            # Check Buy Stop (Triggered if Ask >= Price)
            # We use High >= Price to simulate triggering during the bar
            # Also Check Sell Limit (Triggered if Bid >= Price)
            if (order_type == 4 or order_type == 3) and bar["high"] >= price_open:
                triggered = True
                execution_price = max(bar["open"], price_open)

            # Check Sell Stop (Triggered if Bid <= Price)
            # We use Low <= Price
            # Also Check Buy Limit (Triggered if Ask <= Price)
            elif (order_type == 5 or order_type == 2) and bar["low"] <= price_open:
                triggered = True
                execution_price = min(bar["open"], price_open)

            if triggered:
                order_type_str = "BUY STOP" if order_type == 4 else "SELL STOP"
                bar_time = (
                    bar.name
                    if isinstance(bar.name, datetime)
                    else bar.name.to_pydatetime()
                )
                logger.info(
                    f"[{bar_time}] Pending order #{ticket} ({order_type_str}) triggered at {execution_price:.5f} "
                    f"(Volume: {volume}, SL: {sl:.5f}, TP: {tp:.5f})"
                )

                # Create Position
                position_type = 0 if order_type == 4 else 1  # BUY=0, SELL=1

                # In BacktestTradeProvider, we need a way to convert Order to Position
                # We'll simulate it by calling buy/sell on the provider directly or via Trade
                # But since we are INSIDE the engine, we can manipulate the provider directly

                # 1. Remove Order
                self._order_provider.remove_order(ticket)

                # 2. Add Position
                pos_ticket = self._position_provider.add_position(
                    symbol=order["symbol"],
                    position_type=(
                        PositionType.BUY if position_type == 0 else PositionType.SELL
                    ),
                    volume=volume,
                    price_open=execution_price,
                    price_current=execution_price,
                    magic=order["magic"],
                    stop_loss=sl,
                    take_profit=tp,
                    comment=f"Triggered from order {ticket}",
                    time=(
                        bar.name
                        if isinstance(bar.name, datetime)
                        else bar.name.to_pydatetime()
                    ),
                )

                # 2b. Add to TradeProvider's internal positions (since Engine reads from there too)
                # This duplication is a bit messy in the mock providers.
                # Ideally BacktestTradeProvider should handle "order_trigger"

                # Let's fix this properly: BacktestTradeProvider doesn't support 'orders' natively yet?
                # We need to ensure BacktestTradeProvider HAS _orders support.

                # Hack: We will implement conversion here manually for now.
                # Logic copied from _open_position mostly

                # Add to internal tracking
                self._open_positions[pos_ticket] = {
                    "entry_time": (
                        bar.name.to_pydatetime()
                        if isinstance(bar.name, pd.Timestamp)
                        else bar.name
                    ),
                    "entry_price": execution_price,
                    "entry_sl": sl,
                    "entry_tp": tp,
                    "direction": "long" if position_type == 0 else "short",
                    "size": volume,
                    "entry_bar_index": self._current_bar_index,
                    "highest_price": execution_price,
                    "lowest_price": execution_price,
                }

                # Add to Trade Provider (which Engine uses for P&L)
                # We need to map PositionType enum to int for TradeProvider if it uses ints
                # Looking at _open_position -> self.strategy.trade.buy calls provider
                # We should just insert into self._trade_provider._positions directly

                self._trade_provider._positions[pos_ticket] = {
                    "ticket": pos_ticket,
                    "symbol": order["symbol"],
                    "type": position_type,
                    "volume": volume,
                    "price_open": execution_price,
                    "price_current": execution_price,
                    "sl": sl,
                    "tp": tp,
                    "profit": 0.0,
                    "magic": order["magic"],
                    "comment": order["comment"],
                }

    def _update_positions(self, bar: pd.Series) -> None:
        """
        Update open positions with current bar prices (mark-to-market).

        Also tracks highest/lowest prices for MAE/MFE calculation.

        Args:
            bar: Current OHLCV bar
        """
        # Get all positions from provider
        # pylint: disable=protected-access
        positions = self._trade_provider._positions

        for ticket, pos in positions.items():
            current_price = bar["close"]

            # Calculate unrealized P&L
            if pos["type"] == 0:  # BUY
                pnl = (
                    (current_price - pos["price_open"])
                    * pos["volume"]
                    * self._get_contract_size()
                )
            else:  # SELL
                pnl = (
                    (pos["price_open"] - current_price)
                    * pos["volume"]
                    * self._get_contract_size()
                )

            pos["profit"] = pnl

            # Track highest and lowest prices during trade for MAE/MFE
            if ticket in self._open_positions:
                position_data = self._open_positions[ticket]
                position_data["highest_price"] = max(
                    position_data["highest_price"], bar["high"]
                )
                position_data["lowest_price"] = min(
                    position_data["lowest_price"], bar["low"]
                )
            pos["price_current"] = current_price

    def _check_stops(self, bar: pd.Series) -> None:
        """
        Check if SL/TP hit on current bar.

        Args:
            bar: Current OHLCV bar
        """
        # pylint: disable=protected-access
        positions = list(self._trade_provider._positions.values())

        for pos in positions:
            sl = pos.get("sl", 0.0)
            tp = pos.get("tp", 0.0)

            if pos["type"] == 0:  # BUY position
                # Check SL (hit on bar's low)
                if sl > 0 and bar["low"] <= sl:
                    self._close_position_at_price(pos, sl, "sl")
                # Check TP (hit on bar's high)
                elif tp > 0 and bar["high"] >= tp:
                    self._close_position_at_price(pos, tp, "tp")

            else:  # SELL position
                # Check SL (hit on bar's high)
                if sl > 0 and bar["high"] >= sl:
                    self._close_position_at_price(pos, sl, "sl")
                # Check TP (hit on bar's low)
                elif tp > 0 and bar["low"] <= tp:
                    self._close_position_at_price(pos, tp, "tp")

    def _close_position_at_price(
        self, position: Dict[str, Any], price: float, reason: str
    ) -> None:
        """
        Close position at specific price (for SL/TP).

        Args:
            position: Position dict
            price: Close price
            reason: "sl" or "tp"
        """
        ticket = position["ticket"]

        # Apply exit slippage (worse fill)
        exit_slippage = self.get_slippage()
        if position["type"] == 0:  # BUY position closing (selling)
            price -= exit_slippage  # Selling gets lower price (worse)
        else:  # SELL position closing (buying)
            price += exit_slippage  # Buying gets higher price (worse)

        # Store exit slippage for trade record
        if ticket in self._open_positions:
            self._open_positions[ticket]["exit_slippage"] = exit_slippage

        # Calculate gross profit
        volume = position["volume"]
        if position["type"] == 0:  # BUY position
            gross_profit = (
                (price - position["price_open"]) * volume * self._get_contract_size()
            )
        else:  # SELL position
            gross_profit = (
                (position["price_open"] - price) * volume * self._get_contract_size()
            )

        # Calculate commission (per lot * volume)
        trade_commission = self._calculate_commission(volume)

        # Calculate swap fees based on overnight rollovers
        trade_swap = 0.0
        if ticket in self._open_positions:
            entry_data = self._open_positions[ticket]
            exit_time = (
                self.execution_data.index[self._current_bar_index]
                if self.execution_data is not None
                else datetime.now()
            )
            if isinstance(exit_time, pd.Timestamp):
                exit_time = exit_time.to_pydatetime()
            trade_swap = self._calculate_swap(
                position_type=position["type"],
                volume=volume,
                entry_time=entry_data["entry_time"],
                exit_time=exit_time,
                entry_price=position["price_open"],
                current_price=price,
            )

        # Calculate net profit (commission and swap are already negative values)
        logger.debug(
            f"P&L calc: gross={gross_profit:.2f}, comm={trade_commission:.2f}, swap={trade_swap:.2f}"
        )
        profit = gross_profit + trade_commission + trade_swap
        logger.debug(f"P&L result: {profit:.2f}")

        # Update account balance with net profit
        # pylint: disable=protected-access
        self._trade_provider._balance += profit
        self._trade_provider._equity = self._trade_provider._balance

        # Record trade before closing
        self._record_position_close(position, price, reason)

        # Remove from open positions
        # pylint: disable=protected-access
        if ticket in self._trade_provider._positions:
            del self._trade_provider._positions[ticket]

        # Get current bar time for logging
        # Use execution data index
        bar_time = (
            self.execution_data.index[self._current_bar_index]
            if self.execution_data is not None
            else datetime.now()
        )
        if isinstance(bar_time, pd.Timestamp):
            bar_time = bar_time.to_pydatetime()

        position_type = "BUY" if position["type"] == 0 else "SELL"
        logger.info(
            f"[{bar_time}] Position #{ticket} ({position_type}) closed at {price:.5f} via {reason.upper()} "
            f"(P&L: ${profit:.2f}, Volume: {volume}, Slippage: {exit_slippage:.5f})"
        )

    def _execute_signal(
        self,
        signal_info: SignalDict,
        bar: pd.Series,
        price: Optional[float] = None,
    ) -> None:
        """
        Execute signal from strategy.

        Args:
            signal_info: SignalDict
            bar: Current bar
            price: Optional execution price
        """
        execution_price = price if price is not None else bar["close"]

        # 1. Handle Exit Signals
        # Note: We process exits before entries to allow "Reverse" logic (Close then Open)
        if signal_info.get("exit_signal", 0) != 0:
            self._handle_exit_signal(signal_info, execution_price, bar)

        # 2. Handle Cancel Pending
        if signal_info.get("cancel_pending_signal", 0) != 0:
            self._process_cancel_signal(signal_info)

        # 3. Handle Entry Signals
        if signal_info.get("entry_signal", 0) != 0 and self._process_entry_signal(
            signal_info, execution_price, bar
        ):
            self._open_position(signal_info, bar, price=execution_price)

        # 4. Handle Pending Signals
        if signal_info.get("pending_signal", 0) != 0:
            self._process_pending_signal(signal_info, bar)

    def _handle_exit_signal(
        self,
        signal_info: SignalDict,
        execution_price: float,
        bar: pd.Series,
    ) -> bool:
        """Check and handle exit signals."""
        exit_val = signal_info.get("exit_signal", 0)

        # 1 = Exit Buy (Close Long)
        # -1 = Exit Sell (Close Short)
        is_exit_buy = exit_val == 1
        is_exit_sell = exit_val == -1

        if not (is_exit_buy or is_exit_sell):
            return False

        # pylint: disable=protected-access
        if not self._trade_provider._positions:
            return True

        # Process all matching positions (FIFO or All) - currently strictly one-dict approach
        # The mock provider stores dict of positions, but basic strategy often assumes single position

        # Copy values to safely iterate if needed, though we break inside
        positions = list(self._trade_provider._positions.values())

        for pos_dict in positions:
            ticket = pos_dict["ticket"]
            pos_type = pos_dict["type"]  # 0=Buy, 1=Sell

            if (is_exit_buy and pos_type == 0) or (is_exit_sell and pos_type == 1):
                if self.strategy.trade is None:
                    raise RuntimeError("trade object must be injected by engine")

                success = self.strategy.trade.position_close(ticket=ticket)

                if success:
                    self._record_position_close(pos_dict, execution_price, "signal")
                    position_type = "BUY" if pos_type == 0 else "SELL"
                    bar_time = (
                        bar.name
                        if isinstance(bar.name, datetime)
                        else bar.name.to_pydatetime()
                    )
                    logger.info(
                        f"[{bar_time}] Position #{ticket} ({position_type}) closed via exit signal ({exit_val}) at {execution_price:.5f}"
                    )
        return True

    def _process_entry_signal(
        self, signal_info: SignalDict, price: float, bar: pd.Series
    ) -> bool:
        """
        Process entry signals and manage existing positions.

        Returns True if a new position should be opened.
        """
        entry_val = signal_info.get("entry_signal", 0)

        # 1 = Buy
        # -1 = Sell
        if entry_val not in [1, -1]:
            return False

        # pylint: disable=protected-access
        # Check existing positions
        if len(self._trade_provider._positions) > 0:
            # Simple assumption: Only 1 position allows for now in this logic
            # OR flip logic

            # Iterate positions to see if we need to flip
            # For now, simplistic approach matching previous logic:
            pos_dict = next(iter(self._trade_provider._positions.values()))
            current_is_buy = pos_dict["type"] == 0
            signal_is_buy = entry_val == 1

            if current_is_buy == signal_is_buy:
                # Same direction, do not open new (simplistic)
                return False

            # Opposite direction, try to close (Flip)
            ticket = pos_dict["ticket"]
            if self.strategy.trade is None:
                raise RuntimeError("trade object must be injected by engine")

            success = self.strategy.trade.position_close(ticket=ticket)

            if success:
                self._record_position_close(pos_dict, price, "signal")
                position_type = "BUY" if pos_dict["type"] == 0 else "SELL"
                bar_time = (
                    bar.name
                    if isinstance(bar.name, datetime)
                    else bar.name.to_pydatetime()
                )
                logger.info(
                    f"[{bar_time}] Position #{ticket} ({position_type}) closed via opposite signal at {price:.5f}"
                )
                return True  # Now proceed to open new
            else:
                return False  # Failed to close, so don't open new

        return True

    def _process_pending_signal(self, signal_info: SignalDict, bar: pd.Series) -> None:
        """Process pending order signals."""
        pending_val = signal_info.get("pending_signal", 0)
        price = float(signal_info.get("price") or 0.0)
        sl = signal_info.get("stop_loss", 0.0) or 0.0
        tp = signal_info.get("take_profit", 0.0) or 0.0

        # Map pending signal to OrderType
        # 1: Buy Stop, -1: Sell Stop, 2: Buy Limit, -2: Sell Limit
        order_type = OrderType.UNKNOWN
        if pending_val == 1:
            order_type = OrderType.BUY_STOP
        elif pending_val == -1:
            order_type = OrderType.SELL_STOP
        elif pending_val == 2:
            order_type = OrderType.BUY_LIMIT
        elif pending_val == -2:
            order_type = OrderType.SELL_LIMIT

        if order_type == OrderType.UNKNOWN:
            return

        # Calculate volume
        volume = self._calculate_position_size(bar, price, sl)

        # Add order
        ticket = self._next_trade_id
        self._next_trade_id += 1

        self._order_provider.add_order(
            ticket=ticket,
            time_setup=datetime.now(),  # Mock time
            order_type=order_type,
            state=OrderState.PLACED,
            symbol=self.strategy.symbol,
            volume_initial=volume,
            volume_current=volume,
            price_open=price,
            stop_loss=sl,
            take_profit=tp,
            magic=self._get_magic_number(),
            comment="Pending Order",
        )
        logger.info(f"Pending order placed: {order_type} @ {price}")

    def _process_cancel_signal(self, signal_info: SignalDict) -> None:
        """Cancel pending orders."""
        # Simple implementation: Cancel all if signal is generic, or match magic/type if needed
        # For now, simplistic "cancel all" if cancel_signal is present
        self._order_provider.clear_orders()
        logger.info("All pending orders cancelled by signal")

    def _open_position(
        self, signal_info: SignalDict, bar: pd.Series, price: Optional[float] = None
    ) -> None:
        """
        Open new position from signal.

        Args:
            signal_info: Signal dict
            bar: Current bar
            price: Optional execution price
        """
        entry_price, entry_slippage, is_buy = self._calculate_entry_price(
            signal_info, bar, price
        )
        stop_loss = signal_info.get("stop_loss") or 0.0
        take_profit = signal_info.get("take_profit") or 0.0

        volume = self._calculate_position_size(bar, entry_price, stop_loss)
        contract_size = self._get_contract_size()

        if not self._check_margin(volume, entry_price, contract_size, bar):
            return

        success, ticket = self._execute_trade_order(
            is_buy, volume, stop_loss, take_profit, entry_price
        )

        if success and ticket is not None:
            margin_required = self.calculate_required_margin(
                volume, entry_price, contract_size
            )
            self._record_new_position(
                ticket,
                entry_price,
                volume,
                is_buy,
                stop_loss,
                take_profit,
                entry_slippage,
                margin_required,
                bar,
                entry_slippage,
            )
        else:
            bar_time = (
                bar.name if isinstance(bar.name, datetime) else bar.name.to_pydatetime()
            )
            direction_str = "LONG" if is_buy else "SHORT"
            logger.error(
                f"[{bar_time}] Failed to open {direction_str} position at {entry_price:.5f}"
            )

    def _calculate_entry_price(
        self, signal_info: SignalDict, bar: pd.Series, price: Optional[float]
    ) -> Tuple[float, float, bool]:
        entry_val = signal_info.get("entry_signal", 0)
        is_buy = entry_val == 1

        if price is not None:
            entry_price = price
        else:
            # Use 'price' from SignalDict, fallback to 'entry_price' (legacy) or bar close
            raw_price = (
                signal_info.get("price")
                or signal_info.get("entry_price")
                or bar.get("close", 0.0)
            )
            entry_price = float(cast(Any, raw_price)) if raw_price is not None else 0.0

        entry_slippage = self.get_slippage()
        if is_buy:
            entry_price += entry_slippage
        else:
            entry_price -= entry_slippage

        return entry_price, entry_slippage, is_buy

    def _calculate_position_size(
        self, bar: pd.Series, entry_price: float, stop_loss: float
    ) -> float:
        if self.position_sizer:
            context = {}
            atr_period = self.config.get("atr_period", 14)
            atr_col = f"atr_{atr_period}"
            if atr_col in bar.index:
                context["atr"] = bar[atr_col]

            return float(
                self.position_sizer.calculate_size(
                    account_balance=self._account_provider.get_balance(),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    symbol_info=self._symbol_provider,
                    context=context,
                )
            )
        return 0.1

    def _check_margin(
        self, volume: float, entry_price: float, contract_size: float, bar: pd.Series
    ) -> bool:
        current_balance = self._account_provider.get_balance()
        if not self.has_sufficient_margin(
            volume, entry_price, contract_size, current_balance
        ):
            bar_time = (
                bar.name if isinstance(bar.name, datetime) else bar.name.to_pydatetime()
            )
            logger.warning(
                f"[{bar_time}] Insufficient margin to open position. "
                f"Required: ${self.calculate_required_margin(volume, entry_price, contract_size):.2f}, "
                f"Available: ${self.get_free_margin(current_balance):.2f}"
            )
            return False
        return True

    def _execute_trade_order(
        self,
        is_buy: bool,
        volume: float,
        stop_loss: float,
        take_profit: float,
        entry_price: float,
    ) -> Tuple[bool, Optional[int]]:
        if self.strategy.trade is None:
            raise RuntimeError("trade object must be injected by engine")

        self._trade_provider.set_symbol_price(
            self.strategy.symbol, entry_price, entry_price
        )

        if is_buy:
            success = self.strategy.trade.buy(
                volume, self.strategy.symbol, sl=stop_loss, tp=take_profit
            )
        else:
            success = self.strategy.trade.sell(
                volume, self.strategy.symbol, sl=stop_loss, tp=take_profit
            )

        ticket = None
        # pylint: disable=protected-access
        if success and len(self._trade_provider._positions) > 0:
            pos_dict = next(iter(self._trade_provider._positions.values()))
            ticket = pos_dict["ticket"]

        return success, ticket

    def _record_new_position(
        self,
        ticket: int,
        entry_price: float,
        volume: float,
        is_buy: bool,
        stop_loss: float,
        take_profit: float,
        entry_slippage: float,
        margin_required: float,
        bar: pd.Series,
        slippage_for_entry: float,
    ) -> None:

        if self._first_trade_open is None:
            self._first_trade_open = entry_price
            self._first_trade_size = volume

        # pylint: disable=protected-access
        if len(self._trade_provider._positions) > 0:
            pos_dict = next(iter(self._trade_provider._positions.values()))
            # Ensure it matches the ticket we think it is (it should)
            if pos_dict["ticket"] != ticket:
                # This would be weird but let's just stick to the pos_dict we found
                ticket = pos_dict["ticket"]

            pos_dict["price_open"] = entry_price

            current_balance = self._account_provider.get_balance()

            self._open_positions[ticket] = {
                "entry_time": (
                    bar.name.to_pydatetime()
                    if isinstance(bar.name, pd.Timestamp)
                    else bar.name
                ),
                "entry_price": entry_price,
                "entry_sl": stop_loss,
                "entry_tp": take_profit,
                "direction": "long" if is_buy else "short",
                "size": volume,
                "entry_bar_index": self._current_bar_index,
                "highest_price": entry_price,
                "lowest_price": entry_price,
                "entry_slippage": slippage_for_entry,
                "margin_required": margin_required,
                "equity_at_entry": current_balance,
                "spread_at_entry": self.get_spread(bar),
            }

            self._used_margin += margin_required

            bar_time = (
                bar.name if isinstance(bar.name, datetime) else bar.name.to_pydatetime()
            )
            direction_str = "LONG" if is_buy else "SHORT"

            sl_str = f"{stop_loss:.5f}" if stop_loss > 0 else "None"
            tp_str = f"{take_profit:.5f}" if take_profit > 0 else "None"

            logger.info(
                f"[{bar_time}] Position #{ticket} opened: {direction_str} {volume} lots @ {entry_price:.5f} "
                f"(SL: {sl_str}, TP: {tp_str}, Balance: ${current_balance:.2f})"
            )

    def _record_position_close(
        self, position: Dict[str, Any], exit_price: float, exit_reason: str
    ) -> None:  # noqa: C901
        """
        Record a closed trade.

        Args:
            position: Position dict
            exit_price: Exit price
            exit_reason: Reason for exit
        """
        if self._data_with_signals is None:
            raise RuntimeError("Data with signals must be available")

        ticket = position["ticket"]

        if ticket not in self._open_positions:
            logger.warning(f"Position {ticket} not found in open positions tracking")
            return

        entry_data = self._open_positions[ticket]

        # Calculate total slippage cost
        entry_slippage = entry_data.get("entry_slippage", 0.0)
        exit_slippage = entry_data.get("exit_slippage", 0.0)
        total_slippage = entry_slippage + exit_slippage
        slippage_usd = total_slippage * entry_data["size"] * self._get_contract_size()

        # Calculate P&L
        if position["type"] == 0:  # BUY
            pnl = (
                (exit_price - entry_data["entry_price"])
                * entry_data["size"]
                * self._get_contract_size()
            )
        else:  # SELL
            pnl = (
                (entry_data["entry_price"] - exit_price)
                * entry_data["size"]
                * self._get_contract_size()
            )

        # Calculate duration
        # Use execution data index
        exit_time = self.execution_data.index[self._current_bar_index]
        if isinstance(exit_time, pd.Timestamp):
            exit_time = exit_time.to_pydatetime()

        duration_hours = (
            exit_time - entry_data["entry_time"]
        ).total_seconds() / 3600  # hours

        # Calculate commission (per lot * volume)
        trade_commission = self._calculate_commission(entry_data["size"])

        # Calculate swap fees based on overnight rollovers
        trade_swap = self._calculate_swap(
            position_type=position["type"],
            volume=entry_data["size"],
            entry_time=entry_data["entry_time"],
            exit_time=exit_time,
            entry_price=entry_data["entry_price"],
            current_price=exit_price,
        )

        # Calculate profit metrics
        gross_pnl = pnl  # P&L before commission/swap
        net_pnl = (
            pnl + trade_commission + trade_swap
        )  # P&L after commission/swap (both are negative for costs)

        # Calculate profit in pips dynamically based on symbol digits
        # Get symbol point value (smallest price change)
        point = self._symbol_provider.get_point()
        digits = self._symbol_provider.get_digits()

        # Calculate pip value based on digits
        # - 5-digit pairs (EURUSD): pip = 0.0001 (4th decimal)
        # - 3-digit pairs (USDJPY): pip = 0.01 (2nd decimal)
        # - 2-digit pairs (indices): pip = 1.0 (1st decimal)
        if digits >= 2:
            pip_value = point * 10  # 5/3/2-digit pairs: pip = point * 10
        else:
            pip_value = 1.0  # Default for indices/commodities

        price_diff = (
            exit_price - entry_data["entry_price"]
            if entry_data["direction"] == "long"
            else entry_data["entry_price"] - exit_price
        )
        profit_pips = price_diff / pip_value

        # Update balance
        self._account_provider._balance = (
            self._trade_provider._balance
        )  # pylint: disable=protected-access

        # Calculate cumulative pips
        cumulative_pips = (
            sum(t.profit_loss_pips for t in self._trade_records) + profit_pips
        )

        # Calculate trade bars
        trade_bars = self._current_bar_index - self._open_positions.get(ticket, {}).get(
            "entry_bar_index", self._current_bar_index
        )

        # Calculate risk multiple (if SL was set)
        initial_risk = 0.0
        r_multiple = 0.0
        if entry_data.get("entry_sl"):
            sl_distance = abs(entry_data["entry_price"] - entry_data["entry_sl"])
            initial_risk = sl_distance * entry_data["size"] * self._get_contract_size()
            if initial_risk > 0:
                r_multiple = gross_pnl / initial_risk

        # Calculate MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)
        # These show the worst drawdown and best profit during the trade
        highest_price = entry_data.get("highest_price", entry_data["entry_price"])
        lowest_price = entry_data.get("lowest_price", entry_data["entry_price"])

        if entry_data["direction"] == "long":
            # For long: MAE is how far price went down, MFE is how far it went up
            mae = (entry_data["entry_price"] - lowest_price) / pip_value
            mfe = (highest_price - entry_data["entry_price"]) / pip_value
        else:  # short
            # For short: MAE is how far price went up, MFE is how far it went down
            mae = (highest_price - entry_data["entry_price"]) / pip_value
            mfe = (entry_data["entry_price"] - lowest_price) / pip_value

            mfe = (entry_data["entry_price"] - lowest_price) / pip_value

        # Calculate drawdown at exit
        current_equity = self._account_provider.get_equity()
        drawdown = max(0.0, self._peak_equity - current_equity)

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

        # Create trade record
        trade = TradeRecord(
            # 1️⃣ Trade Identification & Attribution
            trade_id=None,  # Could use UUID here
            ticket=self._next_trade_id,
            symbol=position["symbol"],
            type="buy" if entry_data["direction"] == "long" else "sell",
            magic_number=self._get_magic_number(),
            strategy_name=self.strategy.__class__.__name__,
            setup=None,
            sample_type=None,
            comment="",
            # 2️⃣ Strategy Context
            signal_timeframe=self.timeframe,
            execution_timeframe=self.timeframe,
            session=None,
            day_of_week=(
                entry_data["entry_time"].weekday() if entry_data["entry_time"] else None
            ),
            hour_of_day=(
                entry_data["entry_time"].hour if entry_data["entry_time"] else None
            ),
            # 3️⃣ Trade Timing
            open_time=entry_data["entry_time"],
            close_time=exit_time,
            time_in_trade=duration_hours,
            bars_in_trade=trade_bars,
            # 4️⃣ Entry Definition
            open_price=entry_data["entry_price"],
            requested_entry_price=(
                entry_data["entry_price"] - entry_data.get("entry_slippage", 0.0)
                if entry_data.get("direction") == "long"
                else entry_data["entry_price"] + entry_data.get("entry_slippage", 0.0)
            ),
            spread_at_entry=entry_data.get("spread_at_entry", 0.0),
            size=entry_data["size"],
            # 5️⃣ Exit Definition
            close_price=exit_price,
            requested_exit_price=exit_price,
            close_type=exit_reason.upper() if exit_reason else "UNKNOWN",
            exit_reason=exit_reason.upper() if exit_reason else "UNKNOWN",
            # 6️⃣ Trade Plan & Risk
            stop_loss_price_level=entry_data.get("entry_sl", 0.0),
            profit_target_price_level=entry_data.get("entry_tp", 0.0),
            initial_risk_pips=(
                abs(
                    entry_data["entry_price"]
                    - entry_data.get("entry_sl", entry_data["entry_price"])
                )
                / pip_value
                if entry_data.get("entry_sl")
                else 0.0
            ),
            initial_risk_usd=initial_risk,
            # 7️⃣ Account State
            balance_at_entry=entry_data.get(
                "equity_at_entry", 0.0
            ),  # Use stored equity at entry as balance at entry reference or equity?
            equity_at_entry=entry_data.get("equity_at_entry", 0.0),
            margin_used=entry_data.get("margin_required", 0.0),
            free_margin=entry_data.get("equity_at_entry", 0.0)
            - entry_data.get("margin_required", 0.0),
            balance_pips=cumulative_pips,
            # 8️⃣ Trade Management
            max_position_size_reached=entry_data["size"],
            partial_close_count=0,
            trailing_stop_used=False,
            breakeven_triggered=False,
            # 9️⃣ Execution Quality
            slippage_usd=slippage_usd,
            fill_price_deviation=entry_data.get("entry_slippage", 0.0),
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
            mae_usd=mae * entry_data["size"] * self._get_contract_size() * pip_value,
            mae_pips=mae,
            mfe_usd=mfe * entry_data["size"] * self._get_contract_size() * pip_value,
            mfe_pips=mfe,
            # 1️⃣2️⃣ Regime & Research Tags
            market_regime=None,
            volatility_bucket=None,
            correlation_cluster=None,
            drawdown=drawdown,
            # 1️⃣3️⃣ Compliance & Audit
            rule_violation_flag=False,
            manual_intervention=False,
        )

        self._record_trade(trade)
        self._next_trade_id += 1

        # Release margin before removing position
        margin_to_release = entry_data.get("margin_required", 0.0)
        self._used_margin -= margin_to_release
        self._used_margin = max(0.0, self._used_margin)  # Ensure non-negative

        # Remove from open positions
        del self._open_positions[ticket]

    def _close_all_positions(self) -> None:
        """Close all open positions at the end of backtest."""
        if self._data_with_signals is None or len(self._data_with_signals) == 0:
            return

        # Use last bar's CLOSE price
        last_bar = self._data_with_signals.iloc[-1]
        close_price = last_bar["close"]

        # Copy values to avoid "dictionary changed size during iteration"
        # pylint: disable=protected-access
        positions = list(self._trade_provider._positions.values())

        if positions:
            logger.info(
                f"Closing {len(positions)} open positions at end of data (Price: {close_price})"
            )
            for pos in positions:
                self._close_position_at_price(pos, close_price, "end_of_data")
