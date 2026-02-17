"""Usage example: IP-11 multi-symbol synchronized ingestion with real MT5 data."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.adapters.multisymbol_ingestion import MultiSymbolIngestionPipeline
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger


def get_mt5_credentials() -> dict:
    creds = UserManager().get_mt5_credentials()
    if not creds:
        raise RuntimeError("No default MT5 credentials found in database")
    return creds


def fetch_symbol_bars(
    client: MT5Client,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    df = client.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        date_from=start,
        date_to=end,
    )
    if df is None or df.empty:
        raise RuntimeError(f"No bars returned for {symbol} ({timeframe})")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise RuntimeError(f"{symbol} bars missing DatetimeIndex")
    return df.sort_index()


def main() -> None:
    print("=" * 70)
    print("IP-11 REAL MT5 MULTI-SYMBOL INGESTION EXAMPLE")
    print("=" * 70)

    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframe = "M15"
    end = datetime.now()
    start = end - timedelta(days=7)

    creds = get_mt5_credentials()
    client = MT5Client()

    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise RuntimeError("Failed to connect to MT5")

    try:
        data_by_symbol: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            data_by_symbol[symbol] = fetch_symbol_bars(
                client=client,
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            print(f"{symbol}: fetched {len(data_by_symbol[symbol])} bars")

        synced, summary = MultiSymbolIngestionPipeline.synchronize(
            data_by_symbol=data_by_symbol,
            method="ffill",
            handle_leading_nans="drop",
            handle_trailing_nans="drop",
        )

        print("---- Synchronization summary ----")
        print(f"symbols: {summary.symbols}")
        print(f"rows_before: {summary.rows_before}")
        print(f"rows_after: {summary.rows_after}")
        print(f"common_rows: {summary.common_rows}")

        for symbol, df in synced.items():
            print(
                f"{symbol}: {df.index[0]} -> {df.index[-1]}, columns={list(df.columns)}"
            )

        print("---- Synced data preview ----")
        print(synced)
        

    finally:
        client.shutdown()
        print("MT5 connection closed")


if __name__ == "__main__":
    main()
