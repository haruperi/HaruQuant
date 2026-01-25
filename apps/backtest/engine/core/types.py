"""
Core Data Types for Fast Simulation.

NumPy-friendly data structures optimized for Numba JIT compilation.
Uses structured arrays and simple dtypes for maximum performance.
"""

from dataclasses import dataclass

import numpy as np

# Trade result dtype for structured array
TRADE_DTYPE = np.dtype(
    [
        ("entry_bar", np.int64),
        ("exit_bar", np.int64),
        ("direction", np.int8),  # 1=long, -1=short
        ("entry_price", np.float64),
        ("exit_price", np.float64),
        ("size", np.float64),
        ("pnl", np.float64),
        ("commission", np.float64),
        ("slippage", np.float64),
        ("sl", np.float64),
        ("tp", np.float64),
        ("exit_reason", np.int8),  # 0=signal, 1=sl, 2=tp, 3=end_of_data
    ]
)

# Exit reason constants
EXIT_SIGNAL = 0
EXIT_SL = 1
EXIT_TP = 2
EXIT_END_OF_DATA = 3


@dataclass
class SimulationConfig:
    """
    Configuration for fast simulation.

    All values are scalars or simple types that Numba can handle.

    Attributes:
        initial_balance: Starting capital
        contract_size: Contract size for position sizing (e.g., 100000 for forex)
        commission_per_lot: Commission per lot traded
        slippage_pct: Slippage as percentage of price
        max_positions: Maximum concurrent positions allowed
        use_sl_tp: Whether to use stop loss and take profit
    """

    initial_balance: float = 10000.0
    contract_size: float = 100000.0
    commission_per_lot: float = 7.0
    slippage_pct: float = 0.0
    max_positions: int = 1
    use_sl_tp: bool = True


@dataclass
class TradeResult:
    """
    Result of a single trade.

    Mirrors the TRADE_DTYPE structured array fields.
    """

    entry_bar: int
    exit_bar: int
    direction: int  # 1=long, -1=short
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    commission: float
    slippage: float
    sl: float
    tp: float
    exit_reason: int

    @classmethod
    def from_array(cls, arr: np.ndarray, index: int) -> "TradeResult":
        """Create TradeResult from structured array."""
        row = arr[index]
        return cls(
            entry_bar=int(row["entry_bar"]),
            exit_bar=int(row["exit_bar"]),
            direction=int(row["direction"]),
            entry_price=float(row["entry_price"]),
            exit_price=float(row["exit_price"]),
            size=float(row["size"]),
            pnl=float(row["pnl"]),
            commission=float(row["commission"]),
            slippage=float(row["slippage"]),
            sl=float(row["sl"]),
            tp=float(row["tp"]),
            exit_reason=int(row["exit_reason"]),
        )


@dataclass
class SimulationResult:
    """
    Complete simulation results.

    Attributes:
        equity_curve: Equity value at each bar
        balance_curve: Balance (closed P&L) at each bar
        trades: Array of trade results (structured array)
        trade_count: Number of trades executed
        final_balance: Final account balance
        final_equity: Final account equity
        max_drawdown: Maximum drawdown in currency
        max_drawdown_pct: Maximum drawdown as percentage
    """

    equity_curve: np.ndarray
    balance_curve: np.ndarray
    trades: np.ndarray  # Structured array with TRADE_DTYPE
    trade_count: int
    final_balance: float
    final_equity: float
    max_drawdown: float
    max_drawdown_pct: float

    def get_trade(self, index: int) -> TradeResult:
        """Get a single trade result."""
        if index >= self.trade_count:
            raise IndexError(
                f"Trade index {index} out of range (0-{self.trade_count-1})"
            )
        return TradeResult.from_array(self.trades, index)

    def get_all_trades(self) -> list:
        """Get all trades as list of TradeResult."""
        return [self.get_trade(i) for i in range(self.trade_count)]


def create_trade_array(max_trades: int) -> np.ndarray:
    """Create pre-allocated trade result array."""
    return np.zeros(max_trades, dtype=TRADE_DTYPE)


def create_signal_arrays(n_bars: int) -> dict:
    """
    Create pre-allocated signal arrays.

    Returns:
        dict with:
            - entry_signals: int8 array (1=buy, -1=sell, 0=none)
            - exit_signals: int8 array (1=exit_long, -1=exit_short, 0=none)
            - stop_losses: float64 array
            - take_profits: float64 array
            - sizes: float64 array
    """
    return {
        "entry_signals": np.zeros(n_bars, dtype=np.int8),
        "exit_signals": np.zeros(n_bars, dtype=np.int8),
        "stop_losses": np.zeros(n_bars, dtype=np.float64),
        "take_profits": np.zeros(n_bars, dtype=np.float64),
        "sizes": np.zeros(n_bars, dtype=np.float64),
    }
