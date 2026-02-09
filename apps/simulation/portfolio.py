"""Portfolio Strategy and Engine for Multi-Asset Backtesting.

This module provides portfolio-level orchestration for multi-asset backtesting,
including allocation strategies and execution coordination.
"""

import logging
from typing import Dict, Literal, Optional

import numpy as np
import pandas as pd

from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.portfolio_result import (
    AssetBacktestResult,
    PortfolioBacktestResult,
)
from apps.simulation.synchronizer import DataSynchronizer
from apps.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


class PortfolioStrategy:
    """
    Portfolio strategy with multiple symbols and allocation rules.

    Manages strategies across multiple symbols with position sizing based on
    allocation method (equal weight, risk parity, etc.).
    """

    def __init__(
        self,
        strategies: Dict[str, BaseStrategy],
        symbol_specs: Dict[str, SymbolInfoSimulator],
        data: Dict[str, pd.DataFrame],
        max_total_exposure: float = 1.0,
        max_correlated_exposure: float = 0.6,
        allocation_method: Literal["equal_weight", "risk_parity"] = "equal_weight",
    ):
        """
        Initialize portfolio strategy.

        Args:
            strategies: Dictionary mapping symbol to strategy
            symbol_specs: Dictionary mapping symbol to SymbolInfoSimulator
            data: Dictionary mapping symbol to price DataFrame
            max_total_exposure: Maximum total portfolio exposure (default 1.0 = 100%)
            max_correlated_exposure: Maximum exposure to correlated assets (default 0.6 = 60%)
            allocation_method: Method for calculating allocations ('equal_weight' or 'risk_parity')

        Raises:
            ValueError: If symbol sets don't match or data is invalid
        """
        self.strategies = strategies
        self.symbol_specs = symbol_specs
        self.data = data
        self.max_total_exposure = max_total_exposure
        self.max_correlated_exposure = max_correlated_exposure
        self.allocation_method = allocation_method

        # Validate on initialization
        self.validate()

    def validate(self) -> None:
        """
        Validate portfolio strategy configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Check that symbol sets match
        strategy_symbols = set(self.strategies.keys())
        spec_symbols = set(self.symbol_specs.keys())
        data_symbols = set(self.data.keys())

        if strategy_symbols != spec_symbols:
            raise ValueError(
                f"Strategy symbols {strategy_symbols} don't match "
                f"symbol spec symbols {spec_symbols}"
            )

        if strategy_symbols != data_symbols:
            raise ValueError(
                f"Strategy symbols {strategy_symbols} don't match "
                f"data symbols {data_symbols}"
            )

        # Validate data has datetime index
        for symbol, df in self.data.items():
            if df.empty:
                raise ValueError(f"Data for {symbol} is empty")
            if not isinstance(df.index, pd.DatetimeIndex) and not isinstance(
                df.index, pd.Index
            ):
                raise ValueError(
                    f"Data for {symbol} must have DatetimeIndex, got {type(df.index)}"
                )

        # Validate allocation method
        if self.allocation_method not in ["equal_weight", "risk_parity"]:
            raise ValueError(
                f"Invalid allocation_method: {self.allocation_method}. "
                f"Must be 'equal_weight' or 'risk_parity'"
            )

        logger.info(f"Portfolio strategy validated: {len(self.strategies)} symbols")

    def calculate_allocations(self) -> Dict[str, float]:
        """
        Calculate position size allocations for each symbol.

        Returns:
            Dictionary mapping symbol to allocation weight (0.0 to 1.0)
        """
        if self.allocation_method == "equal_weight":
            return self._calculate_equal_weight()
        elif self.allocation_method == "risk_parity":
            return self._calculate_risk_parity()
        else:
            raise ValueError(f"Unknown allocation method: {self.allocation_method}")

    def _calculate_equal_weight(self) -> Dict[str, float]:
        """
        Calculate equal weight allocation (1/N per symbol).

        Returns:
            Dictionary with equal allocations
        """
        n_symbols = len(self.strategies)
        if n_symbols == 0:
            return {}

        allocation = self.max_total_exposure / n_symbols

        allocations = {symbol: allocation for symbol in self.strategies.keys()}

        logger.info(f"Equal weight allocations: {allocations}")
        return allocations

    def _calculate_risk_parity(self) -> Dict[str, float]:
        """
        Calculate risk parity allocation (inverse volatility weighting).

        Allocates more to less volatile assets, inversely proportional to volatility.

        Returns:
            Dictionary with risk-adjusted allocations
        """
        # Calculate volatility for each symbol
        volatilities = {}
        for symbol, df in self.data.items():
            if "close" not in df.columns:
                raise ValueError(f"Data for {symbol} must have 'close' column")

            # Calculate returns
            returns = df["close"].pct_change().dropna()

            if len(returns) < 2:
                volatilities[symbol] = 1.0  # Default volatility
            else:
                volatilities[symbol] = returns.std()

        # Calculate inverse volatility weights
        inverse_vols = {
            symbol: 1.0 / vol if vol > 0 else 0.0
            for symbol, vol in volatilities.items()
        }
        total_inverse_vol = sum(inverse_vols.values())

        if total_inverse_vol == 0:
            # Fallback to equal weight
            logger.warning("All volatilities are zero, falling back to equal weight")
            return self._calculate_equal_weight()

        # Normalize to sum to max_total_exposure
        allocations = {
            symbol: (inv_vol / total_inverse_vol) * self.max_total_exposure
            for symbol, inv_vol in inverse_vols.items()
        }

        logger.info(f"Risk parity allocations: {allocations}")
        logger.info(f"Volatilities: {volatilities}")

        return allocations


class PortfolioEngine:
    """
    Engine for running multi-asset portfolio backtests.

    Orchestrates data synchronization, allocation calculation, and simulation
    across multiple symbols with a single account.
    """

    def __init__(
        self,
        portfolio_strategy: PortfolioStrategy,
        initial_balance: float,
        config: Optional[Dict] = None,
    ):
        """
        Initialize portfolio engine.

        Args:
            portfolio_strategy: Portfolio strategy configuration
            initial_balance: Starting account balance
            config: Optional configuration dict (commission, slippage, etc.)
        """
        self.portfolio_strategy = portfolio_strategy
        self.initial_balance = initial_balance
        self.config = config or {}

        logger.info(f"PortfolioEngine initialized with balance={initial_balance}")

    def run(
        self,
        synchronize_data: bool = True,
        sync_method: Literal["ffill", "drop", "interpolate"] = "ffill",
    ) -> PortfolioBacktestResult:
        """
        Run portfolio backtest.

        Args:
            synchronize_data: Whether to synchronize data timelines (default True)
            sync_method: Method for synchronizing data ('ffill', 'drop', 'interpolate')

        Returns:
            PortfolioBacktestResult with complete metrics

        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("=" * 80)
        logger.info("Starting Portfolio Backtest")
        logger.info("=" * 80)

        # Step 1: Validate portfolio
        logger.info("Step 1: Validating portfolio strategy...")
        self.portfolio_strategy.validate()

        # Step 2: Calculate allocations
        logger.info("Step 2: Calculating position allocations...")
        allocations = self.portfolio_strategy.calculate_allocations()

        # Step 3: Synchronize data
        if synchronize_data:
            logger.info(f"Step 3: Synchronizing data (method={sync_method})...")
            synchronized_data = DataSynchronizer.synchronize(
                self.portfolio_strategy.data,
                method=sync_method,
                handle_leading_nans="fill",  # Fill instead of drop to keep all bars
                handle_trailing_nans="fill",  # Fill instead of drop to keep all bars
            )
        else:
            logger.info("Step 3: Skipping data synchronization...")
            synchronized_data = self.portfolio_strategy.data

        # Step 4: Create symbol infos (already have SymbolInfoSimulator)
        logger.info(
            "Step 4: Symbol specs ready (using provided SymbolInfoSimulator)..."
        )

        # Step 5: Create account
        leverage = int(self.config.get("leverage", 100))
        logger.info(
            f"Step 5: Creating account with initial balance=${self.initial_balance:,.2f}, leverage={leverage}..."
        )
        account_info = AccountInfoSimulator(
            balance=self.initial_balance,
            equity=self.initial_balance,
            leverage=leverage,
        )

        # Step 6: Create TradeSimulator (which inherits from SimulationEngine)
        logger.info("Step 6: Creating TradeSimulator...")

        from apps.simulation.simulator import TradeSimulator

        # Create simulator with all symbols
        # Note: TradeSimulator inherits from SimulationEngine, so it IS the engine
        engine = TradeSimulator(
            simulator_name=self.config.get("simulator_name", "PortfolioSimulator"),
            mt5_client=None,  # Backtest mode
            account_info=account_info,
            symbols=self.portfolio_strategy.symbol_specs,
        )

        # Step 7: Run portfolio backtest
        logger.info("Step 7: Running portfolio backtest...")

        symbols = list(self.portfolio_strategy.strategies.keys())

        # Get trading period dates (excluding warmup)
        start_date = self.config.get("start_date")
        end_date = self.config.get("end_date")

        if start_date:
            logger.info(f"Trading period: {start_date} to {end_date or 'latest'}")
            logger.info(
                "(Warmup period data loaded but trades will only be counted from start_date)"
            )

        # Get backtest parameters
        commission = float(self.config.get("commission", 0.0))
        slippage = float(self.config.get("slippage", 0.0))
        volume = float(self.config.get("volume", 0.1))

        logger.info(
            f"Backtest parameters: volume={volume}, commission=${commission}/contract, slippage={slippage} points"
        )

        engine.run(
            data=synchronized_data,
            strategy=self.portfolio_strategy.strategies,
            symbol=symbols,
            volume=volume,
            verbose=self.config.get("verbose", False),  # Default to non-verbose
            commission_per_contract=commission,
            slippage_points=slippage,
            allocations=allocations,
            engine_type="event_driven",
            start_date=start_date,
            end_date=end_date,
        )

        # Step 8: Extract results from simulator
        logger.info("Step 8: Extracting results...")

        all_trades = engine._completed_trades
        final_balance = engine._account_data.balance

        # Build equity curve from simulation
        # For now, use a simple series from initial to final balance
        if synchronized_data:
            first_symbol = symbols[0]
            timeline = synchronized_data[first_symbol].index
            # TODO: Extract actual equity curve from engine if available
            equity_curve = pd.Series(
                np.linspace(self.initial_balance, final_balance, len(timeline)),
                index=timeline,
            )
        else:
            equity_curve = pd.Series(dtype=float)

        # Calculate per-asset results
        asset_results: Dict[str, AssetBacktestResult] = {}

        for symbol in symbols:
            # Filter trades for this symbol
            symbol_trades = [t for t in all_trades if t.symbol == symbol]

            if symbol_trades:
                total_return = sum(t.profit_loss for t in symbol_trades)
                gross_profit = sum(
                    t.profit_loss for t in symbol_trades if t.profit_loss > 0
                )
                gross_loss = abs(
                    sum(t.profit_loss for t in symbol_trades if t.profit_loss < 0)
                )
                winning_trades = sum(1 for t in symbol_trades if t.profit_loss > 0)

                win_rate = (
                    (winning_trades / len(symbol_trades) * 100)
                    if symbol_trades
                    else 0.0
                )
                profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

                asset_results[symbol] = AssetBacktestResult(
                    symbol=symbol,
                    total_trades=len(symbol_trades),
                    total_return=total_return,
                    total_return_pct=(
                        (total_return / self.initial_balance * 100)
                        if self.initial_balance > 0
                        else 0.0
                    ),
                    max_drawdown_pct=0.0,  # TODO: Calculate from equity curve
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    sharpe_ratio=0.0,  # TODO: Calculate from returns
                    trades=symbol_trades,
                )
            else:
                asset_results[symbol] = AssetBacktestResult(
                    symbol=symbol,
                    total_trades=0,
                    total_return=0.0,
                    total_return_pct=0.0,
                    max_drawdown_pct=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    sharpe_ratio=0.0,
                    trades=[],
                )

        # Step 9: Package into PortfolioBacktestResult
        logger.info("Step 9: Packaging results...")
        result = PortfolioBacktestResult(
            portfolio_name=self.config.get("portfolio_name", "Portfolio"),
            symbols=symbols,
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            trades=all_trades,
            equity_curve=equity_curve,
            asset_results=asset_results,
        )

        logger.info("=" * 80)
        logger.info("Portfolio Backtest Complete")
        logger.info(f"Symbols: {len(symbols)}")
        logger.info(f"Total Trades: {len(all_trades)}")
        logger.info(f"Initial Balance: ${self.initial_balance:,.2f}")
        logger.info(f"Final Balance: ${final_balance:,.2f}")
        logger.info(f"Total Return: ${final_balance - self.initial_balance:,.2f}")
        logger.info("=" * 80)

        return result
