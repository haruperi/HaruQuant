#!/usr/bin/env python
"""Example 07: Edge Fixture Pipeline Demo.

Type: fixture-based deterministic demo

This example prepares a small synthetic OHLCVS dataset and shows the shared
session labeling used by the Edge pipeline without requiring MT5.

Run:
    python examples/edge/07_fixture_pipeline_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.edge.datasets import prepare_ohlcvs_dataset


class FixtureSource:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def fetch_data(self, symbol: str, timeframe: str, start_pos: int, end_pos: int) -> pd.DataFrame:
        return self._frame.copy()


def main() -> None:
    index = pd.to_datetime(
        [
            "2024-01-01 01:00:00",
            "2024-01-01 03:00:00",
            "2024-01-01 15:00:00",
            "2024-01-01 23:00:00",
        ]
    )
    frame = pd.DataFrame(
        {
            "Open": [1.1000, 1.1002, 1.1004, 1.1006],
            "High": [1.1005, 1.1007, 1.1009, 1.1010],
            "Low": [1.0998, 1.1000, 1.1002, 1.1004],
            "Close": [1.1002, 1.1004, 1.1006, 1.1008],
            "Volume": [10, 11, 12, 13],
            "Spread": [1, 1, 1, 1],
        },
        index=index,
    )

    prepared = prepare_ohlcvs_dataset(
        FixtureSource(frame),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=4,
        exclude_last_bar=False,
    )

    print("Example type: fixture-based deterministic demo")
    print(f"rows={len(prepared.data)} valid={prepared.report.is_valid}")
    print("sessions=" + ",".join(prepared.data["session"].tolist()))
    print("session_hours=" + str(prepared.report.metadata["session_hours"]))


if __name__ == "__main__":
    main()
