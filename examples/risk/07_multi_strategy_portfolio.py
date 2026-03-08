"""
Example 2: Multi-Strategy Portfolio with Risk Management

This example shows the COMPLETE workflow for multiple strategies:
1. Market Data (for all symbols)
2. Signal Generation (from multiple strategies)
3. Position Sizing (for each signal)
4. Regime Detection (portfolio-wide)
5. Risk Budget Allocation (balance risk across strategies)
6. Risk Governance (gate each trade)
7. Execution (only approved trades)

This demonstrates the full power of the risk module.
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import (
    PositionSizer,
    RiskBudgetAllocator,
    RiskGovernor,
    RiskLimits,
    RiskRegimeDetector,
)
from apps.risk.risk_limits import CorrelationPreference
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.trading import Engine

mt5 = get_mt5_api()


def _get_mt5_credentials():
    creds = UserManager().get_mt5_credentials()
    if not creds:
        print("No default broker credentials found.")
        return None
    return creds


class SimpleStrategy:
    """Simple EMA crossover strategy (for demonstration)."""

    def __init__(self, name: str, symbol: str, timeframe: str, fast: int, slow: int, filter: int):
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.fast = fast
        self.slow = slow
        self.filter = filter

    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal from data."""
        if len(data) < max(self.fast, self.slow, self.filter):
            return None

        # Calculate EMAs
        data["ema_fast"] = data["close"].ewm(span=self.fast, adjust=False).mean()
        data["ema_slow"] = data["close"].ewm(span=self.slow, adjust=False).mean()
        data["ema_filter"] = data["close"].ewm(span=self.filter, adjust=False).mean()

        entry_price = data["close"].iloc[-1]

        # BUY signal
        if (
            data["ema_fast"].iloc[-2] <= data["ema_slow"].iloc[-2]
            and data["ema_fast"].iloc[-1] > data["ema_slow"].iloc[-1]
            and data["close"].iloc[-1] > data["ema_filter"].iloc[-1]
        ):
            return {
                "type": "buy",
                "symbol": self.symbol,
                "entry_price": entry_price,
                "stop_loss": None,
                "reason": f"Fast({self.fast}) crossed above Slow({self.slow}), above Filter({self.filter})",
            }

        # SELL signal
        elif (
            data["ema_fast"].iloc[-2] >= data["ema_slow"].iloc[-2]
            and data["ema_fast"].iloc[-1] < data["ema_slow"].iloc[-1]
            and data["close"].iloc[-1] < data["ema_filter"].iloc[-1]
        ):
            return {
                "type": "sell",
                "symbol": self.symbol,
                "entry_price": entry_price,
                "stop_loss": None,
                "reason": f"Fast({self.fast}) crossed below Slow({self.slow}), below Filter({self.filter})",
            }

        return None


