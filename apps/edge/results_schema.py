"""Edge Lab result schemas.

Dataclasses for storing EDS results in a standardized format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TradeSample:
    """Single trade record."""

    entry_time: Any  # datetime or pd.Timestamp
    exit_time: Any
    side: str  # "BUY" or "SELL"
    entry_price: float
    exit_price: float
    r_multiple: float
    mae_r: float  # Maximum Adverse Excursion in R
    mfe_r: float  # Maximum Favorable Excursion in R
    hold_bars: int
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entry_time": str(self.entry_time),
            "exit_time": str(self.exit_time),
            "side": self.side,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "r_multiple": self.r_multiple,
            "mae_r": self.mae_r,
            "mfe_r": self.mfe_r,
            "hold_bars": self.hold_bars,
            "meta": self.meta,
        }


@dataclass
class EdgeStats:
    """Aggregate statistics for an EDS run."""

    n_trades: int
    expectancy_r: float
    win_rate: float
    profit_factor: float
    median_mae_r: float
    median_mfe_r: float
    avg_hold_bars: float
    ci_low: float  # Bootstrap CI lower bound
    ci_high: float  # Bootstrap CI upper bound
    p_value_perm: float  # Permutation test p-value
    extras: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "n_trades": self.n_trades,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "median_mae_r": self.median_mae_r,
            "median_mfe_r": self.median_mfe_r,
            "avg_hold_bars": self.avg_hold_bars,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value_perm": self.p_value_perm,
            "extras": self.extras,
        }

    @property
    def edge_confirmed(self) -> bool:
        """Check if edge is statistically confirmed."""
        return self.ci_low > 0 and self.p_value_perm < 0.05

    @property
    def verdict(self) -> str:
        """Return human-readable verdict."""
        if self.n_trades < 30:
            return "INSUFFICIENT_DATA"
        if self.ci_low > 0 and self.p_value_perm < 0.05:
            return "EDGE_CONFIRMED"
        if self.ci_low > 0:
            return "POTENTIAL_EDGE"
        if self.expectancy_r > 0:
            return "WEAK_SIGNAL"
        return "NO_EDGE"


@dataclass
class EdgeResult:
    """Complete result from an EDS run."""

    symbol: str
    timeframe: str
    eds_name: str
    config: Dict[str, Any]
    stats: EdgeStats
    trades: List[TradeSample] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "eds_name": self.eds_name,
            "config": self.config,
            "stats": self.stats.to_dict(),
            "trades": [t.to_dict() for t in self.trades],
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeResult":
        """Create from dictionary."""
        stats_data = data["stats"]
        stats = EdgeStats(
            n_trades=stats_data["n_trades"],
            expectancy_r=stats_data["expectancy_r"],
            win_rate=stats_data["win_rate"],
            profit_factor=stats_data["profit_factor"],
            median_mae_r=stats_data["median_mae_r"],
            median_mfe_r=stats_data["median_mfe_r"],
            avg_hold_bars=stats_data["avg_hold_bars"],
            ci_low=stats_data["ci_low"],
            ci_high=stats_data["ci_high"],
            p_value_perm=stats_data["p_value_perm"],
            extras=stats_data.get("extras"),
        )

        trades = []
        for t in data.get("trades", []):
            trades.append(
                TradeSample(
                    entry_time=t["entry_time"],
                    exit_time=t["exit_time"],
                    side=t["side"],
                    entry_price=t["entry_price"],
                    exit_price=t["exit_price"],
                    r_multiple=t["r_multiple"],
                    mae_r=t["mae_r"],
                    mfe_r=t["mfe_r"],
                    hold_bars=t["hold_bars"],
                    meta=t.get("meta"),
                )
            )

        return cls(
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            eds_name=data["eds_name"],
            config=data["config"],
            stats=stats,
            trades=trades,
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )

    def summary(self) -> str:
        """Return concise summary string."""
        return (
            f"{self.eds_name} | {self.symbol} {self.timeframe} | "
            f"Trades: {self.stats.n_trades} | "
            f"Exp: {self.stats.expectancy_r:.4f}R | "
            f"CI: [{self.stats.ci_low:.4f}, {self.stats.ci_high:.4f}] | "
            f"p: {self.stats.p_value_perm:.4f} | "
            f"Verdict: {self.stats.verdict}"
        )
