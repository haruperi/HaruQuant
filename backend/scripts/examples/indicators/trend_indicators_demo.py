"""Trend indicator example using live MT5 data and backend indicator services.

Run from the repository root:
    python backend/scripts/examples/indicators/trend_indicators_demo.py --symbol EURUSD --timeframe H1 --count 120
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

from services.utils.logger import logger  # noqa: E402
from services.indicator import ema, sma, wma  # noqa: E402
from _mt5_data import fetch_live_bars, parse_common_args  # noqa: E402


def _macd(data: pd.DataFrame, *, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute MACD locally; backend services currently expose EMA, not MACD."""
    fast_ema = data["close"].ewm(span=fast, adjust=False).mean()
    slow_ema = data["close"].ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_hist": macd_line - signal_line,
        },
        index=data.index,
    )


def _adx(data: pd.DataFrame, *, period: int = 14) -> pd.DataFrame:
    """Compute a compact ADX demonstration formula using pandas."""
    high = data["high"]
    low = data["low"]
    close = data["close"]

    plus_dm = (high.diff()).where(lambda s: (s > (-low.diff())) & (s > 0), 0.0)
    minus_dm = (-low.diff()).where(lambda s: (s > high.diff()) & (s > 0), 0.0)
    tr = pd.concat(
        [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    plus_di = 100 * plus_dm.rolling(period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.rolling(period, min_periods=period).mean() / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di)) * 100
    adx_value = dx.rolling(period, min_periods=period).mean()
    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "adx": adx_value}, index=data.index)


def compute_trend_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute SMA, EMA, WMA plus local MACD and ADX demo columns."""
    result = sma(data, window=14)
    result = ema(result, span=14)
    result = wma(result, window=14)
    return result.join(_macd(result)).join(_adx(result))


def main() -> None:
    args = parse_common_args("Compute trend indicators from live MT5 bars.")
    logger.info(
        f"Starting trend indicator demo for {args.symbol} {args.timeframe} with {args.count} live MT5 bars"
    )
    enriched = compute_trend_indicators(fetch_live_bars(args.symbol, args.timeframe, args.count))
    latest = enriched.tail(5)[
        [
            "close",
            "sma_14",
            "ema_14",
            "wma_14",
            "macd",
            "macd_signal",
            "macd_hist",
            "plus_di",
            "minus_di",
            "adx",
        ]
    ]
    logger.info(f"Computed trend indicators. Latest values:\n{latest}")
    print(latest.round(6).to_string())


if __name__ == "__main__":
    main()
