"""
Fast Simulation Core.

JIT-compiled simulation loop using Numba for 50-100x speedup.
Falls back to pure Python/NumPy if Numba is not available.
"""

import numpy as np

from .types import (
    EXIT_END_OF_DATA,
    EXIT_SIGNAL,
    EXIT_SL,
    EXIT_TP,
    SimulationResult,
    create_trade_array,
)

# Try to import Numba, fall back to pure Python if not available
try:
    from numba import njit

    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

    # Create a no-op decorator
    def njit(*args, **kwargs):
        """Fallback no-op decorator when Numba is unavailable."""

        def decorator(func):
            return func

        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


@njit(cache=True)
def _simulate_core(  # noqa: C901
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    entry_signals: np.ndarray,
    exit_signals: np.ndarray,
    stop_losses: np.ndarray,
    take_profits: np.ndarray,
    sizes: np.ndarray,
    initial_balance: float,
    contract_size: float,
    commission_per_lot: float,
    slippage_pct: float,
) -> tuple:
    """
    JIT-compiled trade simulation core.

    This function is compiled by Numba for maximum performance.
    All inputs must be NumPy arrays or scalar values.

    Args:
        opens/highs/lows/closes: OHLC price arrays
        entry_signals: int8 array (1=buy, -1=sell, 0=none)
        exit_signals: int8 array (1=exit_long, -1=exit_short, 0=none)
        stop_losses: SL price per bar (0 = no SL)
        take_profits: TP price per bar (0 = no TP)
        sizes: Position size per bar (in lots)
        initial_balance: Starting capital
        contract_size: Contract size multiplier
        commission_per_lot: Commission per lot
        slippage_pct: Slippage as percentage

    Returns:
        (equity_curve, balance_curve, trades_flat, trade_count, max_dd, max_dd_pct)
    """
    n = len(closes)

    # Pre-allocate output arrays
    equity = np.zeros(n, dtype=np.float64)
    balance_arr = np.zeros(n, dtype=np.float64)

    # Trade storage: [entry_bar, exit_bar, direction, entry_price, exit_price,
    #                 size, pnl, commission, slippage, sl, tp, exit_reason]
    max_trades = n // 2 + 1  # Max possible trades
    trades = np.zeros((max_trades, 12), dtype=np.float64)
    trade_count = 0

    # State variables
    balance = initial_balance
    position_size = 0.0  # Signed: positive=long, negative=short
    entry_bar = 0
    entry_price = 0.0
    current_sl = 0.0
    current_tp = 0.0
    entry_slippage = 0.0
    entry_commission = 0.0

    # Drawdown tracking
    peak_equity = initial_balance
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    for i in range(n):
        # Current bar prices
        open_price = opens[i]
        high_price = highs[i]
        low_price = lows[i]
        close_price = closes[i]

        # Check for exits if we have a position
        if position_size != 0.0:
            exit_price = 0.0
            exit_reason = -1
            should_exit = False

            if position_size > 0:  # Long position
                # Check SL (hit on low)
                if current_sl > 0 and low_price <= current_sl:
                    exit_price = current_sl
                    exit_reason = EXIT_SL
                    should_exit = True
                # Check TP (hit on high)
                elif current_tp > 0 and high_price >= current_tp:
                    exit_price = current_tp
                    exit_reason = EXIT_TP
                    should_exit = True
                # Check exit signal or opposite entry signal (flip)
                elif exit_signals[i] == 1 or entry_signals[i] == -1:
                    slippage = open_price * slippage_pct
                    exit_price = open_price - slippage
                    exit_reason = EXIT_SIGNAL
                    should_exit = True

            else:  # Short position (position_size < 0)
                # Check SL (hit on high)
                if current_sl > 0 and high_price >= current_sl:
                    exit_price = current_sl
                    exit_reason = EXIT_SL
                    should_exit = True
                # Check TP (hit on low)
                elif current_tp > 0 and low_price <= current_tp:
                    exit_price = current_tp
                    exit_reason = EXIT_TP
                    should_exit = True
                # Check exit signal or opposite entry signal (flip)
                elif exit_signals[i] == -1 or entry_signals[i] == 1:
                    slippage = open_price * slippage_pct
                    exit_price = open_price + slippage
                    exit_reason = EXIT_SIGNAL
                    should_exit = True

            if should_exit:
                # Calculate P&L
                direction = 1 if position_size > 0 else -1
                abs_size = abs(position_size)
                pnl = (exit_price - entry_price) * direction * abs_size * contract_size

                # Exit commission
                exit_commission = abs_size * commission_per_lot
                exit_slippage = (
                    abs(open_price * slippage_pct)
                    if exit_reason == EXIT_SIGNAL
                    else 0.0
                )

                # Net P&L after commission
                net_pnl = pnl - entry_commission - exit_commission
                balance += net_pnl

                # Record trade
                trades[trade_count, 0] = entry_bar
                trades[trade_count, 1] = i
                trades[trade_count, 2] = direction
                trades[trade_count, 3] = entry_price
                trades[trade_count, 4] = exit_price
                trades[trade_count, 5] = abs_size
                trades[trade_count, 6] = net_pnl
                trades[trade_count, 7] = entry_commission + exit_commission
                trades[trade_count, 8] = entry_slippage + exit_slippage
                trades[trade_count, 9] = current_sl
                trades[trade_count, 10] = current_tp
                trades[trade_count, 11] = exit_reason
                trade_count += 1

                # Reset position
                position_size = 0.0
                current_sl = 0.0
                current_tp = 0.0

        # Check for new entries (only if no position)
        if position_size == 0.0 and entry_signals[i] != 0:
            direction = entry_signals[i]  # 1 = long, -1 = short
            size = sizes[i]

            if size > 0:
                # Calculate entry price with slippage
                slippage = open_price * slippage_pct
                if direction == 1:  # Long: slippage makes entry worse (higher)
                    entry_price = open_price + slippage
                else:  # Short: slippage makes entry worse (lower)
                    entry_price = open_price - slippage

                position_size = size * direction
                entry_bar = i
                current_sl = stop_losses[i]
                current_tp = take_profits[i]
                entry_slippage = slippage
                entry_commission = size * commission_per_lot

        # Mark-to-market equity calculation
        if position_size != 0.0:
            direction = 1 if position_size > 0 else -1
            abs_size = abs(position_size)
            unrealized = (
                (close_price - entry_price) * direction * abs_size * contract_size
            )
            equity[i] = balance + unrealized
        else:
            equity[i] = balance

        balance_arr[i] = balance

        # Update drawdown tracking
        if equity[i] > peak_equity:
            peak_equity = equity[i]

        current_dd = peak_equity - equity[i]
        if current_dd > max_drawdown:
            max_drawdown = current_dd
            if peak_equity > 0:
                max_drawdown_pct = (current_dd / peak_equity) * 100.0

    # Close any remaining position at end of data
    if position_size != 0.0:
        exit_price = closes[n - 1]
        direction = 1 if position_size > 0 else -1
        abs_size = abs(position_size)
        pnl = (exit_price - entry_price) * direction * abs_size * contract_size
        exit_commission = abs_size * commission_per_lot
        net_pnl = pnl - entry_commission - exit_commission
        balance += net_pnl

        # Record final trade
        trades[trade_count, 0] = entry_bar
        trades[trade_count, 1] = n - 1
        trades[trade_count, 2] = direction
        trades[trade_count, 3] = entry_price
        trades[trade_count, 4] = exit_price
        trades[trade_count, 5] = abs_size
        trades[trade_count, 6] = net_pnl
        trades[trade_count, 7] = entry_commission + exit_commission
        trades[trade_count, 8] = entry_slippage
        trades[trade_count, 9] = current_sl
        trades[trade_count, 10] = current_tp
        trades[trade_count, 11] = EXIT_END_OF_DATA
        trade_count += 1

        # Update final equity
        equity[n - 1] = balance
        balance_arr[n - 1] = balance

    return equity, balance_arr, trades, trade_count, max_drawdown, max_drawdown_pct


