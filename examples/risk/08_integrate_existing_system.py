"""
Example 3: Integrating Risk Management into Existing Trading System

This example shows how to add the risk module to an EXISTING live trading
system with minimal changes. It demonstrates a "wrapper" pattern where
you intercept signals before execution.

Key Integration Points:
1. Initialize risk components once at startup
2. Wrap your signal execution with risk checks
3. Track equity for regime detection
4. Periodic rebalancing
"""

import os
import sys
from typing import Dict, List, Optional

import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import (
    PositionSizer,
    RiskBudgetAllocator,
    RiskGovernor,
    RiskLimits,
    RiskRegimeDetector,
)
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.mt5 import AccountInfo

mt5 = get_mt5_api()


def _get_mt5_credentials() -> Optional[dict]:
    creds = UserManager().get_mt5_credentials()
    if not creds:
        print("No default broker credentials found.")
        return None
    return creds


def _connect_mt5() -> Optional[MT5Client]:
    creds = _get_mt5_credentials()
    if not creds:
        return None

    mt5_client = MT5Client()
    if not mt5_client.connect(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        print("Failed to initialize MT5")
        return None

    if not hasattr(mt5_client, "get_symbol_info"):
        mt5_client.get_symbol_info = mt5.symbol_info  # type: ignore[attr-defined]
    if not hasattr(mt5_client, "get_account_equity"):
        mt5_client.get_account_equity = lambda: AccountInfo().Equity()  # type: ignore[attr-defined]
    if not hasattr(mt5_client, "get_positions"):
        mt5_client.get_positions = mt5.positions_get  # type: ignore[attr-defined]

    return mt5_client


class RiskManagedTradingWrapper:
    """
    Wrapper that adds risk management to existing trading system.

    Usage:
        # In your existing system initialization:
        risk_wrapper = RiskManagedTradingWrapper(mt5_client)

        # Before executing any trade:
        if risk_wrapper.approve_trade(signal):
            execute_trade(signal)
        else:
            log_rejection(signal)
    """

    def __init__(self, mt5_client, config: Optional[Dict] = None):
        """Initialize risk management wrapper."""
        self.mt5_client = mt5_client
        self.config = config or {}

        # Initialize risk components
        self._setup_risk_components()

        # Tracking
        self.equity_history = []
        self.current_regime = None
        self.last_rebalance = None

        print("[RiskWrapper] Risk management initialized")

    def _setup_risk_components(self):
        """Setup all risk management components."""

        # Extract config or use defaults
        risk_config = self.config.get("risk_management", {})
        sizing_config = self.config.get("position_sizing", {})

        # Risk Limits
        limits_config = risk_config.get("limits", {})
        self.limits = RiskLimits(
            var_cap_frac=limits_config.get("var_cap_frac", 0.10),
            es_cap_frac=limits_config.get("es_cap_frac", 0.15),
            delta_var_cap_frac=limits_config.get("delta_var_cap_frac", 0.02),
            max_single_rc_frac=limits_config.get("max_single_rc_frac", 0.35),
        )

        # Position Sizer
        sizing_method = sizing_config.get("method", "fixed_risk")
        self.position_sizer = PositionSizer(
            method=sizing_method,
            config=sizing_config.get("config", {"risk_percent": 1.0}),
            mt5_client=self.mt5_client,
        )

        # Risk Governor
        gov_config = risk_config.get("governor_config", {})
        self.governor = RiskGovernor(
            mt5_client=self.mt5_client,
            limits=self.limits,
            timeframe=gov_config.get("timeframe", "H1"),
            start_pos=gov_config.get("start_pos", 0),
            end_pos=gov_config.get("end_pos", 500),
        )

        # Regime Detector
        regime_config = risk_config.get("regime_detector", {})
        self.regime_detector = RiskRegimeDetector(
            vol_spike_mult=regime_config.get("vol_spike_mult", 1.8),
            corr_spike_level=regime_config.get("corr_spike_level", 0.55),
            dd_trigger_frac=regime_config.get("dd_trigger_frac", 0.05),
        )

        # Risk Allocator (optional, for multi-strategy)
        if risk_config.get("enable_allocation", False):
            self.allocator = RiskBudgetAllocator(self.governor)
        else:
            self.allocator = None

        # Symbol clusters
        self.symbol_clusters = self.config.get("symbol_clusters", {})

        # Risk budgets
        self.risk_budgets = self.config.get("risk_budgets", {})

    def approve_trade(
        self, signal: Dict, current_positions: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Main method: Check if trade should be executed.

        Args:
            signal: Dict with 'symbol', 'type', 'entry_price', 'stop_loss', etc.
            current_positions: Optional dict of {symbol: lots}. If None, fetched from MT5.

        Returns:
            True if trade approved, False if rejected
        """

        symbol = signal["symbol"]

        # ====================================================================
        # STEP 1: Position Sizing
        # ====================================================================

        # If volume not already in signal, calculate it
        if "volume" not in signal:
            account_balance = self.mt5_client.get_account_equity()
            symbol_info = self.mt5_client.get_symbol_info(symbol)

            volume = self.position_sizer.calculate_size(
                account_balance=account_balance,
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                symbol_info=symbol_info,
                symbol=symbol,
                signal_type=signal.get("type"),
            )

            signal["volume"] = volume

        # ====================================================================
        # STEP 2: Get Current Positions
        # ====================================================================

        if current_positions is None:
            current_positions = self._get_current_positions()

        # ====================================================================
        # STEP 3: Update Regime (periodically)
        # ====================================================================

        # Update regime every iteration or when needed
        self._update_regime()

        # ====================================================================
        # STEP 4: Risk Governor Check
        # ====================================================================

        report = self.governor.evaluate_add_position(
            current_positions=current_positions,
            candidate_symbol=symbol,
            candidate_lots=signal["volume"],
            symbol_to_cluster=self.symbol_clusters,
            regime=self.current_regime,
        )

        # Log decision
        if report.decision == "ACCEPT":
            print(f"[RiskWrapper] APPROVED: {symbol} {signal['volume']:.3f} lots")
            print(f"  New VaR: ${report.new_var:,.2f}, Delta: ${report.delta_var:,.2f}")
            return True
        else:
            print(f"[RiskWrapper] REJECTED: {symbol} {signal['volume']:.3f} lots")
            print(f"  Reason: {report.reason}")
            return False

    def calculate_position_sizes(
        self, signals: List[Dict], use_allocation: bool = True
    ) -> Dict[str, float]:
        """
        Calculate position sizes for multiple signals, optionally using risk allocation.

        Args:
            signals: List of signal dicts
            use_allocation: Whether to use risk budget allocation

        Returns:
            Dict of {symbol: volume}
        """

        # ====================================================================
        # STEP 1: Calculate Base Sizes
        # ====================================================================

        account_balance = self.mt5_client.get_account_equity()
        base_lots = {}

        for signal in signals:
            symbol = signal["symbol"]
            symbol_info = self.mt5_client.get_symbol_info(symbol)

            volume = self.position_sizer.calculate_size(
                account_balance=account_balance,
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                symbol_info=symbol_info,
                symbol=symbol,
                signal_type=signal.get("type"),
            )

            base_lots[symbol] = volume

        # ====================================================================
        # STEP 2: Risk Allocation (if enabled and multi-strategy)
        # ====================================================================

        if not use_allocation or self.allocator is None or len(signals) == 1:
            return base_lots

        symbols = list(base_lots.keys())
        budgets = {s: self.risk_budgets.get(s, 1.0 / len(symbols)) for s in symbols}

        target_lots = self.allocator.compute_target_lots(
            symbols=symbols, base_lots=base_lots, budgets=budgets, regime=self.current_regime
        )

        print("[RiskWrapper] Risk allocation applied:")
        for symbol in symbols:
            print(f"  {symbol}: {base_lots[symbol]:.3f} -> {target_lots[symbol]:.3f} lots")

        return target_lots

    def _get_current_positions(self) -> Dict[str, float]:
        """Get current positions from MT5."""
        positions = {}

        # Get all open positions
        all_positions = self.mt5_client.get_positions()

        if all_positions:
            # Group by symbol
            for pos in all_positions:
                symbol = pos.symbol
                positions[symbol] = positions.get(symbol, 0) + pos.volume

        return positions

    def _update_regime(self):
        """Update current market regime."""

        try:
            # Build returns dataframe
            symbols = list(self.symbol_clusters.keys()) if self.symbol_clusters else ["EURUSD"]

            returns_data = {}
            for symbol in symbols:
                daily_data = self.mt5_client.get_bars(
                    symbol=symbol, timeframe="D1", count=100, start_pos=0
                )

                if daily_data is not None and not daily_data.empty and len(daily_data) >= 60:
                    returns_data[symbol] = daily_data["close"].pct_change()

            if len(returns_data) < 1:
                # Not enough data, assume NORMAL
                return

            returns_df = pd.DataFrame(returns_data)

            # Build equity curve
            current_equity = self.mt5_client.get_account_equity()
            self.equity_history.append(current_equity)

            if len(self.equity_history) > 100:
                self.equity_history = self.equity_history[-100:]

            equity_curve = pd.Series(self.equity_history, index=returns_df.index[-len(self.equity_history) :])

            # Detect regime
            regime = self.regime_detector.detect(returns_df, equity_curve)

            if self.current_regime is None or regime.name != self.current_regime.name:
                print(f"[RiskWrapper] Regime changed: {regime.name}")

                if regime.name == "STRESS":
                    print("  WARNING: STRESS regime detected - limits tightened!")

            self.current_regime = regime

        except Exception as e:
            print(f"[RiskWrapper] Regime detection error: {e}")
            # Continue with previous regime

    def propose_rebalancing(
        self, current_positions: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Propose portfolio rebalancing to align with risk budgets.

        Args:
            current_positions: Optional current positions dict

        Returns:
            Dict of {symbol: delta_lots} - positive = buy, negative = sell
        """

        if current_positions is None:
            current_positions = self._get_current_positions()

        if not current_positions:
            print("[RiskWrapper] No positions to rebalance")
            return {}

        # Use risk governor's rebalancing helper
        target_budgets = {s: self.risk_budgets.get(s, 1.0 / len(current_positions)) for s in current_positions}

        deltas = self.governor.propose_rc_rebalance(
            positions=current_positions,
            target_rc_budget=target_budgets,
            regime=self.current_regime,
        )

        if deltas:
            print("[RiskWrapper] Rebalancing proposal:")
            for symbol, delta in deltas.items():
                action = "BUY" if delta > 0 else "SELL"
                print(f"  {symbol}: {action} {abs(delta):.3f} lots")
        else:
            print("[RiskWrapper] Portfolio already balanced")

        return deltas

    def get_risk_status(self) -> Dict:
        """Get current risk status summary."""

        current_positions = self._get_current_positions()
        equity = self.mt5_client.get_account_equity()

        # Calculate portfolio risk
        var, es, margin, rc_map = self.governor._compute_portfolio_risk(
            current_positions, equity, self.limits
        )

        return {
            "equity": equity,
            "positions": current_positions,
            "var": var,
            "es": es,
            "var_cap": equity * self.limits.var_cap_frac,
            "es_cap": equity * self.limits.es_cap_frac,
            "var_utilization": var / (equity * self.limits.var_cap_frac) if var < float("inf") else 0,
            "regime": self.current_regime.name if self.current_regime else "UNKNOWN",
            "risk_contributions": rc_map,
        }


# ============================================================================
# EXAMPLE USAGE IN EXISTING SYSTEM
# ============================================================================


def example_integration_with_existing_system():
    """Example: How to integrate into existing trading system."""

    # Your existing MT5 client
    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    # Configuration (can load from JSON)
    config = {
        "risk_management": {
            "limits": {"var_cap_frac": 0.08, "es_cap_frac": 0.12},
            "governor_config": {"timeframe": "H1", "start_pos": 0, "end_pos": 500},
        },
        "position_sizing": {"method": "fixed_risk", "config": {"risk_percent": 1.0}},
        "symbol_clusters": {"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"},
        "risk_budgets": {"EURUSD": 0.35, "GBPUSD": 0.35, "XAUUSD": 0.30},
    }

    # Initialize risk wrapper ONCE at startup
    risk_wrapper = RiskManagedTradingWrapper(mt5_client, config)

    # ========================================================================
    # Your existing trading loop
    # ========================================================================

    print("\n" + "=" * 80)
    print("EXAMPLE: Integration with Existing Trading System")
    print("=" * 80)

    # Simulate some signals from your existing strategies
    signals = [
        {
            "symbol": "EURUSD",
            "type": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "strategy": "EMA_Cross",
        },
        {
            "symbol": "GBPUSD",
            "type": "buy",
            "entry_price": 1.2500,
            "stop_loss": 1.2450,
            "strategy": "Breakout",
        },
    ]

    # ========================================================================
    # APPROACH 1: Simple - Check each trade individually
    # ========================================================================

    print("\n[APPROACH 1] Simple Individual Trade Approval:")
    print("-" * 80)

    for signal in signals:
        # Just wrap your existing execution with risk check
        if risk_wrapper.approve_trade(signal):
            print(f"  -> Executing {signal['symbol']} trade...")
            # your_existing_execution_function(signal)
        else:
            print(f"  -> Skipping {signal['symbol']} trade (rejected by risk)")

    # ========================================================================
    # APPROACH 2: Advanced - Batch processing with allocation
    # ========================================================================

    print("\n[APPROACH 2] Batch Processing with Risk Allocation:")
    print("-" * 80)

    # Calculate sizes with risk allocation
    target_sizes = risk_wrapper.calculate_position_sizes(signals, use_allocation=True)

    # Update signals with allocated sizes
    for signal in signals:
        signal["volume"] = target_sizes.get(signal["symbol"], 0.01)

    # Get current positions once
    current_positions = risk_wrapper._get_current_positions()

    # Approve each trade
    for signal in signals:
        if risk_wrapper.approve_trade(signal, current_positions):
            print(f"  -> Executing {signal['symbol']}: {signal['volume']:.3f} lots")
            # your_existing_execution_function(signal)

            # Update current_positions for next iteration
            current_positions[signal["symbol"]] = (
                current_positions.get(signal["symbol"], 0) + signal["volume"]
            )

    # ========================================================================
    # APPROACH 3: Periodic Rebalancing
    # ========================================================================

    print("\n[APPROACH 3] Periodic Rebalancing Check:")
    print("-" * 80)

    rebalance_deltas = risk_wrapper.propose_rebalancing()

    if rebalance_deltas:
        print("  Rebalancing trades to execute:")
        for symbol, delta in rebalance_deltas.items():
            print(f"    {symbol}: {delta:+.3f} lots")
            # execute_rebalancing_trade(symbol, delta)

    # ========================================================================
    # MONITORING: Get risk status
    # ========================================================================

    print("\n[MONITORING] Current Risk Status:")
    print("-" * 80)

    status = risk_wrapper.get_risk_status()

    print(f"  Equity: ${status['equity']:,.2f}")
    print(f"  Regime: {status['regime']}")
    print(f"  VaR: ${status['var']:,.2f} / ${status['var_cap']:,.2f} ({status['var_utilization']:.1%})")
    print(f"  ES: ${status['es']:,.2f} / ${status['es_cap']:,.2f}")

    if status["risk_contributions"]:
        print("\n  Risk Contributions:")
        for symbol, rc in status["risk_contributions"].items():
            print(f"    {symbol}: {rc:.1%}")

    # Cleanup
    mt5_client.shutdown()

    print("\n" + "=" * 80)
    print("INTEGRATION EXAMPLE COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    example_integration_with_existing_system()

