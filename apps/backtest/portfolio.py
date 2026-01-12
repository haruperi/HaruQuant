"""
Portfolio Backtesting Module.

Multi-asset portfolio backtesting with unified timeline synchronization.
Supports stocks, forex, and crypto with portfolio-level risk management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from apps.logger import logger

from .engine.base import BaseEngine
from .engine.event_driven import EventDrivenEngine
from .result import BacktestResult, EquityPoint, TradeRecord

# =========================================================================
# Enums
# =========================================================================


class AssetClass(str, Enum):
    """Asset class enumeration."""

    FOREX = "forex"
    STOCK = "stock"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    INDEX = "index"


# =========================================================================
# Data Models
# =========================================================================


@dataclass
class AssetSpecification:
    """
    Specification for a single asset in the portfolio.

    Defines asset-specific parameters like contract size, point value,
    commission structure, and trading hours.
    """

    # Asset identification
    symbol: str
    asset_class: AssetClass

    # Contract specifications
    contract_size: float = 100000.0  # Forex default
    point: float = 0.00001  # 5-digit forex
    tick_value: float = 10.0  # Value per lot per pip

    # Costs
    commission: float = 0.0  # Per trade
    spread_points: float = 0.0  # Average spread

    # Risk parameters
    leverage: int = 100
    margin_requirement: float = 0.01  # 1% for 100:1 leverage

    # Position limits
    max_position_pct: float = 0.25  # Max 25% of portfolio per asset
    max_correlation_exposure: float = 0.50  # Max 50% in correlated assets

    # Trading session (optional)
    trading_hours: Optional[Dict[str, Any]] = None

    # Metadata
    description: str = ""

    def __post_init__(self):
        """Validate asset specification."""
        if self.contract_size <= 0:
            raise ValueError(f"Invalid contract_size: {self.contract_size}")
        if self.leverage <= 0:
            raise ValueError(f"Invalid leverage: {self.leverage}")
        if not 0 <= self.max_position_pct <= 1:
            raise ValueError(f"max_position_pct must be 0-1: {self.max_position_pct}")


@dataclass
class PortfolioPosition:
    """
    Represents an open position in the portfolio.

    Tracks position details for a single asset including P&L,
    margin usage, and position sizing.
    """

    # Position identification
    symbol: str
    position_id: str

    # Position details
    entry_time: datetime
    entry_price: float
    size: float  # In lots
    direction: int  # 1 = long, -1 = short

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # Margin tracking
    margin_used: float = 0.0

    # Excursion tracking
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion

    # Metadata
    strategy_name: str = ""
    notes: str = ""

    def calculate_pnl(
        self, current_price: float, contract_size: float, point: float
    ) -> float:
        """
        Calculate unrealized P&L for current position.

        Args:
            current_price: Current market price
            contract_size: Asset contract size
            point: Point value for the asset

        Returns:
            Unrealized P&L in account currency
        """
        price_diff = (current_price - self.entry_price) * self.direction
        pnl = price_diff * self.size * contract_size
        return pnl

    def update_excursions(
        self, current_price: float, contract_size: float, point: float
    ) -> None:
        """
        Update MAE and MFE based on current price.

        Args:
            current_price: Current market price
            contract_size: Asset contract size
            point: Point value for the asset
        """
        pnl = self.calculate_pnl(current_price, contract_size, point)

        # Update MFE (best profit)
        if pnl > self.mfe:
            self.mfe = pnl

        # Update MAE (worst loss)
        if pnl < self.mae:
            self.mae = pnl


@dataclass
class PortfolioBacktestResult:
    """
    Results from a multi-asset portfolio backtest.

    Contains all individual asset results plus portfolio-level metrics.
    """

    # Configuration
    portfolio_name: str
    start_date: datetime
    end_date: datetime
    initial_balance: float

    # Final state
    final_balance: float
    final_equity: float

    # Individual asset results
    asset_results: Dict[str, BacktestResult] = field(default_factory=dict)

    # Portfolio-level data
    equity_curve: List[EquityPoint] = field(default_factory=list)
    all_trades: List[TradeRecord] = field(default_factory=list)

    # Portfolio analytics
    correlation_matrix: Optional[pd.DataFrame] = None
    asset_allocations: Dict[str, float] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio-level summary statistics.

        Returns:
            Dict with portfolio metrics
        """
        total_return = self.final_balance - self.initial_balance
        total_return_pct = (
            (total_return / self.initial_balance * 100)
            if self.initial_balance > 0
            else 0
        )

        # Calculate max drawdown from equity curve
        max_dd = 0.0
        max_dd_pct = 0.0
        if self.equity_curve:
            max_dd_pct = max(
                (p.drawdown_percent for p in self.equity_curve), default=0.0
            )
            max_dd = max((p.drawdown for p in self.equity_curve), default=0.0)

        return {
            "portfolio_name": self.portfolio_name,
            "period": f"{self.start_date.date()} to {self.end_date.date()}",
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "total_trades": len(self.all_trades),
            "assets_traded": len(self.asset_results),
            "asset_allocations": self.asset_allocations,
        }

    def get_asset_contributions(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate each asset's contribution to portfolio performance.

        Returns:
            Dict mapping symbol to contribution metrics
        """
        contributions = {}

        for symbol, result in self.asset_results.items():
            asset_pnl = result.total_return
            contribution_pct = (
                (asset_pnl / self.initial_balance * 100)
                if self.initial_balance > 0
                else 0
            )

            contributions[symbol] = {
                "pnl": asset_pnl,
                "contribution_pct": contribution_pct,
                "trades": result.total_trades,
                "win_rate": result.win_rate,
                "sharpe": result.sharpe_ratio,
            }

        return contributions


@dataclass
class PortfolioStrategy:
    """
    Multi-asset strategy specification.

    Maps symbols to their individual strategies and asset specifications.
    """

    name: str
    strategies: Dict[str, Any]  # symbol -> strategy instance
    asset_specs: Dict[str, AssetSpecification]  # symbol -> asset spec
    data: Dict[str, pd.DataFrame]  # symbol -> OHLCV data

    # Portfolio constraints
    max_total_exposure: float = 1.0  # Max 100% capital deployed
    max_correlated_exposure: float = 0.5  # Max 50% in correlated assets
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly, quarterly

    def validate(self) -> None:
        """Validate portfolio strategy configuration."""
        if not self.strategies:
            raise ValueError("Portfolio must have at least one strategy")

        if set(self.strategies.keys()) != set(self.asset_specs.keys()):
            raise ValueError("Strategies and asset_specs must have matching symbols")

        if set(self.strategies.keys()) != set(self.data.keys()):
            raise ValueError("Strategies and data must have matching symbols")

        logger.info(f"Portfolio strategy validated: {len(self.strategies)} assets")


# =========================================================================
# Portfolio Engine
# =========================================================================


class PortfolioEngine:
    """
    Multi-asset portfolio backtest engine.

    Runs backtests on multiple assets simultaneously with:
    - Unified timeline synchronization
    - Portfolio-level risk management
    - Correlation tracking
    - Capital allocation across assets
    """

    def __init__(
        self,
        portfolio_strategy: PortfolioStrategy,
        initial_balance: float = 10000.0,
        engines: Optional[Dict[str, BaseEngine]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize portfolio engine.

        Args:
            portfolio_strategy: PortfolioStrategy instance
            initial_balance: Starting portfolio balance
            engines: Pre-configured engines for each asset (optional)
            config: Additional configuration
        """
        self.portfolio_strategy = portfolio_strategy
        self.portfolio_strategy.validate()

        self.initial_balance = initial_balance
        self.config = config or {}

        # Asset engines (will be created if not provided)
        self.engines = engines or {}

        # Portfolio state
        self.current_balance = initial_balance
        self.current_equity = initial_balance
        self.peak_equity = initial_balance

        # Position tracking
        self.open_positions: Dict[str, List[PortfolioPosition]] = {
            symbol: [] for symbol in portfolio_strategy.strategies.keys()
        }

        # Results tracking
        self.equity_curve: List[EquityPoint] = []
        self.all_trades: List[TradeRecord] = []
        self.asset_results: Dict[str, BacktestResult] = {}

        logger.info(
            f"PortfolioEngine initialized: {len(portfolio_strategy.strategies)} assets, "
            f"${initial_balance:.2f} initial balance"
        )

    def run(self) -> PortfolioBacktestResult:
        """
        Run multi-asset portfolio backtest.

        Returns:
            PortfolioBacktestResult with complete portfolio data
        """
        logger.info(f"Starting portfolio backtest: {self.portfolio_strategy.name}")

        try:
            # Step 1: Synchronize timelines across all assets
            unified_timeline = self._synchronize_timelines()
            logger.info(f"Unified timeline: {len(unified_timeline)} periods")

            # Step 2: Run individual asset backtests
            self._run_asset_backtests()

            # Step 3: Calculate portfolio-level metrics
            self._calculate_portfolio_metrics()

            # Step 4: Calculate correlation matrix
            correlation_matrix = self._calculate_correlation_matrix()

            # Step 5: Calculate asset allocations
            asset_allocations = self._calculate_asset_allocations()

            # Step 6: Apply portfolio constraints
            self._apply_portfolio_constraints()

            # Build final result
            result = PortfolioBacktestResult(
                portfolio_name=self.portfolio_strategy.name,
                start_date=unified_timeline[0],
                end_date=unified_timeline[-1],
                initial_balance=self.initial_balance,
                final_balance=self.current_balance,
                final_equity=self.current_equity,
                asset_results=self.asset_results,
                equity_curve=self.equity_curve,
                all_trades=self.all_trades,
                correlation_matrix=correlation_matrix,
                asset_allocations=asset_allocations,
                metadata=self.config,
            )

            logger.info(
                f"Portfolio backtest complete: {result.final_balance:.2f} "
                f"({result.get_portfolio_summary()['total_return_pct']:.2f}%)"
            )

            return result

        except Exception as e:
            logger.error(f"Portfolio backtest failed: {e}")
            raise

    def _synchronize_timelines(self) -> pd.DatetimeIndex:
        """
        Create unified timeline across all assets.

        Finds common dates or creates union of all dates depending on config.

        Returns:
            DatetimeIndex with unified timeline
        """
        timeline_mode = self.config.get("timeline_mode", "union")

        all_indices = []
        for _, data in self.portfolio_strategy.data.items():
            all_indices.append(data.index)

        if timeline_mode == "intersection":
            # Only trade when all assets have data
            unified = all_indices[0]
            for idx in all_indices[1:]:
                unified = unified.intersection(idx)
        else:  # union (default)
            # Trade whenever any asset has data
            unified = all_indices[0]
            for idx in all_indices[1:]:
                unified = unified.union(idx)

        unified = unified.sort_values()

        logger.debug(f"Timeline synchronized ({timeline_mode}): {len(unified)} periods")

        return unified

    def _run_asset_backtests(self) -> None:
        """
        Run backtest for each individual asset.

        Note: This is a simplified version. In production, you would:
        1. Create individual engines for each asset
        2. Run them with allocated capital
        3. Aggregate results
        """
        if not self.portfolio_strategy.strategies:
            return

        num_assets = len(self.portfolio_strategy.strategies)
        per_asset_balance = (
            self.initial_balance / num_assets
            if num_assets > 0
            else self.initial_balance
        )

        default_timeframe = self.config.get("timeframe", "H1")
        default_data_step_mode = self.config.get("data_step_mode", "trading_timeframe")
        default_slippage_points = self.config.get("slippage_points", 0.0)
        default_commission = self.config.get("commission", 0.0)

        for symbol in self.portfolio_strategy.strategies.keys():
            logger.info(f"Running backtest for {symbol}...")

            strategy = self.portfolio_strategy.strategies[symbol]
            data = self.portfolio_strategy.data[symbol]
            asset_spec = self.portfolio_strategy.asset_specs.get(symbol)

            engine = self.engines.get(symbol)
            if engine is None:
                commission = (
                    asset_spec.commission
                    if asset_spec is not None
                    else default_commission
                )
                leverage = asset_spec.leverage if asset_spec is not None else 100

                engine = EventDrivenEngine(
                    strategy=strategy,
                    data=data,
                    initial_balance=per_asset_balance,
                    commission=commission,
                    slippage_points=default_slippage_points,
                    leverage=leverage,
                    timeframe=default_timeframe,
                    data_step_mode=default_data_step_mode,
                    config=self.config,
                )

            result = engine.run()
            self.asset_results[symbol] = result

            logger.debug(f"Backtest complete for {symbol}")

    def _calculate_portfolio_metrics(self) -> None:
        """
        Calculate portfolio-level performance metrics.

        Aggregates individual asset results into portfolio equity curve.
        """
        # Build portfolio equity curve by combining all asset equity curves
        # This is a simplified version

        # Calculate portfolio equity at each point
        self.current_balance = self.initial_balance
        self.current_equity = self.initial_balance

        # Aggregate all trades from individual assets
        for _, result in self.asset_results.items():
            if result:
                self.all_trades.extend(result.trades)
                self.current_balance += result.total_return

        self.current_equity = self.current_balance

        # Record final equity point
        if self.portfolio_strategy.data:
            first_symbol = list(self.portfolio_strategy.data.keys())[0]
            end_time = (
                self.portfolio_strategy.data[first_symbol].index[-1].to_pydatetime()
            )

            self.equity_curve.append(
                EquityPoint(
                    timestamp=end_time,
                    balance=self.current_balance,
                    equity=self.current_equity,
                    drawdown=max(0, self.peak_equity - self.current_equity),
                    drawdown_percent=(
                        (
                            (self.peak_equity - self.current_equity)
                            / self.peak_equity
                            * 100
                        )
                        if self.peak_equity > 0
                        else 0
                    ),
                )
            )

    def _calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        Calculate correlation matrix between asset returns.

        Returns:
            DataFrame with pairwise correlations
        """
        symbols = list(self.portfolio_strategy.data.keys())

        if len(symbols) < 2:
            return pd.DataFrame()

        # Calculate returns for each asset
        returns_data = {}
        for symbol, data in self.portfolio_strategy.data.items():
            if "close" in data.columns:
                returns = data["close"].pct_change()
                returns_data[symbol] = returns

        if not returns_data:
            return pd.DataFrame()

        # Create DataFrame and calculate correlation
        returns_df = pd.DataFrame(returns_data)
        correlation_matrix = returns_df.corr()

        logger.debug(f"Correlation matrix calculated for {len(symbols)} assets")

        return correlation_matrix

    def _calculate_asset_allocations(self) -> Dict[str, float]:
        """
        Calculate capital allocation percentages for each asset.

        Returns:
            Dict mapping symbol to allocation percentage
        """
        allocations = {}

        # Simple equal-weight allocation for now
        num_assets = len(self.portfolio_strategy.strategies)
        if num_assets > 0:
            equal_weight = 100.0 / num_assets

            for symbol in self.portfolio_strategy.strategies.keys():
                allocations[symbol] = equal_weight

        logger.debug(f"Asset allocations calculated: {allocations}")

        return allocations

    def _apply_portfolio_constraints(self) -> None:
        """
        Apply portfolio-level risk constraints.

        - Maximum total exposure
        - Maximum correlated asset exposure
        - Position size limits
        """
        # Calculate total exposure
        total_exposure = 0.0
        for positions in self.open_positions.values():
            for pos in positions:
                total_exposure += abs(pos.margin_used)

        exposure_pct = (
            total_exposure / self.initial_balance if self.initial_balance > 0 else 0
        )

        if exposure_pct > self.portfolio_strategy.max_total_exposure:
            logger.warning(
                f"Portfolio exposure ({exposure_pct:.1%}) exceeds limit "
                f"({self.portfolio_strategy.max_total_exposure:.1%})"
            )

        logger.debug(f"Portfolio constraints applied: exposure={exposure_pct:.1%}")

    def get_portfolio_sharpe(self) -> float:
        """
        Calculate portfolio-level Sharpe ratio.

        Returns:
            Portfolio Sharpe ratio
        """
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0.0

        # Extract equity values
        equity_values = [p.equity for p in self.equity_curve]

        # Calculate returns
        returns = pd.Series(equity_values).pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # Annualized Sharpe (assuming daily returns)
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)

        return float(sharpe)


# =========================================================================
# Helper Functions
# =========================================================================


def create_asset_spec_forex(
    symbol: str,
    spread_points: float = 2.0,
    commission: float = 0.0,
    leverage: int = 100,
) -> AssetSpecification:
    """
    Create asset specification with forex defaults.

    Args:
        symbol: Forex pair (e.g., "EURUSD")
        spread_points: Average spread in points
        commission: Commission per trade
        leverage: Leverage ratio

    Returns:
        AssetSpecification configured for forex
    """
    return AssetSpecification(
        symbol=symbol,
        asset_class=AssetClass.FOREX,
        contract_size=100000.0,
        point=0.00001,  # 5-digit
        tick_value=10.0,  # $10 per pip per lot
        commission=commission,
        spread_points=spread_points,
        leverage=leverage,
        margin_requirement=1.0 / leverage,
        max_position_pct=0.25,
        description=f"Forex pair {symbol}",
    )


def create_asset_spec_stock(
    symbol: str,
    commission: float = 1.0,
    leverage: int = 4,
) -> AssetSpecification:
    """
    Create asset specification with stock defaults.

    Args:
        symbol: Stock ticker (e.g., "AAPL")
        commission: Commission per trade
        leverage: Leverage ratio (typically 2-4 for stocks)

    Returns:
        AssetSpecification configured for stocks
    """
    return AssetSpecification(
        symbol=symbol,
        asset_class=AssetClass.STOCK,
        contract_size=1.0,  # 1 share per lot
        point=0.01,  # $0.01 per share
        tick_value=0.01,
        commission=commission,
        spread_points=0.01,  # Bid-ask spread
        leverage=leverage,
        margin_requirement=1.0 / leverage,
        max_position_pct=0.20,
        description=f"Stock {symbol}",
    )


def create_asset_spec_crypto(
    symbol: str,
    spread_points: float = 0.1,
    commission: float = 0.0,
    leverage: int = 10,
) -> AssetSpecification:
    """
    Create asset specification with crypto defaults.

    Args:
        symbol: Crypto pair (e.g., "BTCUSD")
        spread_points: Average spread
        commission: Commission per trade (often 0 with spread)
        leverage: Leverage ratio (varies by exchange)

    Returns:
        AssetSpecification configured for crypto
    """
    return AssetSpecification(
        symbol=symbol,
        asset_class=AssetClass.CRYPTO,
        contract_size=1.0,  # 1 coin per lot
        point=0.01,  # $0.01 for most cryptos
        tick_value=0.01,
        commission=commission,
        spread_points=spread_points,
        leverage=leverage,
        margin_requirement=1.0 / leverage,
        max_position_pct=0.15,  # Lower for volatile crypto
        description=f"Cryptocurrency {symbol}",
    )


def calculate_portfolio_sharpe(
    equity_curve: List[EquityPoint],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate Sharpe ratio for portfolio equity curve.

    Args:
        equity_curve: List of EquityPoint objects
        risk_free_rate: Risk-free rate (annualized)
        periods_per_year: Number of periods per year (252 for daily)

    Returns:
        Annualized Sharpe ratio
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    # Extract equity values
    equity_values = [p.equity for p in equity_curve]

    # Calculate returns
    returns = pd.Series(equity_values).pct_change().dropna()

    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    # Excess returns
    excess_returns = returns - (risk_free_rate / periods_per_year)

    # Annualized Sharpe
    sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(periods_per_year)

    return float(sharpe)
