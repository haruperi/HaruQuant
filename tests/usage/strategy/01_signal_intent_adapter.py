"""Usage example: StrategyAdapter + SignalRouter canonical SignalIntent flow."""

from __future__ import annotations

import os
import sys

import pandas as pd

# Allow running this usage file directly from repository root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.strategy import BaseStrategy, SignalRouter, StrategyAdapter


class ExampleStrategy(BaseStrategy):
    def on_init(self) -> None:
        self.state["initialized"] = True

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        out = data.copy()
        out["entry_signal"] = 0
        out["exit_signal"] = 0
        out["price"] = out["close"]
        out.iloc[-1, out.columns.get_loc("entry_signal")] = 1
        return out

    def get_signal(self, data: pd.DataFrame, index: int):
        signal = super().get_signal(data, index)
        if signal is None:
            return None
        signal["reason"] = "example crossover"
        signal["features"] = {"ema_fast": 1.1010, "ema_slow": 1.1002}
        signal["confidence"] = 0.76
        signal["tags"] = {"regime": "trend"}
        signal["metadata"] = {"source": "usage_example"}
        signal["volume"] = 0.10
        signal["order_type"] = "MARKET"
        signal["time_in_force"] = "GTC"
        return signal


def main() -> None:
    strategy = ExampleStrategy({"symbol": "EURUSD", "strategy_id": "example-1"})
    strategy.on_init()

    adapter = StrategyAdapter(strategy)
    routed = []
    router = SignalRouter(handler=lambda intent: routed.append(intent))

    bars = pd.DataFrame(
        [{"close": 1.1000}, {"close": 1.1015}],
        index=[pd.Timestamp("2026-02-18T10:00:00Z"), pd.Timestamp("2026-02-18T10:01:00Z")],
    )

    bars = adapter.on_bar(bars)
    intent = adapter.build_signal_intent(bars, len(bars) - 1)
    if intent is None:
        print("No signal intent generated.")
        return

    event = adapter.event_for_signal(intent, run_id="run-1", trace_id="trace-1", correlation_id="corr-1")
    router.route(intent)

    print("SignalIntent:")
    print(intent)
    print("\nStrategyEvent envelope:")
    print(event)
    print(f"\nRouted intents: {len(routed)}")


if __name__ == "__main__":
    main()
