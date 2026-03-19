"""
Example 1: Simple Single-Strategy with Risk Management

This example shows the complete workflow for a single strategy:
1. Market Data
2. Signal Generation
3. Position Sizing
4. Regime Detection
5. Risk Governance
6. Execution

No risk allocation needed for single strategy.
"""

import os
import sys
import time
from datetime import datetime

import pandas as pd

# Add repo root to path for local imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import GovernanceEngine, PortfolioRiskEngine, PositionSizer, RiskLimits, RiskRegimeDetector
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


def main():
    """Run single strategy with risk management."""

    print("\n" + "=" * 80)
    print("EXAMPLE 1: Simple Single-Strategy Trading with Risk Management")
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

    print("\n[SETUP] MT5 Connected")
    print(f"Account Equity: ${mt5_client.get_account_equity():,.2f}")

    # Configure risk limits (conservative for example)
    limits = RiskLimits(
        var_cap_frac=0.08,  # 8% max portfolio VaR
        es_cap_frac=0.12,  # 12% max portfolio ES
        delta_var_cap_frac=0.015,  # 1.5% max VaR increase per trade
        max_single_rc_frac=0.20,  # 20% max from single position
    )

    # Initialize Position Sizer (1% risk per trade)
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

    # Initialize Governance Engine
    governor = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=mt5_client,
            timeframe="H1",
            start_pos=0,
            end_pos=500,
        ),
        limits=limits,
    )

    # Initialize Regime Detector
    regime_detector = RiskRegimeDetector(
        vol_spike_mult=1.8, corr_spike_level=0.55, dd_trigger_frac=0.05, lookback=60
    )

    print("[SETUP] Risk Management Components Initialized")
    print(f"  - Position Sizing: Fixed Risk 1%")
    print(f"  - VaR Cap: {limits.var_cap_frac:.0%}")
    print(f"  - ES Cap: {limits.es_cap_frac:.0%}")

    # ============================================================================
    # STRATEGY CONFIGURATION
    # ============================================================================

    symbol = "EURUSD"
    timeframe = "M5"
    magic_number = 100001

    print(f"\n[STRATEGY] {symbol} Trend Following on {timeframe}")

    # ============================================================================
    # MAIN TRADING LOOP
    # ============================================================================

    print("\n" + "=" * 80)
    print("STARTING TRADING LOOP (single demonstration iteration)")
    print("=" * 80)

    try:
        iteration = 0
        max_iterations = 1
        while iteration < max_iterations:
            iteration += 1
            print(f"\n[Iteration {iteration}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # ================================================================
            # STEP 1: MARKET DATA
            # ================================================================
            print("\n[STEP 1] Fetching Market Data...")

            # Fetch current bars for strategy
            data = mt5_client.get_bars(symbol=symbol, timeframe=timeframe, count=200, start_pos=0)

            if data is None or data.empty:
                print("  [WARN] No data available, skipping iteration")
                continue

            print(f"  [OK] Fetched {len(data)} bars")
            print(f"  Latest Close: {data['close'].iloc[-1]:.5f}")

            # ================================================================
            # STEP 2: SIGNAL GENERATION
            # ================================================================
            print("\n[STEP 2] Generating Signal...")

            # Simple EMA crossover strategy (example)
            data["ema_fast"] = data["close"].ewm(span=20, adjust=False).mean()
            data["ema_slow"] = data["close"].ewm(span=50, adjust=False).mean()
            data["ema_filter"] = data["close"].ewm(span=200, adjust=False).mean()

            # Check for signal on latest bar
            signal = None
            entry_price = data["close"].iloc[-1]

            # BUY signal: Fast crosses above Slow, and price above filter
            if (
                data["ema_fast"].iloc[-2] <= data["ema_slow"].iloc[-2]
                and data["ema_fast"].iloc[-1] > data["ema_slow"].iloc[-1]
                and data["close"].iloc[-1] > data["ema_filter"].iloc[-1]
            ):
                signal = {
                    "type": "buy",
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "stop_loss": None,  # Will be calculated dynamically
                    "reason": "EMA Fast crossed above Slow, price above filter",
                }

            # SELL signal: Fast crosses below Slow, and price below filter
            elif (
                data["ema_fast"].iloc[-2] >= data["ema_slow"].iloc[-2]
                and data["ema_fast"].iloc[-1] < data["ema_slow"].iloc[-1]
                and data["close"].iloc[-1] < data["ema_filter"].iloc[-1]
            ):
                signal = {
                    "type": "sell",
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "stop_loss": None,  # Will be calculated dynamically
                    "reason": "EMA Fast crossed below Slow, price below filter",
                }

            if signal is None:
                print("  [INFO] No signal generated")
                continue

            print(f"  [OK] Signal: {signal['type'].upper()}")
            print(f"  Entry: {signal['entry_price']:.5f}")
            print(f"  Reason: {signal['reason']}")

            # ================================================================
            # STEP 3: POSITION SIZING
            # ================================================================
            print("\n[STEP 3] Calculating Position Size...")

            account_balance = mt5_client.get_account_equity()
            symbol_info = mt5_client.get_symbol_info(symbol)

            # Calculate position size (stop loss calculated dynamically if None)
            volume = position_sizer.calculate_size(
                account_balance=account_balance,
                entry_price=signal["entry_price"],
                stop_loss=signal["stop_loss"],
                symbol_info=symbol_info,
                symbol=symbol,
                signal_type=signal["type"],
            )

            print(f"  [OK] Calculated Size: {volume:.3f} lots")
            print(f"  Account Balance: ${account_balance:,.2f}")
            print(f"  Risk: 1% = ${account_balance * 0.01:,.2f}")

            # ================================================================
            # STEP 4: REGIME DETECTION
            # ================================================================
            print("\n[STEP 4] Detecting Market Regime...")

            # Build returns dataframe for regime detection
            # For single strategy, we just need data for the one symbol
            daily_data = mt5_client.get_bars(symbol=symbol, timeframe="D1", count=100, start_pos=0)

            if daily_data is None or daily_data.empty or len(daily_data) < 60:
                print("  [WARN] Insufficient data for regime detection, assuming NORMAL")
                regime = None
            else:
                # Calculate returns
                returns = pd.DataFrame()
                returns[symbol] = daily_data["close"].pct_change()

                # Simple equity curve (for example, use account balance)
                equity_curve = pd.Series(
                    [account_balance] * len(daily_data), index=daily_data.index
                )

                # Detect regime
                regime = regime_detector.detect(returns, equity_curve)
                print(f"  [OK] Detected Regime: {regime.name}")

                if regime.name == "STRESS":
                    print("  [WARN] STRESS regime - limits will be tightened!")

            # ================================================================
            # STEP 5: SKIP ALLOCATION (Single Strategy)
            # ================================================================
            print("\n[STEP 5] Risk Budget Allocation...")
            print("  [INFO] Skipped (only needed for multi-strategy)")

            # ================================================================
            # STEP 6: RISK GOVERNANCE
            # ================================================================
            print("\n[STEP 6] Governance Engine Review...")

            # Get current positions
            current_positions = {}
            positions = mt5_client.get_positions(symbol=symbol)
            if positions:
                total_volume = sum(pos.volume for pos in positions)
                if total_volume > 0:
                    current_positions[symbol] = total_volume
                    print(f"  Current Position: {symbol} {total_volume:.3f} lots")

            # Evaluate trade through governance engine
            report = governor.evaluate_add_position(
                current_positions=current_positions,
                candidate_symbol=symbol,
                candidate_lots=volume,
                regime=regime,
            )

            print(f"\n  Decision: {report.decision}")
            print(f"  Reason: {report.reason}")
            print(f"  Current VaR: ${report.current_var:,.2f}")
            print(f"  New VaR: ${report.new_var:,.2f}")
            print(f"  Delta VaR: ${report.delta_var:,.2f}")
            print(f"  New ES: ${report.new_es:,.2f}")

            # ================================================================
            # STEP 7: EXECUTION
            # ================================================================
            print("\n[STEP 7] Trade Execution...")

            if report.decision == "REJECT":
                print("  [REJECT] Trade rejected by Governance Engine")
                print(f"  Reason: {report.reason}")
            else:
                print("  [OK] Trade approved by Governance Engine")

                # Execute the trade
                order_type = mt5_client.ORDER_TYPE_BUY if signal["type"] == "buy" else mt5_client.ORDER_TYPE_SELL

                print(f"\n  Executing {signal['type'].upper()} order:")
                print(f"    Symbol: {symbol}")
                print(f"    Volume: {volume:.3f} lots")
                print(f"    Price: {signal['entry_price']:.5f}")

                # In a real scenario, you would execute here:
                # result = mt5_client.order_send(
                #     symbol=symbol,
                #     order_type=order_type,
                #     volume=volume,
                #     price=signal['entry_price'],
                #     magic=magic_number,
                #     comment="Risk-managed trade"
                # )

                print("  [INFO] DEMO MODE - Order not actually sent")

            # Wait before next iteration
            if iteration < max_iterations:
                print("\n" + "-" * 80)
                print("Waiting 30 seconds before next iteration...")
                time.sleep(30)

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

