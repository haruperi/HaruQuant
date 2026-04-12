"""
Usage Example: Position Sizing Methods with Live MT5 Data

This script demonstrates all 6 position sizing methods using real MT5 prices:
1. fixed_lot
2. milestone
3. fixed_risk
4. kelly
5. volatility (ATR-based)
6. fixed_fractional

Run:
    python backend/scripts/examples/risk/01_position_sizing.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import pandas as pd

from backend.mcp.mt5_mcp import MT5Client, get_mt5_api
from backend.services.risk_engine import PositionSizer
from backend.services.indicators.volatility.atr import atr
from backend.data.database.sqlite.users import UserManager
from backend.services.simulation.engine import Engine

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
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return None
    return mt5_client


def _get_latest_price(mt5_client: MT5Client, symbol: str, timeframe: str) -> Optional[float]:
    data = mt5_client.get_bars(symbol=symbol, timeframe=timeframe, count=200, start_pos=0)
    if data is None or data.empty:
        return None
    return float(data["close"].iloc[-1])


def _get_latest_atr(
    mt5_client: MT5Client,
    symbol: str,
    timeframe: str,
    period: int,
) -> Optional[float]:
    bars_needed = period + 50
    data = mt5_client.get_bars(symbol=symbol, timeframe=timeframe, count=bars_needed, start_pos=0)
    if data is None or data.empty or len(data) < period:
        return None

    data_with_atr = atr(data, period=period)
    atr_col = f"atr_{period}"
    if atr_col not in data_with_atr.columns:
        return None

    latest = float(data_with_atr[atr_col].iloc[-2])
    if pd.isna(latest) or latest <= 0:
        return None

    return latest


def _build_stop_loss(entry_price: float, symbol: str, signal_type: str) -> float:
    # Simple fixed distance stop (50 pips for non-JPY, 0.50 for JPY pairs)
    pip_distance = 0.50 if "JPY" in symbol.upper() else 0.005
    if signal_type.lower() == "sell":
        return entry_price + pip_distance
    return entry_price - pip_distance


def main() -> None:
    print("\n" + "=" * 80)
    print("POSITION SIZING METHODS - LIVE MT5 DATA")
    print("=" * 80)

    mt5_client = _connect_mt5()
    if not mt5_client:
        return

    try:
        symbol = "EURUSD"
        price_timeframe = "M5"
        atr_timeframe = "D1"
        atr_period = 10
        signal_type = "buy"

        engine_instance = Engine(backend="mt5")
        api = engine_instance.api
        account = api.account_info()
        account_balance = float(account.equity)
        if account_balance <= 0:
            print("Failed to fetch account equity from MT5.")
            return

        # Custom Account Balance
        account_balance = 1000

        symbol_info = None
        raw_symbol_info = mt5.symbol_info(symbol)
        if raw_symbol_info is None:
            print(f"Failed to fetch symbol info for {symbol}.")
            return
        point_value = float(getattr(raw_symbol_info, "point", 0.0))

        entry_price = _get_latest_price(mt5_client, symbol, price_timeframe)
        if entry_price is None:
            print(f"No price data available for {symbol} on {price_timeframe}")
            return

        latest_atr = _get_latest_atr(mt5_client, symbol, atr_timeframe, atr_period)

        print(f"Account Balance: ${account_balance:,.2f}")
        print(f"Symbol: {symbol}")
        print(f"Entry Price ({price_timeframe}): {entry_price:.5f}")
        if latest_atr is not None:
            print(f"ATR({atr_period}) [{atr_timeframe}]: {latest_atr:.5f}")
        else:
            print(f"ATR({atr_period}) [{atr_timeframe}]: unavailable")

        if latest_atr is not None:
            stop_distance = latest_atr / 3.0
            if signal_type.lower() == "sell":
                stop_loss = entry_price + stop_distance
            else:
                stop_loss = entry_price - stop_distance
        else:
            stop_loss = _build_stop_loss(entry_price, symbol, signal_type)
            stop_distance = abs(entry_price - stop_loss)

        print("\n" + "-" * 80)
        print("1) Fixed Lot")
        sizer_fixed_lot = PositionSizer(method="fixed_lot", config={"lot_size": 0.2})
        size_fixed_lot = sizer_fixed_lot.calculate_size(
            account_balance=account_balance,
            entry_price=entry_price,
            symbol_info=symbol_info,
        )
        print(f"Size: {size_fixed_lot:.4f} lots (fixed)")

        print("\n" + "-" * 80)
        print("2) Milestone")
        sizer_milestone = PositionSizer(
            method="milestone",
            config={
                "initial_balance": 1000.0,
                "base_lot_size": 0.1,
                "milestone_amount": 3000.0,
                "lot_increment": 0.1,
            },
        )
        size_milestone = sizer_milestone.calculate_size(
            account_balance=account_balance,
            entry_price=entry_price,
            symbol_info=symbol_info,
        )
        print(f"Size: {size_milestone:.4f} lots (milestone)")

        print("\n" + "-" * 80)
        print("3) Fixed Risk (1% per trade)")
        sizer_fixed_risk = PositionSizer(
            method="fixed_risk",
            config={"risk_percent": 1.0, "use_dynamic_stop_loss": False},
        )
        size_fixed_risk = sizer_fixed_risk.calculate_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=stop_loss,
            symbol_info=symbol_info,
            symbol=symbol,
            signal_type=signal_type,
        )
        if point_value > 0:
            stop_pips = stop_distance / point_value / 10
            print(f"Stop Loss: {stop_loss:.5f} Stop Loss Pips: {stop_pips:.2f}")
        else:
            print(f"Stop Loss: {stop_loss:.5f}")
        print(f"Size: {size_fixed_risk:.4f} lots (fixed risk)")

        print("\n" + "-" * 80)
        print("4) Kelly Criterion")
        sizer_kelly = PositionSizer(
            method="kelly",
            config={
                "kelly_fraction_limit": 0.25,
                "win_rate": 0.55,
                "avg_win": 150.0,
                "avg_loss": 100.0,
            },
        )
        size_kelly = sizer_kelly.calculate_size(
            account_balance=account_balance,
            entry_price=entry_price,
            symbol_info=symbol_info,
        )
        print(f"Size: {size_kelly:.4f} lots (kelly)")

        print("\n" + "-" * 80)
        print("5) Volatility (ATR-based)")
        if latest_atr is None:
            print("ATR not available; skipping volatility sizing.")
        else:
            sizer_volatility = PositionSizer(
                method="volatility",
                config={"risk_percent": 1.5, "atr_multiplier": 1.0},
            )
            size_volatility = sizer_volatility.calculate_size(
                account_balance=account_balance,
                entry_price=entry_price,
                context={"atr": latest_atr},
                symbol_info=symbol_info,
            )
            print(f"Size: {size_volatility:.4f} lots (volatility)")

        print("\n" + "-" * 80)
        print("6) Fixed Fractional (2% of capital)")
        sizer_fixed_fractional = PositionSizer(
            method="fixed_fractional",
            config={"fraction": 2.0},
        )
        size_fixed_fractional = sizer_fixed_fractional.calculate_size(
            account_balance=account_balance,
            entry_price=entry_price,
            symbol_info=symbol_info,
        )
        print(f"Size: {size_fixed_fractional:.4f} lots (fixed fractional)")

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        if 'engine_instance' in locals():
            engine_instance.client.shutdown()
        mt5_client.shutdown()


if __name__ == "__main__":
    main()

