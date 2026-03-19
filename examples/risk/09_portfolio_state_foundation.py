"""
Example 9: Canonical Portfolio State Foundation with Real Data

This example keeps Phase 1 small, but makes it relevant to the actual system:
- loads real historical bars from the connected MT5 client
- seeds the simulator with actual symbol metadata
- opens a couple of simulator positions through the trading API
- builds PortfolioState directly from the simulator snapshot using the
  engine-backed reconstruction helper

Run:
    python examples/risk/09_portfolio_state_foundation.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from typing import Dict, Optional

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk import PortfolioStateEngine, RiskLimits
from apps.trading import Engine, Trade, core


TIMEFRAME = "H1"
BAR_COUNT = 300
SYMBOLS = ["EURUSD", "XAUUSD"]
SYMBOL_TO_CLUSTER = {"EURUSD": "FOREX", "XAUUSD": "METALS"}


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _mutable_sim_symbol(engine: Engine, symbol_name: str) -> Optional[core.SymbolInfo]:
    for idx, symbol_row in enumerate(engine.state.trading_symbols):
        name = str(getattr(symbol_row, "name", "") or "")
        if name != symbol_name:
            continue
        if isinstance(symbol_row, core.SymbolInfo):
            return symbol_row
        mutable = core.SymbolInfo(engine._to_dict(symbol_row))
        engine.state.trading_symbols[idx] = mutable
        return mutable
    return None


def _round_volume(raw_volume: float, volume_min: float, volume_max: float, volume_step: float) -> float:
    volume = max(volume_min, min(raw_volume, volume_max))
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return float(max(volume, volume_min))


def _prepare_simulator_symbol(engine: Engine, symbol: str, latest_close: float) -> Optional[core.SymbolInfo]:
    raw_symbol = engine.client.symbol_info(symbol)
    if raw_symbol is None:
        return None

    if engine.symbol_info(symbol) is None:
        engine.state.trading_symbols.append(raw_symbol)

    mutable = _mutable_sim_symbol(engine, symbol)
    if mutable is None:
        return None

    point = float(getattr(mutable, "point", 0.0001) or 0.0001)
    spread_points = float(getattr(mutable, "spread", 2.0) or 2.0)
    spread_value = point * max(spread_points, 1.0)

    mutable.bid = float(latest_close)
    mutable.ask = float(latest_close + spread_value)
    mutable.last = float(latest_close)
    return mutable


def _load_market_data(engine: Engine, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    data = engine.client.get_bars(symbol=symbol, timeframe=timeframe, count=count, start_pos=0)
    if data is None or data.empty:
        return pd.DataFrame()
    return data.copy()


def _seed_sim_account(engine: Engine) -> None:
    account = engine.account_info()
    account["login"] = 123456
    account["server"] = "Backtest Simulation Server"
    account["company"] = "HaruQuant"
    account["balance"] = 10000.0
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = 10000.0
    account["margin"] = 0.0
    account["margin_free"] = 10000.0
    account["margin_level"] = 0.0
    account["commission"] = 7.0
    account["leverage"] = 400


def _open_example_positions(engine: Engine, market_data: Dict[str, pd.DataFrame]) -> None:
    trade = Trade(engine.api)
    requests = [
        {"symbol": "EURUSD", "side": "BUY", "target_volume": 0.10},
        {"symbol": "XAUUSD", "side": "SELL", "target_volume": 0.05},
    ]

    for request in requests:
        symbol = request["symbol"]
        if symbol not in market_data or market_data[symbol].empty:
            continue

        symbol_info = engine.symbol_info(symbol)
        if symbol_info is None:
            continue

        point = float(getattr(symbol_info, "point", 0.0001) or 0.0001)
        volume_min = float(getattr(symbol_info, "volume_min", 0.01) or 0.01)
        volume_max = float(getattr(symbol_info, "volume_max", 100.0) or 100.0)
        volume_step = float(getattr(symbol_info, "volume_step", 0.01) or 0.01)
        volume = _round_volume(
            raw_volume=float(request["target_volume"]),
            volume_min=volume_min,
            volume_max=volume_max,
            volume_step=volume_step,
        )

        trade.SetTypeFillingBySymbol(symbol)

        ask = float(getattr(symbol_info, "ask", 0.0) or 0.0)
        bid = float(getattr(symbol_info, "bid", 0.0) or 0.0)
        if request["side"] == "BUY":
            price = ask
            sl = price - (50 * point)
        else:
            price = bid
            sl = price + (50 * point)

        result = trade.PositionOpen(
            symbol=symbol,
            order_type=request["side"],
            volume=volume,
            price=price,
            sl=sl,
            tp=0.0,
            comment="Phase 1 portfolio state example",
        )

        print(
            f"{symbol} {request['side']}: retcode={int(result.retcode)} "
            f"order={int(result.order)} volume={volume:.2f}"
        )

    engine.monitor_account(verbose=False)


def main() -> None:
    _print_header("PHASE 1 PORTFOLIO STATE FOUNDATION")

    engine = Engine(backend="sim")
    try:
        _seed_sim_account(engine)

        market_data: Dict[str, pd.DataFrame] = {}
        symbol_specs: Dict[str, object] = {}

        print(f"Loading real {TIMEFRAME} data from connected client...")
        for symbol in SYMBOLS:
            data = _load_market_data(engine, symbol, TIMEFRAME, BAR_COUNT)
            if data.empty:
                print(f"{symbol}: no data available, skipped")
                continue

            market_data[symbol] = data
            close_col = "close" if "close" in data.columns else "Close"
            latest_close = float(data[close_col].iloc[-1])

            prepared_symbol = _prepare_simulator_symbol(engine, symbol, latest_close)
            if prepared_symbol is None:
                print(f"{symbol}: symbol info unavailable, skipped")
                continue

            symbol_specs[symbol] = prepared_symbol
            print(f"{symbol}: loaded {len(data)} bars, latest_close={latest_close:.5f}")

        if not market_data:
            print("No market data was loaded. Ensure the MT5 client is connected and history is available.")
            return

        print("\nOpening small simulator positions from real symbol state...")
        _open_example_positions(engine, market_data)

        state_engine = PortfolioStateEngine()
        as_of = None
        if market_data:
            latest_ts = max(df.index[-1] for df in market_data.values() if not df.empty)
            as_of = pd.Timestamp(latest_ts).isoformat()

        state = state_engine.build_state_from_engine(
            engine=engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=as_of,
            limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12),
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "simulator_plus_real_market_data",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
            },
        )
        positions = engine.positions_get()

        _print_header("CANONICAL PORTFOLIO STATE")
        print(f"Account Equity: ${float(state.account.equity):,.2f}")
        print(f"Active Symbols: {state.active_symbols}")
        print(f"Position Map: {state.position_map}")
        print(f"Exposures: {state.exposures}")
        print(f"Has Errors: {state.validation_summary.has_errors}")
        print(f"Has Warnings: {state.validation_summary.has_warnings}")

        if state.validation_summary.issues:
            print("\nValidation Issues:")
            for issue in state.validation_summary.issues:
                print(f"  [{issue.severity}] {issue.code}: {issue.message}")

        print("\nSimulator Positions:")
        for position in positions or []:
            symbol = str(getattr(position, "symbol", "") or "")
            volume = float(getattr(position, "volume", 0.0) or 0.0)
            pos_type = getattr(position, "type", "")
            print(f"  {symbol}: volume={volume:.2f} type={pos_type}")

        print("\nMarkets:")
        for symbol, market in state.markets.items():
            print(
                f"  {symbol}: timeframe={market.timeframe}, rows={market.row_count}, last_close={market.last_close}"
            )

        print("\nThis example uses real bars plus the existing simulator/trading stack.")
        print("It reconstructs the canonical state through PortfolioStateEngine.build_state_from_engine(...).")
    finally:
        if getattr(engine, "client", None) is not None:
            engine.client.shutdown()


if __name__ == "__main__":
    main()
