"""Volatility indicator example using live MT5 data and backend indicator services.

Run from the repository root:
    python backend/scripts/examples/indicators/volatility_indicators_demo.py --symbol EURUSD --timeframe H1 --count 120
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from backend.common.logger import logger  # noqa: E402
from backend.services.indicators import atr, bbands  # noqa: E402
from _mt5_data import fetch_live_bars, parse_common_args  # noqa: E402


def _keltner_channel(data: pd.DataFrame, *, period: int = 20, atr_multiplier: float = 2.0) -> pd.DataFrame:
    middle = data["close"].ewm(span=period, adjust=False).mean()
    range_atr = data["atr_14"]
    return pd.DataFrame(
        {
            "kc_middle": middle,
            "kc_upper": middle + (range_atr * atr_multiplier),
            "kc_lower": middle - (range_atr * atr_multiplier),
        },
        index=data.index,
    )


def _standard_deviation(data: pd.DataFrame, *, period: int = 20) -> pd.Series:
    stddev = data["close"].rolling(period, min_periods=period).std(ddof=0)
    stddev.name = f"stddev_{period}"
    return stddev


def compute_volatility_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute Bollinger Bands and ATR plus local Keltner/stddev demo columns."""
    result = bbands(data, period=20, std_dev=2.0)
    result = atr(result, period=14)
    return result.join(_keltner_channel(result)).join(_standard_deviation(result))


def main() -> None:
    args = parse_common_args("Compute volatility indicators from live MT5 bars.")
    logger.info(
        f"Starting volatility indicator demo for {args.symbol} {args.timeframe} with {args.count} live MT5 bars"
    )
    enriched = compute_volatility_indicators(fetch_live_bars(args.symbol, args.timeframe, args.count))
    latest = enriched.tail(5)[
        [
            "close",
            "bb_middle_20_2",
            "bb_upper_20_2",
            "bb_lower_20_2",
            "atr_14",
            "kc_middle",
            "kc_upper",
            "kc_lower",
            "stddev_20",
        ]
    ]
    logger.info(f"Computed volatility indicators. Latest values:\n{latest}")
    print(latest.round(6).to_string())


if __name__ == "__main__":
    main()
