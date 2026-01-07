"""
Backtest Result.

Data structure for capturing backtest outcomes.
Stores all events, state changes, and trade history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

from apps.finance import drawdowns, efficiency, metrics, ratios, returns, risks

# =========================================================================
# Canonical Enums
# =========================================================================


class CloseType(str, Enum):
    """Canonical close type strings."""

    TP = "TP"
    SL = "SL"
    TIME_EXIT = "TIME_EXIT"
    SIGNAL_EXIT = "SIGNAL_EXIT"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    TRAILING_STOP = "TRAILING_STOP"
    BREAKEVEN_STOP = "BREAKEVEN_STOP"
    MARGIN_CLOSE = "MARGIN_CLOSE"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    UNKNOWN = "UNKNOWN"


class ExitReason(str, Enum):
    """Canonical exit reason strings."""

    STRATEGY_EXIT = "STRATEGY_EXIT"
    RISK_EXIT = "RISK_EXIT"
    SESSION_END = "SESSION_END"
    TIMEOUT = "TIMEOUT"
    BROKER_EVENT = "BROKER_EVENT"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class TradeEventType(str, Enum):
    """Canonical trade event type strings."""

    OPEN = "OPEN"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    MOVE_SL = "MOVE_SL"
    MOVE_TP = "MOVE_TP"
    SET_BREAKEVEN = "SET_BREAKEVEN"
    TRAILING_UPDATE = "TRAILING_UPDATE"
    FEE_APPLIED = "FEE_APPLIED"


class Session(str, Enum):
    """Canonical trading session strings."""

    ASIA = "ASIA"
    LONDON = "LONDON"
    NEWYORK = "NEWYORK"
    OVERLAP_LONDON_NY = "OVERLAP_LONDON_NY"
    OFF_HOURS = "OFF_HOURS"


# =========================================================================
# Trade Record
# =========================================================================


@dataclass
class TradeRecord:
    """
    Record of a completed trade.

    Captures full trade lifecycle from entry to exit.
    Works for both backtesting and live trading.
    Some fields will return None/0 when not applicable.
    """

    # ═════════════════════════════════════════════════════════════════════
    # 1️⃣ Trade Identification & Attribution
    # ═════════════════════════════════════════════════════════════════════
    trade_id: Optional[str] = None  # Internal UUID
    ticket: int = 0  # Broker ticket number
    symbol: str = ""
    type: str = "buy"  # Buy / Sell
    magic_number: int = 0  # Magic number identifier
    strategy_name: Optional[str] = None
    setup: Optional[str] = None  # Entry setup name/pattern
    sample_type: Optional[str] = None  # IS / OOS / WFO
    comment: str = ""

    # ═════════════════════════════════════════════════════════════════════
    # 2️⃣ Strategy Context
    # ═════════════════════════════════════════════════════════════════════
    signal_timeframe: Optional[str] = None
    execution_timeframe: Optional[str] = None
    session: Optional[str] = None  # ASIA / LONDON / NEWYORK
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    hour_of_day: Optional[int] = None  # 0-23

    # ═════════════════════════════════════════════════════════════════════
    # 3️⃣ Trade Timing
    # ═════════════════════════════════════════════════════════════════════
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    time_in_trade: float = 0.0  # Duration in hours
    bars_in_trade: int = 0  # Number of bars the trade was open

    # ═════════════════════════════════════════════════════════════════════
    # 4️⃣ Entry Definition
    # ═════════════════════════════════════════════════════════════════════
    open_price: float = 0.0
    requested_entry_price: float = 0.0  # Limit/stop price (if applicable)
    spread_at_entry: float = 0.0  # Spread in pips
    size: float = 0.0  # Volume in lots

    # ═════════════════════════════════════════════════════════════════════
    # 5️⃣ Exit Definition
    # ═════════════════════════════════════════════════════════════════════
    close_price: float = 0.0
    requested_exit_price: float = 0.0  # Limit/stop price (if applicable)
    close_type: str = CloseType.UNKNOWN.value  # TP, SL, SIGNAL_EXIT, etc.
    exit_reason: str = ExitReason.UNKNOWN.value  # STRATEGY_EXIT, RISK_EXIT, etc.

    # ═════════════════════════════════════════════════════════════════════
    # 6️⃣ Trade Plan & Risk
    # ═════════════════════════════════════════════════════════════════════
    stop_loss_price_level: float = 0.0
    profit_target_price_level: float = 0.0
    initial_risk_pips: float = 0.0
    initial_risk_usd: float = 0.0

    # ═════════════════════════════════════════════════════════════════════
    # 7️⃣ Account State
    # ═════════════════════════════════════════════════════════════════════
    balance_at_entry: float = 0.0
    equity_at_entry: float = 0.0
    margin_used: float = 0.0
    free_margin: float = 0.0
    balance_pips: float = 0.0  # Cumulative profit in pips

    # ═════════════════════════════════════════════════════════════════════
    # 8️⃣ Trade Management
    # ═════════════════════════════════════════════════════════════════════
    max_position_size_reached: float = 0.0
    partial_close_count: int = 0
    trailing_stop_used: bool = False
    breakeven_triggered: bool = False

    # ═════════════════════════════════════════════════════════════════════
    # 9️⃣ Execution Quality
    # ═════════════════════════════════════════════════════════════════════
    slippage_usd: float = 0.0
    fill_price_deviation: float = 0.0  # Requested vs actual (pips)
    execution_latency_ms: float = 0.0

    # ═════════════════════════════════════════════════════════════════════
    # 🔟 Performance Results
    # ═════════════════════════════════════════════════════════════════════
    profit_loss: float = 0.0  # Net P&L after commission and swap
    profit_loss_pips: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    r_multiple: float = 0.0  # Profit / initial risk
    buy_hold: float = 0.0  # Buy & Hold Value at time of trade
    buy_hold_pips: float = 0.0  # Buy & Hold Pips at time of trade

    # ═════════════════════════════════════════════════════════════════════
    # 1️⃣1️⃣ Excursion & Drawdown Analytics
    # ═════════════════════════════════════════════════════════════════════
    mae_usd: float = 0.0  # Maximum Adverse Excursion (USD)
    mae_pips: float = 0.0  # Maximum Adverse Excursion (pips)
    mfe_usd: float = 0.0  # Maximum Favorable Excursion (USD)
    mfe_pips: float = 0.0  # Maximum Favorable Excursion (pips)
    drawdown: float = 0.0  # Account drawdown at trade exit

    # ═════════════════════════════════════════════════════════════════════
    # 1️⃣2️⃣ Regime & Research Tags
    # ═════════════════════════════════════════════════════════════════════
    market_regime: Optional[str] = None  # Trend / Range / Volatile
    volatility_bucket: Optional[str] = None  # Low / Medium / High
    correlation_cluster: Optional[str] = None

    # ═════════════════════════════════════════════════════════════════════
    # 1️⃣3️⃣ Compliance & Audit
    # ═════════════════════════════════════════════════════════════════════
    rule_violation_flag: bool = False
    manual_intervention: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame creation."""
        return {
            # 1️⃣ Trade Identification & Attribution
            "trade_id": self.trade_id,
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.type,
            "magic_number": self.magic_number,
            "strategy_name": self.strategy_name,
            "setup": self.setup,
            "sample_type": self.sample_type,
            "comment": self.comment,
            # 2️⃣ Strategy Context
            "signal_timeframe": self.signal_timeframe,
            "execution_timeframe": self.execution_timeframe,
            "session": self.session,
            "day_of_week": self.day_of_week,
            "hour_of_day": self.hour_of_day,
            # 3️⃣ Trade Timing
            "open_time": self.open_time,
            "close_time": self.close_time,
            "time_in_trade": self.time_in_trade,
            "bars_in_trade": self.bars_in_trade,
            # 4️⃣ Entry Definition
            "open_price": self.open_price,
            "requested_entry_price": self.requested_entry_price,
            "spread_at_entry": self.spread_at_entry,
            "size": self.size,
            # 5️⃣ Exit Definition
            "close_price": self.close_price,
            "requested_exit_price": self.requested_exit_price,
            "close_type": self.close_type,
            "exit_reason": self.exit_reason,
            # 6️⃣ Trade Plan & Risk
            "stop_loss_price_level": self.stop_loss_price_level,
            "profit_target_price_level": self.profit_target_price_level,
            "initial_risk_pips": self.initial_risk_pips,
            "initial_risk_usd": self.initial_risk_usd,
            # 7️⃣ Account State
            "balance_at_entry": self.balance_at_entry,
            "equity_at_entry": self.equity_at_entry,
            "margin_used": self.margin_used,
            "free_margin": self.free_margin,
            "balance_pips": self.balance_pips,
            # 8️⃣ Trade Management
            "max_position_size_reached": self.max_position_size_reached,
            "partial_close_count": self.partial_close_count,
            "trailing_stop_used": self.trailing_stop_used,
            "breakeven_triggered": self.breakeven_triggered,
            # 9️⃣ Execution Quality
            "slippage_usd": self.slippage_usd,
            "fill_price_deviation": self.fill_price_deviation,
            "execution_latency_ms": self.execution_latency_ms,
            # 🔟 Performance Results
            "profit_loss": self.profit_loss,
            "profit_loss_pips": self.profit_loss_pips,
            "commission": self.commission,
            "swap": self.swap,
            "r_multiple": self.r_multiple,
            "buy_hold": self.buy_hold,
            "buy_hold_pips": self.buy_hold_pips,
            # 1️⃣1️⃣ Excursion & Drawdown Analytics
            "mae_usd": self.mae_usd,
            "mae_pips": self.mae_pips,
            "mfe_usd": self.mfe_usd,
            "mfe_pips": self.mfe_pips,
            # 1️⃣2️⃣ Regime & Research Tags
            "market_regime": self.market_regime,
            "volatility_bucket": self.volatility_bucket,
            "correlation_cluster": self.correlation_cluster,
            # 1️⃣3️⃣ Compliance & Audit
            "rule_violation_flag": self.rule_violation_flag,
            "manual_intervention": self.manual_intervention,
        }


