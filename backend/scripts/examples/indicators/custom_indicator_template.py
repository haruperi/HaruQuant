"""Custom indicator template using live MT5 data and backend validation helpers.

Copy this file and adapt `custom_zscore` for your own indicator.

Run from the repository root:
    python backend/scripts/examples/indicators/custom_indicator_template.py --symbol EURUSD --timeframe H1 --count 120
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

    from haruquant.utils import logger
from haruquant.indicator import require_columns, require_dataframe, require_positive_int
from _mt5_data import fetch_live_bars, parse_common_args  # noqa: E402


def custom_zscore(
    data: pd.DataFrame,
    *,
    period: int = 20,
    source: str = "close",
    output_col: str | None = None,
) -> pd.DataFrame:
    """Return a copy of `data` with a rolling z-score column."""
    require_dataframe(data)
    require_columns(data, [source])
    require_positive_int(period, name="period")

    result = data.copy()
    mean = result[source].rolling(window=period, min_periods=period).mean()
    std = result[source].rolling(window=period, min_periods=period).std(ddof=0)
    result[output_col or f"zscore_{period}"] = (result[source] - mean) / std
    return result


def demo() -> None:
    """Demonstrate template usage."""
    args = parse_common_args("Compute a custom z-score from live MT5 bars.")
    logger.info(
        f"Starting custom z-score demo for {args.symbol} {args.timeframe} with {args.count} live MT5 bars"
    )
    data = fetch_live_bars(args.symbol, args.timeframe, args.count)
    result = custom_zscore(data, period=3)
    latest = result.tail(5)
    logger.info(f"Custom z-score latest values:\n{latest}")
    print(latest.round(6).to_string())


if __name__ == "__main__":
    demo()
