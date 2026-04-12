"""Run a backend strategy on live MT5 bars and emit a canonical signal intent.

This example is read-only: it fetches real broker data and routes the resulting
signal intent to a print handler. It does not place orders.

Run from the repository root:
    python backend/scripts/examples/strategies/live_strategy_demo.py --symbol EURUSD --timeframe H1 --count 120
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.common.logger import logger  # noqa: E402
from backend.mcp.mt5_mcp import MT5Utils  # noqa: E402
from backend.services.indicators import ema  # noqa: E402
from backend.services.strategy import BaseStrategy, SignalDict, SignalRouter, StrategyAdapter  # noqa: E402


class LiveEmaCrossoverStrategy(BaseStrategy):
    """Simple EMA crossover strategy for live-data signal demonstration."""

    def __init__(self, params: Optional[dict[str, object]] = None) -> None:
        super().__init__(params)
        self.fast_span = int(self.params.get("fast_span", 12))
        self.slow_span = int(self.params.get("slow_span", 26))

    def on_init(self) -> None:
        logger.info(
            f"Initialized {self.strategy_id} for {self.symbol}: fast={self.fast_span}, slow={self.slow_span}"
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        result = ema(data, span=self.fast_span)
        result = ema(result, span=self.slow_span)
        fast_col = f"ema_{self.fast_span}"
        slow_col = f"ema_{self.slow_span}"

        previous_fast = result[fast_col].shift(1)
        previous_slow = result[slow_col].shift(1)
        crossed_up = (previous_fast <= previous_slow) & (result[fast_col] > result[slow_col])
        crossed_down = (previous_fast >= previous_slow) & (result[fast_col] < result[slow_col])

        result["entry_signal"] = 0
        result.loc[crossed_up, "entry_signal"] = 1
        result.loc[crossed_down, "entry_signal"] = -1
        result["exit_signal"] = 0
        result["pending_signal"] = 0
        result["cancel_pending_signal"] = 0
        result["price"] = result["close"]
        return result

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        signal = super().get_signal(data, index)
        if signal is None:
            return None

        direction = "bullish" if signal["entry_signal"] == 1 else "bearish"
        signal["reason"] = f"{direction} EMA crossover on {self.symbol}"
        signal["stop_loss"] = None
        signal["take_profit"] = None
        return signal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a read-only live MT5 strategy signal demo.")
    parser.add_argument("--symbol", default="EURUSD", help="MT5 symbol to fetch")
    parser.add_argument("--timeframe", default="H1", help="MT5 timeframe, e.g. M15, H1, D1")
    parser.add_argument("--count", type=int, default=120, help="Number of bars to fetch")
    parser.add_argument("--fast-span", type=int, default=12, help="Fast EMA span")
    parser.add_argument("--slow-span", type=int, default=26, help="Slow EMA span")
    parser.add_argument("--qty", type=float, default=0.01, help="Intent quantity in lots")
    return parser.parse_args()


def fetch_live_bars(symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    """Fetch live broker bars through the migrated MT5 MCP client boundary."""
    client = MT5Utils.get_connected_client()
    if client is None:
        raise RuntimeError("Could not connect to MT5 through backend.mcp.mt5_mcp")
    try:
        bars = client.get_bars(symbol=symbol, timeframe=timeframe, count=count)
    finally:
        client.shutdown()

    if bars is None or bars.empty:
        raise RuntimeError(f"No MT5 bars returned for {symbol} {timeframe}")
    return bars


def run_strategy() -> None:
    args = parse_args()
    logger.info(
        f"Running read-only EMA crossover strategy on {args.symbol} {args.timeframe} with {args.count} live MT5 bars"
    )
    data = fetch_live_bars(args.symbol, args.timeframe, args.count)

    strategy = LiveEmaCrossoverStrategy(
        {
            "symbol": args.symbol,
            "strategy_id": "live_ema_crossover_demo",
            "fast_span": args.fast_span,
            "slow_span": args.slow_span,
        }
    )
    strategy.on_init()
    adapter = StrategyAdapter(strategy, default_qty=args.qty)
    enriched = adapter.on_bar(data)

    intent = adapter.build_signal_intent(
        enriched,
        len(enriched) - 1,
        features={
            f"ema_{args.fast_span}": enriched[f"ema_{args.fast_span}"].iloc[-1],
            f"ema_{args.slow_span}": enriched[f"ema_{args.slow_span}"].iloc[-1],
            "close": enriched["close"].iloc[-1],
        },
        tags=["read_only", "live_mt5_data", "example"],
        metadata={"timeframe": args.timeframe, "bar_count": args.count},
    )

    latest = enriched.tail(5)[["close", f"ema_{args.fast_span}", f"ema_{args.slow_span}", "entry_signal"]]
    print(latest.round(6).to_string())

    if intent is None:
        print("No actionable signal on the latest bar.")
        return

    router = SignalRouter(handler=lambda routed: print(f"ROUTED_INTENT={routed}"))
    router.route(intent)


if __name__ == "__main__":
    run_strategy()