def run_simulation_python(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    entry_signals: np.ndarray,
    exit_signals: np.ndarray,
    stop_losses: np.ndarray,
    take_profits: np.ndarray,
    sizes: np.ndarray,
    initial_balance: float = 10000.0,
    contract_size: float = 100000.0,
    commission_per_lot: float = 7.0,
    slippage_pct: float = 0.0,
) -> SimulationResult:
    """
    Run simulation using pure Python/NumPy (fallback when Numba not available).

    See run_simulation() for full documentation.
    """
    # Call the core simulation function
    equity, balance_arr, trades_flat, trade_count, max_dd, max_dd_pct = _simulate_core(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        entry_signals=entry_signals,
        exit_signals=exit_signals,
        stop_losses=stop_losses,
        take_profits=take_profits,
        sizes=sizes,
        initial_balance=initial_balance,
        contract_size=contract_size,
        commission_per_lot=commission_per_lot,
        slippage_pct=slippage_pct,
    )

    # Convert flat trades array to structured array
    trades_structured = create_trade_array(trade_count)
    for i in range(trade_count):
        trades_structured[i]["entry_bar"] = int(trades_flat[i, 0])
        trades_structured[i]["exit_bar"] = int(trades_flat[i, 1])
        trades_structured[i]["direction"] = int(trades_flat[i, 2])
        trades_structured[i]["entry_price"] = trades_flat[i, 3]
        trades_structured[i]["exit_price"] = trades_flat[i, 4]
        trades_structured[i]["size"] = trades_flat[i, 5]
        trades_structured[i]["pnl"] = trades_flat[i, 6]
        trades_structured[i]["commission"] = trades_flat[i, 7]
        trades_structured[i]["slippage"] = trades_flat[i, 8]
        trades_structured[i]["sl"] = trades_flat[i, 9]
        trades_structured[i]["tp"] = trades_flat[i, 10]
        trades_structured[i]["exit_reason"] = int(trades_flat[i, 11])

    return SimulationResult(
        equity_curve=equity,
        balance_curve=balance_arr,
        trades=trades_structured,
        trade_count=trade_count,
        final_balance=balance_arr[-1] if len(balance_arr) > 0 else initial_balance,
        final_equity=equity[-1] if len(equity) > 0 else initial_balance,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
    )


