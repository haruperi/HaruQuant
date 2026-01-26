"""Synthetic tick generator for tester mode."""

from __future__ import annotations

from typing import Any


class TicksGen:
    """Generate synthetic ticks from 1-minute bars."""

    @staticmethod
    def generate_ticks_from_bars(
        bars: list[dict[str, Any]],
        symbol: str,
        symbol_point: float,
    ) -> list[dict[str, Any]]:
        """Generate synthetic ticks from a sequence of bars."""
        ticks: list[dict[str, Any]] = []
        for bar in bars:
            open_price = float(bar.get("open", 0.0))
            high_price = float(bar.get("high", open_price))
            low_price = float(bar.get("low", open_price))
            close_price = float(bar.get("close", open_price))
            base_time = int(bar.get("time", 0))
            spread = float(bar.get("spread", 0.0))
            tick_volume = int(bar.get("tick_volume", 0))
            real_volume = float(bar.get("real_volume", 0.0))

            prices = [open_price, high_price, low_price, close_price]
            for idx, price in enumerate(prices):
                ticks.append(
                    {
                        "symbol": symbol,
                        "time": base_time + idx * 10,
                        "bid": price,
                        "ask": price + spread * symbol_point,
                        "last": price,
                        "volume": tick_volume,
                        "time_msc": (base_time + idx * 10) * 1000,
                        "flags": 0,
                        "volume_real": real_volume,
                    }
                )
        return ticks
