#!/usr/bin/env python
"""OHLCVS Pipeline Example.

Type: live-broker dependent manual demo

Prepare an analysis-ready OHLCVS dataset for Edge Lab.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from services.research import CleaningConfig, EnrichmentConfig, prepare_ohlcvs_dataset  # noqa: E402


class DemoSource:
    """Small demo source with one missing bar and synthesized spread/volume."""

    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_pos: int,
        end_pos: int,
    ) -> pd.DataFrame:
        idx = pd.to_datetime(
            [
                "2024-01-02 00:00:00",
                "2024-01-02 00:01:00",
                "2024-01-02 00:03:00",
                "2024-01-02 00:04:00",
            ]
        )

        rng = np.random.default_rng(7)
        close = 1.1000 + np.cumsum(rng.normal(0.0, 0.00015, len(idx)))
        open_ = np.roll(close, 1)
        open_[0] = close[0]
        high = np.maximum(open_, close) + 0.0002
        low = np.minimum(open_, close) - 0.0002

        return pd.DataFrame(
            {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
            },
            index=idx,
        )


def main() -> None:
    prepared = prepare_ohlcvs_dataset(
        DemoSource(),
        symbol="EURUSD",
        timeframe="M1",
        start_pos=0,
        end_pos=10,
        exclude_last_bar=False,
        cleaning=CleaningConfig(
            timeframe="M1",
            missing_bar_policy="ffill_close",
            broker_timezone="UTC",
            output_timezone="UTC",
        ),
        enrichment=EnrichmentConfig(symbol="EURUSD", rollover_hour_utc=21),
    )

    print("OHLCVS Pipeline Example")
    print(f"Rows: {len(prepared.data)}")
    print(f"Valid: {prepared.report.is_valid}")
    print(f"Warnings: {len(prepared.report.warnings)}")
    print(f"Fatal errors: {len(prepared.report.fatal_errors)}")
    print(f"Cleaning actions: {len(prepared.report.cleaning_actions)}")
    print()

    if prepared.report.warnings:
        print("Warnings:")
        for issue in prepared.report.warnings:
            print(f"  - {issue.code}: {issue.message} (count={issue.count})")
        print()

    if prepared.report.cleaning_actions:
        print("Cleaning actions:")
        for action in prepared.report.cleaning_actions:
            print(f"  - {action.action}: {action.count}")
        print()

    print("Selected enriched columns:")
    selected = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Spread",
        "returns",
        "log_returns",
        "body_pips",
        "range_pips",
        "session",
        "hour",
        "weekday",
        "is_rollover_hour",
    ]
    print(prepared.data[selected].head().to_string())


if __name__ == "__main__":
    main()
