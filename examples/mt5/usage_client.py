"""Comprehensive MT5 client usage examples for apps.mt5.client.

Run:
    python examples/mt5/usage_client.py

Credentials:
    This example reads broker credentials from the project database via
    MT5Utils.get_mt5_credentials(). Update your default MT5 credentials there
    before running live sections.

Tip:
    Comment/uncomment function calls in main() to run only the sections you want.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.mt5 import MT5Client, MT5Utils


def _header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"[MT5 CLIENT EXAMPLE] {title}")
    print("=" * 60)
    print()




def f01_basic_lifecycle_no_login() -> None:
    _header("01_basic_lifecycle_no_login")
    client = MT5Utils.get_connected_client()
    print(f"Initial state: {client.connection_state}")
    print(f"is_connected(): {client.is_connected()}")
    client.shutdown()
    print(f"State after shutdown(): {client.connection_state}")


def f02_connect_and_disconnect() -> None:
    _header("02_connect_and_disconnect")
    client = MT5Utils.get_connected_client()
    print(f"Connected state: {client.connection_state}")
    print(f"is_connected(): {client.is_connected()}")
    client.shutdown()


def f03_fetch_bars() -> None:
    _header("03_fetch_bars")
    client = MT5Utils.get_connected_client()
    try:
        bars = client.get_bars(symbol="EURUSD", timeframe="M1", count=20)
        if bars is None or bars.empty:
            print("No bars returned.")
        else:
            print(f"Bars shape: {bars.shape}")
            print(bars.tail(3))
    finally:
        client.shutdown()


def f04_fetch_ticks() -> None:
    _header("04_fetch_ticks")
    client = MT5Utils.get_connected_client()
    try:
        ticks_df = client.get_ticks(symbol="EURUSD", count=10, as_dataframe=True)
        if ticks_df is None or ticks_df.empty:
            print("No tick dataframe returned.")
        else:
            print(f"Tick dataframe shape: {ticks_df.shape}")
            print(ticks_df.tail(3))

        ticks_list = client.get_ticks(symbol="EURUSD", count=3, as_dataframe=False)
        print(f"Tick list entries: {0 if ticks_list is None else len(ticks_list)}")
    finally:
        client.shutdown()


def f05_stream_ticks_short_run() -> None:
    _header("05_stream_ticks_short_run")
    client = MT5Utils.get_connected_client()
    events: list[dict[str, Any]] = []

    def on_tick(tick: Any) -> None:
        if isinstance(tick, dict):
            events.append(tick)

    try:
        probe = client.get_ticks(symbol="EURUSD", count=1, as_dataframe=False)
        if not probe:
            print("Skipped streaming ticks: initial tick probe returned no data.")
            return
        started = client.start_streaming(
            symbol="EURUSD",
            data_type="ticks",
            callback=on_tick,
            interval=0.1,
        )
        print(f"start_streaming(ticks) -> {started}")
        if started:
            time.sleep(2.0)
            stopped = client.stop_streaming("EURUSD", "ticks")
            print(f"stop_streaming(ticks) -> {stopped}")
            print(f"Ticks captured: {len(events)}")
    finally:
        client.shutdown()


def f06_stream_bars_short_run() -> None:
    _header("06_stream_bars_short_run")
    client = MT5Utils.get_connected_client()
    bars: list[Any] = []

    def on_bar(bar: Any) -> None:
        bars.append(bar)

    try:
        probe = client.get_bars(symbol="EURUSD", timeframe="M1", count=1)
        if probe is None or probe.empty:
            print("Skipped streaming bars: initial bar probe returned no data.")
            return
        started = client.start_streaming(
            symbol="EURUSD",
            data_type="bars",
            callback=on_bar,
            interval=1.0,
            timeframe="M1",
        )
        print(f"start_streaming(bars) -> {started}")
        if started:
            time.sleep(3.0)
            stopped = client.stop_streaming("EURUSD", "bars")
            print(f"stop_streaming(bars) -> {stopped}")
            print(f"Bars captured: {len(bars)}")
    finally:
        client.shutdown()


def f07_tick_range_query() -> None:
    _header("07_tick_range_query")
    client = MT5Utils.get_connected_client()
    try:
        end = datetime.now()
        start = end - timedelta(minutes=1)
        ticks = client.get_ticks(
            symbol="EURUSD",
            start=start,
            end=end,
            as_dataframe=True,
        )
        if ticks is None or ticks.empty:
            print("No ticks returned for range query.")
        else:
            print(f"Range ticks: {len(ticks)} rows")
    finally:
        client.shutdown()


def f08_context_manager_usage() -> None:
    _header("08_context_manager_usage")
    client = MT5Utils.get_connected_client()
    print(f"Connected inside context manager: {client.is_connected()}")


def main() -> None:
    
    # Toggle sections by commenting/uncommenting calls below.
    f01_basic_lifecycle_no_login()
    f02_connect_and_disconnect()
    f03_fetch_bars()
    f04_fetch_ticks()
    f05_stream_ticks_short_run()
    f06_stream_bars_short_run()
    f07_tick_range_query()
    f08_context_manager_usage()

    print("\n[MT5 CLIENT EXAMPLE] Done.")


if __name__ == "__main__":
    main()