@dataclass
class EquityPoint:
    """Single point on equity curve."""

    timestamp: datetime
    balance: float
    equity: float
    drawdown: float  # Current drawdown from peak
    drawdown_percent: float


@dataclass
class BacktestResult:
    """
    Complete backtest results.

    Immutable record of everything that happened during backtest.
    """

    # Configuration
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_balance: float

    # Execution mode
    backtest_mode: str  # "event_driven" or "vectorized"
    data_step_mode: str  # "tick", "m1_bars", or "trading_timeframe"

    # Final state
    final_balance: float
    final_equity: float

    # Trade history
    trades: List[TradeRecord] = field(default_factory=list)

    # Equity curve
    equity_curve: List[EquityPoint] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # Helper Methods for Finance Module
    # =========================================================================

    def _get_equity_series(self) -> pd.Series:
        """Get equity as pandas Series for finance calculations."""
        if not self.equity_curve:
            return pd.Series(dtype=float)

        equity_data = [(p.timestamp, p.equity) for p in self.equity_curve]
        timestamps, equity_values = zip(*equity_data) if equity_data else ([], [])

        return pd.Series(equity_values, index=pd.DatetimeIndex(timestamps))

    def _get_returns_series(self) -> pd.Series:
        """Get returns series for finance calculations."""
        equity_series = self._get_equity_series()
        return returns.returns_series(equity_series)

    # =========================================================================
    # Performance Properties (Using Finance Module)
    # =========================================================================

    @property
    def total_return(self) -> float:
        """Total return in account currency."""
        trades_df = self.get_trades_df()
        return returns.net_profit(trades_df)

    @property
    def total_return_pct(self) -> float:
        """Total return percentage."""
        if self.initial_balance == 0:
            return 0.0
        return (self.total_return / self.initial_balance) * 100

    @property
    def max_drawdown(self) -> float:
        """Maximum drawdown in account currency."""
        equity_series = self._get_equity_series()
        return drawdowns.max_strategy_drawdown(equity_series)

    @property
    def max_drawdown_pct(self) -> float:
        """Maximum drawdown percentage."""
        if not self.equity_curve:
            return 0.0
        return max((p.drawdown_percent for p in self.equity_curve), default=0.0)

    @property
    def total_trades(self) -> int:
        """Total number of trades."""
        trades_df = self.get_trades_df()
        return metrics.total_trades(trades_df)

    @property
    def winning_trades(self) -> int:
        """Number of winning trades."""
        trades_df = self.get_trades_df()
        return metrics.winning_trades(trades_df)

    @property
    def losing_trades(self) -> int:
        """Number of losing trades."""
        trades_df = self.get_trades_df()
        return metrics.losing_trades(trades_df)

    @property
    def breakeven_trades(self) -> int:
        """Number of break-even trades."""
        trades_df = self.get_trades_df()
        return metrics.breakeven_trades(trades_df)

    @property
    def win_rate(self) -> float:
        """Win rate percentage."""
        trades_df = self.get_trades_df()
        return metrics.win_rate(trades_df)

    @property
    def gross_profit(self) -> float:
        """Gross profit (sum of all winning trades)."""
        trades_df = self.get_trades_df()
        return returns.gross_profit(trades_df)

    @property
    def gross_loss(self) -> float:
        """Gross loss (sum of all losing trades)."""
        trades_df = self.get_trades_df()
        return returns.gross_loss(trades_df)

    @property
    def profit_factor(self) -> float:
        """Profit factor (Gross Profit / |Gross Loss|)."""
        trades_df = self.get_trades_df()
        return ratios.profit_factor(trades_df)

    @property
    def avg_win(self) -> float:
        """Average winning trade."""
        trades_df = self.get_trades_df()
        return metrics.avg_win(trades_df)

    @property
    def avg_loss(self) -> float:
        """Average losing trade."""
        trades_df = self.get_trades_df()
        return metrics.avg_loss(trades_df)

    @property
    def avg_win_loss_ratio(self) -> float:
        """Ratio of average win to average loss (payoff ratio)."""
        trades_df = self.get_trades_df()
        return ratios.payoff_ratio(trades_df)

    @property
    def max_consecutive_wins(self) -> int:
        """Maximum consecutive winning trades."""
        trades_df = self.get_trades_df()
        return metrics.max_consecutive_wins(trades_df)

    @property
    def max_consecutive_losses(self) -> int:
        """Maximum consecutive losing trades."""
        trades_df = self.get_trades_df()
        return metrics.max_consecutive_losses(trades_df)

    @property
    def avg_trade_duration(self) -> float:
        """Average trade duration in hours."""
        trades_df = self.get_trades_df()
        return metrics.avg_time_in_trade(trades_df)

    @property
    def avg_trade_bars(self) -> float:
        """Average number of bars per trade."""
        if not self.trades:
            return 0.0
        return sum(t.bars_in_trade for t in self.trades) / len(self.trades)

    # =========================================================================
    # Additional Metrics (New)
    # =========================================================================

    @property
    def expectancy(self) -> float:
        """Expected value per trade."""
        trades_df = self.get_trades_df()
        return ratios.expectancy(trades_df)

    @property
    def expectancy_r(self) -> float:
        """Expectancy in R-multiples."""
        trades_df = self.get_trades_df()
        return ratios.expectancy_r(trades_df)

    @property
    def sqn(self) -> float:
        """System Quality Number (Van Tharp)."""
        trades_df = self.get_trades_df()
        return metrics.sqn(trades_df)

    @property
    def cagr(self) -> float:
        """Compound Annual Growth Rate."""
        equity_series = self._get_equity_series()
        return returns.cagr(equity_series)

    @property
    def avg_drawdown(self) -> float:
        """Average drawdown."""
        equity_series = self._get_equity_series()
        return drawdowns.avg_drawdown(equity_series)

    @property
    def max_drawdown_duration(self) -> int:
        """Maximum drawdown duration in periods."""
        equity_series = self._get_equity_series()
        return drawdowns.max_drawdown_duration(equity_series)

    @property
    def ulcer_index(self) -> float:
        """Ulcer Index - measure of downside volatility."""
        equity_series = self._get_equity_series()
        return drawdowns.ulcer_index(equity_series)

    # =========================================================================
    # Risk Metrics (Using Finance Module)
    # =========================================================================

    @property
    def sharpe_ratio(self) -> float:
        """Sharpe Ratio (Annualized)."""
        ret_series = self._get_returns_series()
        return ratios.sharpe_ratio(ret_series, risk_free_rate=0.0, annualize=True)

    @property
    def sortino_ratio(self) -> float:
        """Sortino Ratio (Annualized)."""
        ret_series = self._get_returns_series()
        return ratios.sortino_ratio(ret_series, target_return=0.0, annualize=True)

    @property
    def calmar_ratio(self) -> float:
        """Calmar Ratio - CAGR / Max Drawdown."""
        return ratios.calmar_ratio(self.cagr, self.max_drawdown)

    @property
    def omega_ratio(self) -> float:
        """Omega Ratio - probability-weighted gains vs losses."""
        ret_series = self._get_returns_series()
        return ratios.omega_ratio(ret_series, threshold=0.0)

    @property
    def value_at_risk_95(self) -> float:
        """Value at Risk at 95% confidence."""
        ret_series = self._get_returns_series()
        return risks.value_at_risk(ret_series, confidence=0.95)

    @property
    def conditional_var_95(self) -> float:
        """Conditional VaR (Expected Shortfall) at 95%."""
        ret_series = self._get_returns_series()
        return risks.conditional_var(ret_series, confidence=0.95)

    @property
    def volatility(self) -> float:
        """Get annualized return volatility."""
        ret_series = self._get_returns_series()
        return risks.annualized_volatility(ret_series)

    # =========================================================================
    # Methods
    # =========================================================================

    def get_trades_df(self) -> pd.DataFrame:
        """
        Get trades as DataFrame.

        Returns:
            DataFrame with all trade records
        """
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame([trade.to_dict() for trade in self.trades])

    def get_equity_df(self) -> pd.DataFrame:
        """
        Get equity curve as DataFrame.

        Returns:
            DataFrame with timestamp, balance, equity, drawdown
        """
        if not self.equity_curve:
            return pd.DataFrame()

        return pd.DataFrame(
            [
                {
                    "timestamp": point.timestamp,
                    "balance": point.balance,
                    "equity": point.equity,
                    "drawdown": point.drawdown,
                    "drawdown_percent": point.drawdown_percent,
                }
                for point in self.equity_curve
            ]
        )

    def summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Dict with key backtest statistics
        """
        return {
            # Configuration
            "strategy": self.strategy_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": f"{self.start_date.date()} to {self.end_date.date()}",
            "backtest_mode": self.backtest_mode,
            # Balance
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "final_equity": self.final_equity,
            # Returns
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "cagr": self.cagr,
            # Drawdown
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "avg_drawdown": self.avg_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            # Trades
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            # P&L
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            # Risk-Adjusted
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            # System Quality
            "sqn": self.sqn,
        }

    def comprehensive_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics using full finance module.

        Returns:
            Dict with extensive backtest statistics
        """
        trades_df = self.get_trades_df()
        equity_series = self._get_equity_series()
        ret_series = self._get_returns_series()

        return {
            # ═════════════════════════════════════════════════════════════
            # Configuration
            # ═════════════════════════════════════════════════════════════
            "strategy": self.strategy_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": f"{self.start_date.date()} to {self.end_date.date()}",
            "backtest_mode": self.backtest_mode,
            "data_step_mode": self.data_step_mode,
            # ═════════════════════════════════════════════════════════════
            # Balance & Returns
            # ═════════════════════════════════════════════════════════════
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "cagr": returns.cagr(equity_series),
            "gross_profit": returns.gross_profit(trades_df),
            "gross_loss": returns.gross_loss(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Trade Counts
            # ═════════════════════════════════════════════════════════════
            "total_trades": metrics.total_trades(trades_df),
            "winning_trades": metrics.winning_trades(trades_df),
            "losing_trades": metrics.losing_trades(trades_df),
            "breakeven_trades": metrics.breakeven_trades(trades_df),
            "long_trades": metrics.long_trades(trades_df),
            "short_trades": metrics.short_trades(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Win/Loss Statistics
            # ═════════════════════════════════════════════════════════════
            "win_rate": metrics.win_rate(trades_df),
            "avg_win": metrics.avg_win(trades_df),
            "avg_loss": metrics.avg_loss(trades_df),
            "largest_win": metrics.largest_win(trades_df),
            "largest_loss": metrics.largest_loss(trades_df),
            "median_win": metrics.median_win(trades_df),
            "median_loss": metrics.median_loss(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Expectancy & Edge
            # ═════════════════════════════════════════════════════════════
            "expectancy": ratios.expectancy(trades_df),
            "expectancy_r": ratios.expectancy_r(trades_df),
            "payoff_ratio": ratios.payoff_ratio(trades_df),
            "profit_factor": ratios.profit_factor(trades_df),
            "edge_ratio": ratios.edge_ratio(trades_df),
            # ═════════════════════════════════════════════════════════════
            # R-Multiple Analytics
            # ═════════════════════════════════════════════════════════════
            "avg_r_multiple": metrics.avg_r_multiple(trades_df),
            "median_r_multiple": metrics.median_r_multiple(trades_df),
            "max_r_multiple": metrics.max_r_multiple(trades_df),
            "min_r_multiple": metrics.min_r_multiple(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Trade Sequences
            # ═════════════════════════════════════════════════════════════
            "max_consecutive_wins": metrics.max_consecutive_wins(trades_df),
            "max_consecutive_losses": metrics.max_consecutive_losses(trades_df),
            "avg_consecutive_wins": metrics.avg_consecutive_wins(trades_df),
            "avg_consecutive_losses": metrics.avg_consecutive_losses(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Time Statistics
            # ═════════════════════════════════════════════════════════════
            "avg_time_in_trade": metrics.avg_time_in_trade(trades_df),
            "median_time_in_trade": metrics.median_time_in_trade(trades_df),
            "max_time_in_trade": metrics.max_time_in_trade(trades_df),
            "min_time_in_trade": metrics.min_time_in_trade(trades_df),
            # ═════════════════════════════════════════════════════════════
            # System Quality
            # ═════════════════════════════════════════════════════════════
            "sqn": metrics.sqn(trades_df),
            "trade_efficiency": metrics.trade_efficiency(trades_df),
            "expectancy_variance": metrics.expectancy_variance(trades_df),
            "trade_outcome_entropy": metrics.trade_outcome_entropy(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Drawdowns
            # ═════════════════════════════════════════════════════════════
            "max_drawdown": drawdowns.max_strategy_drawdown(equity_series),
            "max_drawdown_pct": self.max_drawdown_pct,
            "avg_drawdown": drawdowns.avg_drawdown(equity_series),
            "max_drawdown_duration": drawdowns.max_drawdown_duration(equity_series),
            "avg_drawdown_duration": drawdowns.avg_drawdown_duration(equity_series),
            "ulcer_index": drawdowns.ulcer_index(equity_series),
            "pain_index": drawdowns.pain_index(equity_series),
            # ═════════════════════════════════════════════════════════════
            # Risk-Adjusted Ratios
            # ═════════════════════════════════════════════════════════════
            "sharpe_ratio": ratios.sharpe_ratio(ret_series),
            "sortino_ratio": ratios.sortino_ratio(ret_series),
            "calmar_ratio": ratios.calmar_ratio(
                returns.cagr(equity_series),
                drawdowns.max_strategy_drawdown(equity_series),
            ),
            "omega_ratio": ratios.omega_ratio(ret_series),
            "gain_to_pain_ratio": ratios.gain_to_pain_ratio(ret_series),
            # ═════════════════════════════════════════════════════════════
            # Trade-Based Ratios
            # ═════════════════════════════════════════════════════════════
            "profit_to_mae_ratio": ratios.profit_to_mae_ratio(trades_df),
            "mfe_to_mae_ratio": ratios.mfe_to_mae_ratio(trades_df),
            "return_over_drawdown": ratios.return_over_drawdown(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Risk Metrics
            # ═════════════════════════════════════════════════════════════
            "volatility": risks.annualized_volatility(ret_series),
            "downside_volatility": risks.downside_volatility(ret_series),
            "value_at_risk_95": risks.value_at_risk(ret_series, 0.95),
            "conditional_var_95": risks.conditional_var(ret_series, 0.95),
            "exposure_time_ratio": risks.exposure_time_ratio(trades_df),
            # ═════════════════════════════════════════════════════════════
            # Efficiency Metrics
            # ═════════════════════════════════════════════════════════════
            "return_per_unit_risk": efficiency.return_per_unit_risk(trades_df),
            "time_efficiency": efficiency.time_efficiency(trades_df),
            "return_per_trade": efficiency.return_per_trade(trades_df),
            "mfe_efficiency": efficiency.mfe_efficiency(trades_df),
            "mae_efficiency": efficiency.mae_efficiency(trades_df),
            "exit_efficiency": efficiency.exit_efficiency(trades_df),
            "win_efficiency": efficiency.win_efficiency(trades_df),
            "loss_containment_efficiency": efficiency.loss_containment_efficiency(
                trades_df
            ),
        }

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"BacktestResult({self.strategy_name} on {self.symbol} {self.timeframe}, "
            f"{self.total_trades} trades, "
            f"{self.total_return_pct:.2f}% return)"
        )