def main():
    """Run multi-strategy portfolio with risk management."""

    print("\n" + "=" * 80)
    print("EXAMPLE 2: Multi-Strategy Portfolio with Risk Management")
    print("=" * 80)

    # ============================================================================
    # SETUP: Initialize MT5 and Risk Components
    # ============================================================================

    # Initialize MT5 client
    creds = _get_mt5_credentials()
    if not creds:
        return

    mt5_client = MT5Client()
    if not mt5_client.connect(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        print("Failed to initialize MT5")
        return

    if not hasattr(mt5_client, "get_account_equity"):
        def _get_equity():
            engine_instance = Engine(backend="mt5")
            api = engine_instance.api
            account = api.account_info()
            equity = float(account.equity)
            engine_instance.client.shutdown()
            return equity
        mt5_client.get_account_equity = _get_equity  # type: ignore[attr-defined]
    if not hasattr(mt5_client, "get_positions"):
        mt5_client.get_positions = mt5.positions_get  # type: ignore[attr-defined]

    print("\n[SETUP] MT5 Connected")
    account_equity = mt5_client.get_account_equity()
    print(f"Account Equity: ${account_equity:,.2f}")

    # Configure risk limits
    limits = RiskLimits(
        var_cap_frac=0.10,  # 10% max portfolio VaR
        es_cap_frac=0.15,  # 15% max portfolio ES
        delta_var_cap_frac=0.02,  # 2% max VaR increase per trade
        max_single_rc_frac=0.35,  # 35% max from single position
        cluster_var_caps={
            "FOREX": 0.06,  # 6% max VaR from all forex
            "METALS": 0.05,  # 5% max VaR from metals
        },
    )

    # Initialize Position Sizer
    position_sizer = PositionSizer(
        method="fixed_risk",
        config={
            "risk_percent": 1.0,
            "use_dynamic_stop_loss": True,
            "atr_period": 10,
            "atr_target_devider": 3.0,
            "atr_timeframe": "H4",
        },
        mt5_client=mt5_client,
    )

    # Initialize Risk Governor
    governor = RiskGovernor(
        mt5_client=mt5_client, limits=limits, timeframe="H1", start_pos=0, end_pos=500
    )

    # Initialize Regime Detector
    regime_detector = RiskRegimeDetector(
        vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60
    )

    # Initialize Risk Budget Allocator with correlation preference
    corr_pref = CorrelationPreference(
        target_corr=0.50,  # Prefer correlations <= 0.50
        penalty_strength=2.0,  # Moderate penalty for high correlation
        min_budget_frac=0.30,  # Never reduce below 30% of budget
    )

    allocator = RiskBudgetAllocator(governor, corr_pref)

    print("[SETUP] Risk Management Components Initialized")

    # ============================================================================
    # STRATEGY CONFIGURATION
    # ============================================================================

    strategies = [
        SimpleStrategy(
            name="EURUSD_Trend",
            symbol="EURUSD",
            timeframe="M15",
            fast=20,
            slow=50,
            filter=200,
        ),
        SimpleStrategy(
            name="GBPUSD_Trend",
            symbol="GBPUSD",
            timeframe="M15",
            fast=20,
            slow=50,
            filter=200,
        ),
        SimpleStrategy(
            name="XAUUSD_Breakout",
            symbol="XAUUSD",
            timeframe="M15",
            fast=10,
            slow=30,
            filter=100,
        ),
    ]

    # Risk budgets for each strategy (must sum to ~1.0)
    risk_budgets = {
        "EURUSD": 0.30,  # 30% of portfolio risk
        "GBPUSD": 0.30,  # 30% of portfolio risk
        "XAUUSD": 0.40,  # 40% of portfolio risk
    }

    # Symbol clusters for cluster limits
    symbol_clusters = {"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"}

    print(f"\n[STRATEGIES] Configured {len(strategies)} strategies:")
    for strategy in strategies:
        budget = risk_budgets.get(strategy.symbol, 0)
        print(f"  - {strategy.name} ({strategy.symbol}) - Risk Budget: {budget:.0%}")

    # ============================================================================
    # MAIN TRADING LOOP
    # ============================================================================

    print("\n" + "=" * 80)
    print("STARTING MULTI-STRATEGY TRADING LOOP (Press Ctrl+C to stop)")
    print("=" * 80)

    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n{'=' * 80}")
            print(f"[Iteration {iteration}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

            # ================================================================
            # STEP 1: MARKET DATA
            # ================================================================
            print("\n[STEP 1] Fetching Market Data for All Strategies...")

            all_data = {}
            for strategy in strategies:
                data = mt5_client.get_bars(
                    symbol=strategy.symbol,
                    timeframe=strategy.timeframe,
                    count=250,
                    start_pos=0,
                )

                if data is None or data.empty:
                    print(f"  ⚠ {strategy.symbol}: No data available")
                    continue

                all_data[strategy.symbol] = data
                print(
                    f"  ✓ {strategy.symbol}: {len(data)} bars, Latest: {data['close'].iloc[-1]:.5f}"
                )

            if not all_data:
                print("  ✗ No data available for any strategy, skipping iteration")
                time.sleep(60)
                continue

            # ================================================================
            # STEP 2: SIGNAL GENERATION
            # ================================================================
            print("\n[STEP 2] Generating Signals from All Strategies...")

            signals = []
            for strategy in strategies:
                if strategy.symbol not in all_data:
                    continue

                signal = strategy.generate_signal(all_data[strategy.symbol])

                if signal:
                    signal["strategy_name"] = strategy.name
                    signals.append(signal)
                    print(f"  ✓ {strategy.name}: {signal['type'].upper()} signal")
                    print(f"    Reason: {signal['reason']}")

            if not signals:
                print("  ℹ No signals generated from any strategy")
                time.sleep(60)
                continue

            print(f"\n  Total Signals: {len(signals)}")

            # ================================================================
            # STEP 3: POSITION SIZING
            # ================================================================
            print("\n[STEP 3] Calculating Position Sizes for All Signals...")

            account_balance = mt5_client.get_account_equity()
            base_lots = {}

            for signal in signals:
                symbol = signal["symbol"]
                symbol_info = mt5_client.get_symbol_info(symbol)

                volume = position_sizer.calculate_size(
                    account_balance=account_balance,
                    entry_price=signal["entry_price"],
                    stop_loss=signal["stop_loss"],
                    symbol_info=symbol_info,
                    symbol=symbol,
                    signal_type=signal["type"],
                )

                signal["volume"] = volume
                base_lots[symbol] = volume

                print(f"  ✓ {symbol}: {volume:.3f} lots (1% risk)")

            # ================================================================
            # STEP 4: REGIME DETECTION
            # ================================================================
            print("\n[STEP 4] Detecting Market Regime...")

            # Build returns dataframe for all symbols
            symbols = list(all_data.keys())
            returns_data = {}

            for symbol in symbols:
                daily_data = mt5_client.get_bars(
                    symbol=symbol, timeframe="D1", count=100, start_pos=0
                )

                if daily_data is not None and not daily_data.empty and len(daily_data) >= 60:
                    returns_data[symbol] = daily_data["close"].pct_change()

            if len(returns_data) < 2:
                print("  ⚠ Insufficient data for regime detection, assuming NORMAL")
                regime = None
            else:
                returns_df = pd.DataFrame(returns_data)

                # Build equity curve (simplified - use account balance)
                equity_curve = pd.Series(
                    [account_balance] * len(returns_df), index=returns_df.index
                )

                regime = regime_detector.detect(returns_df, equity_curve)

                print(f"  ✓ Detected Regime: {regime.name}")

                if regime.name == "STRESS":
                    print("  ⚠ STRESS regime detected!")
                    print("    - VaR cap will be tightened to 7%")
                    print("    - ES cap will be tightened to 10%")
                    print("    - Correlation floor raised to 0.75")

            # ================================================================
            # STEP 5: RISK BUDGET ALLOCATION
            # ================================================================
            print("\n[STEP 5] Risk Budget Allocation...")

            # Only allocate for entry signals (not exits)
            entry_signals = [s for s in signals if s["type"] in ["buy", "sell"]]

            if not entry_signals:
                print("  ℹ No entry signals to allocate")
                target_lots = base_lots
            else:
                # Get symbols from entry signals
                entry_symbols = [s["symbol"] for s in entry_signals]
                entry_base_lots = {s: base_lots[s] for s in entry_symbols}
                entry_budgets = {s: risk_budgets.get(s, 1.0 / len(entry_symbols)) for s in entry_symbols}

                print(f"  Allocating risk across {len(entry_symbols)} positions:")
                for symbol, budget in entry_budgets.items():
                    print(f"    {symbol}: {budget:.0%} risk budget")

                # Compute target lots using allocator
                target_lots = allocator.compute_target_lots(
                    symbols=entry_symbols,
                    base_lots=entry_base_lots,
                    budgets=entry_budgets,
                    regime=regime,
                )

                print("\n  Risk-Adjusted Position Sizes:")
                for symbol in entry_symbols:
                    base = entry_base_lots[symbol]
                    target = target_lots.get(symbol, base)
                    change = target - base
                    direction = "+" if change > 0.01 else "-" if change < -0.01 else "="

                    print(
                        f"    {symbol}: {base:.3f} -> {target:.3f} lots "
                        f"({direction}{abs(change):.3f})"
                    )

                # Update signal volumes with allocated sizes
                for signal in signals:
                    if signal["symbol"] in target_lots:
                        signal["volume"] = target_lots[signal["symbol"]]

            # ================================================================
            # STEP 6: RISK GOVERNANCE
            # ================================================================
            print("\n[STEP 6] Risk Governor Review...")

            # Get current positions
            current_positions = {}
            for symbol in symbols:
                positions = mt5_client.get_positions(symbol=symbol)
                if positions:
                    total_volume = sum(pos.volume for pos in positions)
                    if total_volume > 0:
                        current_positions[symbol] = total_volume

            if current_positions:
                print("  Current Portfolio:")
                for symbol, volume in current_positions.items():
                    print(f"    {symbol}: {volume:.3f} lots")
            else:
                print("  Current Portfolio: Empty")

            # Evaluate each signal through risk governor
            approved_signals = []
            rejected_signals = []

            for signal in signals:
                symbol = signal["symbol"]
                volume = signal["volume"]

                report = governor.evaluate_add_position(
                    current_positions=current_positions,
                    candidate_symbol=symbol,
                    candidate_lots=volume,
                    symbol_to_cluster=symbol_clusters,
                    regime=regime,
                )

                print(f"\n  {signal['strategy_name']} ({symbol}):")
                print(f"    Decision: {report.decision}")
                print(f"    New VaR: ${report.new_var:,.2f} (Cap: ${account_balance * limits.var_cap_frac:,.2f})")
                print(f"    Delta VaR: ${report.delta_var:,.2f}")

                if report.decision == "ACCEPT":
                    approved_signals.append(signal)
                    # Update current positions for next evaluation
                    current_positions[symbol] = current_positions.get(symbol, 0) + volume
                else:
                    rejected_signals.append(signal)
                    print(f"    Reason: {report.reason}")

            print(f"\n  Summary: {len(approved_signals)} Approved, {len(rejected_signals)} Rejected")

            # ================================================================
            # STEP 7: EXECUTION
            # ================================================================
            print("\n[STEP 7] Trade Execution...")

            if not approved_signals:
                print("  ℹ No trades to execute")
            else:
                for signal in approved_signals:
                    print(f"\n  Executing {signal['type'].upper()}: {signal['symbol']}")
                    print(f"    Strategy: {signal['strategy_name']}")
                    print(f"    Volume: {signal['volume']:.3f} lots")
                    print(f"    Price: {signal['entry_price']:.5f}")
                    print(f"    Reason: {signal['reason']}")

                    # In real scenario, execute here:
                    # order_type = mt5_client.ORDER_TYPE_BUY if signal['type'] == 'buy' else mt5_client.ORDER_TYPE_SELL
                    # result = mt5_client.order_send(
                    #     symbol=signal['symbol'],
                    #     order_type=order_type,
                    #     volume=signal['volume'],
                    #     price=signal['entry_price'],
                    #     comment=f"{signal['strategy_name']} - Risk Managed"
                    # )

                    print("    ℹ DEMO MODE - Order not actually sent")

            # Wait before next iteration
            print("\n" + "=" * 80)
            print("Waiting 60 seconds before next iteration...")
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Trading loop stopped by user")

    finally:
        mt5_client.shutdown()
        print("[SHUTDOWN] MT5 disconnected")
        print("\n" + "=" * 80)
        print("EXAMPLE COMPLETED")
        print("=" * 80)


if __name__ == "__main__":
    main()

