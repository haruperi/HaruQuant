"""Profile helpers for Market Structure symbol/timeframe classes."""

from __future__ import annotations

from typing import Any, Dict


MAJOR_FX = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "EURGBP"}
INDEX_MARKERS = ("US30", "NAS", "SPX", "GER", "UK100", "JP225", "AUS200", "FRA40", "USTEC", "DE40")
METAL_MARKERS = ("XAU", "XAG", "XPT", "XPD")
CRYPTO_MARKERS = ("BTC", "ETH", "SOL", "XRP", "ADA", "DOGE")

PROFILE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "major_fx::intraday_fast": {
        "bias_verdict_min_gap": 12.0,
        "trend_confidence_min": 32.0,
        "reversion_confidence_min": 32.0,
    },
    "major_fx::intraday_swing": {
        "bias_verdict_min_gap": 14.0,
        "trend_confidence_min": 34.0,
        "reversion_confidence_min": 34.0,
    },
    "jpy_fx::intraday_fast": {
        "bias_verdict_min_gap": 14.0,
        "trend_confidence_min": 36.0,
        "reversion_confidence_min": 34.0,
    },
    "metals::intraday_fast": {
        "bias_verdict_min_gap": 18.0,
        "trend_confidence_min": 38.0,
        "reversion_confidence_min": 36.0,
    },
    "indices::intraday_fast": {
        "bias_verdict_min_gap": 18.0,
        "trend_confidence_min": 38.0,
        "reversion_confidence_min": 36.0,
    },
}


def timeframe_bucket(timeframe: str) -> str:
    tf = timeframe.upper()
    if tf in {"M1", "M5", "M15"}:
        return "intraday_fast"
    if tf in {"M30", "H1", "H4"}:
        return "intraday_swing"
    if tf in {"D1", "W1", "MN1"}:
        return "higher_timeframe"
    return "other"


def symbol_class(symbol: str) -> str:
    sym = symbol.upper()
    if sym in MAJOR_FX:
        return "major_fx"
    if "JPY" in sym and len(sym) >= 6:
        return "jpy_fx"
    if any(marker in sym for marker in METAL_MARKERS):
        return "metals"
    if any(marker in sym for marker in CRYPTO_MARKERS):
        return "crypto"
    if any(marker in sym for marker in INDEX_MARKERS):
        return "indices"
    if len(sym) == 6 and sym.isalpha():
        return "fx_cross"
    return "other"


def resolve_market_structure_profile(symbol: str, timeframe: str) -> Dict[str, str]:
    symbol_group = symbol_class(symbol)
    timeframe_group = timeframe_bucket(timeframe)
    return {
        "symbol_class": symbol_group,
        "timeframe_bucket": timeframe_group,
        "profile_key": f"{symbol_group}::{timeframe_group}",
    }


def resolve_market_structure_profile_overrides(symbol: str, timeframe: str) -> Dict[str, Any]:
    profile = resolve_market_structure_profile(symbol, timeframe)
    return dict(PROFILE_OVERRIDES.get(profile["profile_key"], {}))
