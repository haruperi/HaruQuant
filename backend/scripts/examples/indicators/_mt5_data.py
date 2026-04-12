"""Shared live MT5 data helpers for indicator examples."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

from backend.mcp.mt5_mcp import MT5Utils


@dataclass(frozen=True)
class IndicatorExampleArgs:
    symbol: str
    timeframe: str
    count: int


def add_common_mt5_args(parser: argparse.ArgumentParser) -> None:
    """Add common live MT5 options to an indicator example parser."""
    parser.add_argument("--symbol", default="EURUSD", help="MT5 symbol to fetch")
    parser.add_argument("--timeframe", default="H1", help="MT5 timeframe, e.g. M15, H1, D1")
    parser.add_argument("--count", type=int, default=120, help="Number of completed bars to fetch")


def parse_common_args(description: str) -> IndicatorExampleArgs:
    """Parse common live MT5 example arguments."""
    parser = argparse.ArgumentParser(description=description)
    add_common_mt5_args(parser)
    args = parser.parse_args()
    return IndicatorExampleArgs(symbol=args.symbol, timeframe=args.timeframe, count=args.count)


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
