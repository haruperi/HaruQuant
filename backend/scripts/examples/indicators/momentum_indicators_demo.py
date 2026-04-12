"""Momentum indicator example using live MT5 data and backend indicator services.

Run from the repository root:
    python backend/scripts/examples/indicators/momentum_indicators_demo.py --symbol EURUSD --timeframe H1 --count 120
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
from backend.services.indicators import rsi  # noqa: E402
from _mt5_data import fetch_live_bars, parse_common_args  # noqa: E402


def _stochastic(data: pd.DataFrame, *, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    low_min = data["low"].rolling(k_period, min_periods=k_period).min()
    high_max = data["high"].rolling(k_period, min_periods=k_period).max()
    percent_k = 100 * (data["close"] - low_min) / (high_max - low_min)
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"stoch_k": percent_k, "stoch_d": percent_d}, index=data.index)


def _cci(data: pd.DataFrame, *, period: int = 20) -> pd.Series:
    typical_price = (data["high"] + data["low"] + data["close"]) / 3
    mean = typical_price.rolling(period, min_periods=period).mean()
    mean_deviation = (typical_price - mean).abs().rolling(period, min_periods=period).mean()
    cci = (typical_price - mean) / (0.015 * mean_deviation)
    cci.name = f"cci_{period}"
    return cci


def _roc(data: pd.DataFrame, *, period: int = 12) -> pd.Series:
    roc = data["close"].pct_change(periods=period) * 100
    roc.name = f"roc_{period}"
    return roc


def compute_momentum_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI plus local stochastic, CCI, and ROC demo columns."""
    result = rsi(data, period=14)
    return result.join(_stochastic(result)).join(_cci(result)).join(_roc(result))


def main() -> None:
    args = parse_common_args("Compute momentum indicators from live MT5 bars.")
    logger.info(
        f"Starting momentum indicator demo for {args.symbol} {args.timeframe} with {args.count} live MT5 bars"
    )
    enriched = compute_momentum_indicators(fetch_live_bars(args.symbol, args.timeframe, args.count))
    latest = enriched.tail(5)[["close", "rsi_14", "stoch_k", "stoch_d", "cci_20", "roc_12"]]
    logger.info(f"Computed momentum indicators. Latest values:\n{latest}")
    print(latest.round(6).to_string())


if __name__ == "__main__":
    main()
