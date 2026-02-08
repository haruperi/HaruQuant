"""Portfolio Backtest Result Classes.

This module provides result classes for multi-asset portfolio backtesting,
including per-asset metrics and portfolio-level aggregation.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd

from apps.simulation.records import TradeRecord


@dataclass
class AssetBacktestResult:
    """
    Results for a single asset within a portfolio backtest.

    Contains performance metrics for one symbol's trades.
    """

    symbol: str
    total_trades: int
    total_return: float  # Absolute profit/loss
    total_return_pct: float  # Percentage return
    max_drawdown_pct: float
    win_rate: float  # Percentage of winning trades
    profit_factor: float  # Gross profit / gross loss
    sharpe_ratio: float
    trades: List[TradeRecord] = field(default_factory=list)

    def _get_returns_series(self) -> pd.Series:
        """
        Get time series of returns for correlation calculation.

        Returns:
            Series indexed by close time with cumulative returns
        """
        if not self.trades:
            return pd.Series(dtype=float)

        # Create series of trade returns indexed by close time
        returns_data = []
        for trade in self.trades:
            if trade.close_time is not None:
                returns_data.append(
                    {"time": trade.close_time, "return": trade.profit_loss}
                )

        if not returns_data:
            return pd.Series(dtype=float)

        df = pd.DataFrame(returns_data)
        df = df.groupby("time")["return"].sum()
        return df

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "total_trades": self.total_trades,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
        }


class PortfolioBacktestResult:
    """
    Results for a multi-asset portfolio backtest.

    Contains portfolio-level metrics and per-asset breakdowns.
    """

    def __init__(
        self,
        portfolio_name: str,
        symbols: List[str],
        initial_balance: float,
        final_balance: float,
        trades: List[TradeRecord],
        equity_curve: pd.Series,
        asset_results: Dict[str, AssetBacktestResult],
    ):
        """
        Initialize portfolio backtest result.

        Args:
            portfolio_name: Name of the portfolio/backtest
            symbols: List of symbols in portfolio
            initial_balance: Starting account balance
            final_balance: Ending account balance
            trades: All trades across all symbols
            equity_curve: Time series of account equity
            asset_results: Per-asset results dictionary
        """
        self.portfolio_name = portfolio_name
        self.symbols = symbols
        self.initial_balance = initial_balance
        self.final_balance = final_balance
        self.trades = trades
        self.equity_curve = equity_curve
        self.asset_results = asset_results

    def get_portfolio_summary(self) -> Dict:
        """
        Get summary statistics for the entire portfolio.

        Returns:
            Dictionary with portfolio-level metrics
        """
        total_trades = len(self.trades)
        total_return = self.final_balance - self.initial_balance
        total_return_pct = (
            (total_return / self.initial_balance * 100)
            if self.initial_balance > 0
            else 0.0
        )

        # Calculate max drawdown from equity curve
        max_drawdown_pct = self._calculate_max_drawdown()

        # Calculate win rate
        winning_trades = sum(1 for t in self.trades if t.profit_loss > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Calculate profit factor
        gross_profit = sum(t.profit_loss for t in self.trades if t.profit_loss > 0)
        gross_loss = abs(sum(t.profit_loss for t in self.trades if t.profit_loss < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()

        return {
            "portfolio_name": self.portfolio_name,
            "symbols": self.symbols,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "max_drawdown_pct": max_drawdown_pct,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
        }

    def get_asset_contributions(self) -> Dict[str, Dict]:
        """
        Get each asset's contribution to portfolio performance.

        Returns:
            Dictionary mapping symbol to contribution metrics
        """
        contributions = {}

        for symbol, asset_result in self.asset_results.items():
            # Calculate percentage of total return
            total_return = self.final_balance - self.initial_balance
            contribution_pct = (
                (asset_result.total_return / total_return * 100)
                if total_return != 0
                else 0.0
            )

            contributions[symbol] = {
                "symbol": symbol,
                "total_return": asset_result.total_return,
                "contribution_pct": contribution_pct,
                "total_trades": asset_result.total_trades,
                "win_rate": asset_result.win_rate,
                "sharpe_ratio": asset_result.sharpe_ratio,
            }

        return contributions

    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        Calculate correlation matrix of returns between assets.

        Returns:
            DataFrame with pairwise correlations
        """
        # Build dataframe of returns for each asset
        returns_dict = {}
        for symbol, asset_result in self.asset_results.items():
            returns_series = asset_result._get_returns_series()
            if not returns_series.empty:
                returns_dict[symbol] = returns_series

        if not returns_dict:
            # Return empty dataframe
            return pd.DataFrame()

        # Align all series to common timeline
        returns_df = pd.DataFrame(returns_dict)

        # Fill NaNs with 0 (no trade = no return)
        returns_df = returns_df.fillna(0)

        # Calculate correlation matrix
        if len(returns_df) < 2:
            # Not enough data for correlation
            return pd.DataFrame()

        correlation_matrix = returns_df.corr()
        return correlation_matrix

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage from equity curve."""
        if self.equity_curve.empty:
            return 0.0

        # Calculate running maximum
        running_max = self.equity_curve.expanding().max()

        # Calculate drawdown
        drawdown = (self.equity_curve - running_max) / running_max * 100

        # Get maximum drawdown (most negative value)
        max_drawdown = float(abs(drawdown.min()))

        return max_drawdown

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio from equity curve.

        Args:
            risk_free_rate: Annual risk-free rate (default 0)

        Returns:
            Sharpe ratio (annualized)
        """
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0

        # Calculate returns
        returns = self.equity_curve.pct_change().dropna()

        if returns.empty or returns.std() == 0:
            return 0.0

        # Calculate Sharpe ratio
        mean_return = returns.mean()
        std_return = returns.std()

        # Annualize (assuming daily data - adjust if needed)
        sharpe = float((mean_return - risk_free_rate / 252) / std_return * np.sqrt(252))

        return sharpe

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "portfolio_summary": self.get_portfolio_summary(),
            "asset_contributions": self.get_asset_contributions(),
            "asset_results": {
                symbol: result.to_dict()
                for symbol, result in self.asset_results.items()
            },
        }
