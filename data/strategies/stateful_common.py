"""Shared helpers for stateful example strategies."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from services.strategy.stateful import PositionSnapshot, StrategyContext

SIGNAL_COLUMN_DEFAULTS: dict[str, Any] = {
    "entry_signal": 0,
    "exit_signal": 0,
    "pending_signal": 0,
    "cancel_pending_signal": 0,
    "pending_signal_2": 0,
    "cancel_pending_signal_2": 0,
    "price": float("nan"),
    "price_2": float("nan"),
    "stop_loss": float("nan"),
    "take_profit": float("nan"),
    "signal_reason": "",
    "setup_id": "",
    "group_id": "",
}

ACTIVATOR_COLUMN_DEFAULTS: dict[str, bool] = {
    "buy_setup_active": False,
    "sell_setup_active": False,
    "buy_add_active": False,
    "sell_add_active": False,
    "buy_exit_active": False,
    "sell_exit_active": False,
    "buy_pyramid_active": False,
    "sell_pyramid_active": False,
    "buy_martingale_active": False,
    "sell_martingale_active": False,
    "buy_decompose_active": False,
    "sell_decompose_active": False,
    "buy_trail_active": False,
    "sell_trail_active": False,
}


def ensure_signal_columns(
    data: pd.DataFrame,
    *,
    include_activators: bool = False,
    include_compat_columns: bool = True,
) -> pd.DataFrame:
    """Return bars with the HaruQuant v1.0 strategy signal schema."""
    out = data.copy()
    defaults: dict[str, Any] = dict(SIGNAL_COLUMN_DEFAULTS)
    if include_activators:
        defaults.update(ACTIVATOR_COLUMN_DEFAULTS)
    if include_compat_columns:
        defaults.update({"sl": 0.0, "tp": 0.0})

    for column, default in defaults.items():
        if column not in out.columns:
            out[column] = default
    return out


def ensure_no_signal_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Return bars with neutral signal columns for tick generation."""
    out = ensure_signal_columns(data, include_activators=True)
    for column in (
        "entry_signal",
        "exit_signal",
        "pending_signal",
        "cancel_pending_signal",
        "pending_signal_2",
        "cancel_pending_signal_2",
    ):
        out[column] = 0
    for column in ("price", "price_2", "stop_loss", "take_profit"):
        out[column] = float("nan")
    for column in ("signal_reason", "setup_id", "group_id"):
        out[column] = ""
    for column in ACTIVATOR_COLUMN_DEFAULTS:
        out[column] = False
    out["sl"] = 0.0
    out["tp"] = 0.0
    return out


def is_bar_close(context: StrategyContext) -> bool:
    phase = ""
    if context.current_tick:
        phase = str(context.current_tick.get("is_bar_close", "") or "")
    return "close" in {part.strip().lower() for part in phase.split("|")}


def current_mid_price(context: StrategyContext) -> float:
    tick = context.current_tick or {}
    bid = float(tick.get("bid", 0.0) or 0.0)
    ask = float(tick.get("ask", bid) or bid)
    if bid <= 0.0:
        return ask
    if ask <= 0.0:
        return bid
    return (bid + ask) / 2.0


def historical_mid_prices(context: StrategyContext) -> pd.Series:
    data = context.market_data
    tick_index = int(context.metadata.get("tick_index", 0) if context.metadata else 0)
    if data is None or data.empty:
        return pd.Series(dtype="float64")
    window = data.iloc[: tick_index + 1]
    if "bid" not in window.columns:
        return pd.Series(dtype="float64")
    bid = pd.to_numeric(window["bid"], errors="coerce")
    ask = (
        pd.to_numeric(window["ask"], errors="coerce")
        if "ask" in window.columns
        else bid
    )
    mid = (bid + ask) / 2.0
    return mid.dropna()


def rolling_rsi(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    last_loss = float(avg_loss.iloc[-1] or 0.0)
    if last_loss <= 0.0:
        return 100.0
    rs = float(avg_gain.iloc[-1] or 0.0) / last_loss
    return float(100 - (100 / (1 + rs)))


def rolling_sma(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period:
        return None
    value = prices.rolling(window=period, min_periods=period).mean().iloc[-1]
    return None if pd.isna(value) else float(value)


def positions_for_side(
    context: StrategyContext,
    side: str,
) -> list[PositionSnapshot]:
    target = str(side).upper()
    return [
        position
        for position in context.positions_for_symbol()
        if str(position.side).upper() == target
    ]


def basket_pnl(positions: Iterable[PositionSnapshot]) -> float:
    return float(sum(float(position.profit_loss or 0.0) for position in positions))


def weighted_average_price(positions: Iterable[PositionSnapshot]) -> float | None:
    rows = list(positions)
    total_volume = sum(float(position.volume or 0.0) for position in rows)
    if total_volume <= 0.0:
        return None
    weighted = sum(
        float(position.open_price or 0.0) * float(position.volume or 0.0)
        for position in rows
    )
    return float(weighted / total_volume)


def oldest_position(positions: Iterable[PositionSnapshot]) -> PositionSnapshot | None:
    rows = list(positions)
    if not rows:
        return None
    return sorted(rows, key=lambda position: str(position.opened_at or ""))[0]