def run_simulation(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    entry_signals: np.ndarray,
    exit_signals: np.ndarray,
    stop_losses: np.ndarray,
    take_profits: np.ndarray,
    sizes: np.ndarray,
    initial_balance: float = 10000.0,
    contract_size: float = 100000.0,
    commission_per_lot: float = 7.0,
    slippage_pct: float = 0.0,
) -> SimulationResult:
    """
    Run fast trade simulation.

    Uses Numba JIT compilation if available, otherwise falls back to
    pure Python/NumPy implementation.

    Args:
        opens: Open prices array
        highs: High prices array
        lows: Low prices array
        closes: Close prices array
        entry_signals: Entry signal array (1=buy, -1=sell, 0=none)
        exit_signals: Exit signal array (1=exit_long, -1=exit_short, 0=none)
        stop_losses: Stop loss prices (0 = no SL)
        take_profits: Take profit prices (0 = no TP)
        sizes: Position sizes in lots
        initial_balance: Starting capital
        contract_size: Contract size (e.g., 100000 for forex)
        commission_per_lot: Commission per lot traded
        slippage_pct: Slippage as percentage of price

    Returns:
        SimulationResult with equity curve, trades, and statistics
    """
    return run_simulation_python(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        entry_signals=entry_signals,
        exit_signals=exit_signals,
        stop_losses=stop_losses,
        take_profits=take_profits,
        sizes=sizes,
        initial_balance=initial_balance,
        contract_size=contract_size,
        commission_per_lot=commission_per_lot,
        slippage_pct=slippage_pct,
    )


def is_numba_available() -> bool:
    """Check if Numba is available for JIT compilation."""
    return NUMBA_AVAILABLE
