"""Position sizing resolution for simulation runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import pandas as pd

from services.risk import PositionSizer
from services.simulation.config import PositionSizeConfig, SimulationConfig
from services.simulation.data_preparation import PreparedSimulationData


class SimulationPositionSizingError(RuntimeError):
    """Raised when simulation position sizing cannot be resolved."""


@dataclass(frozen=True)
class SimulationSymbolInfo:
    """Minimal symbol-info adapter for risk_engine.PositionSizer."""

    contract_size: float = 100000.0
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01

    def get_contract_size(self) -> float:
        return float(self.contract_size)

    def get_lots_min(self) -> float:
        return float(self.min_lot)

    def get_lots_max(self) -> float:
        return float(self.max_lot)

    def get_lots_step(self) -> float:
        return float(self.lot_step)


def resolve_position_size(
    config: SimulationConfig,
    prepared: PreparedSimulationData,
) -> float:
    """Resolve configured money management into one primitive lot size."""
    position_config = config.execution.position_size
    method = _position_sizer_method(position_config.type)
    sizer_config = _position_sizer_config(config, position_config)
    sizing_input = _position_sizing_input(config, prepared)
    sizer = PositionSizer(method=method, config=sizer_config, mt5_client=None)
    size = sizer.calculate_size(
        account_balance=float(config.account.initial_balance),
        entry_price=sizing_input["entry_price"],
        stop_loss=sizing_input["stop_loss"],
        symbol_info=SimulationSymbolInfo(
            contract_size=float(config.execution.contract_size),
        ),
        context=sizing_input["context"],
        symbol=sizing_input["symbol"],
        signal_type=sizing_input["signal_type"],
    )
    size = float(size)
    if size <= 0.0:
        raise SimulationPositionSizingError(
            f"position sizing resolved non-positive lot size: {size}"
        )
    return size


def _position_sizer_method(position_type: str) -> str:
    mapping = {
        "fixed_lot": "fixed_lot",
        "fixed_percent": "fixed_risk",
        "milestone": "milestone",
        "kelly_criterion": "kelly",
        "volatility_adjusted_atr": "volatility",
        "fixed_fractional": "fixed_fractional",
    }
    return mapping[position_type]


def _position_sizer_config(
    config: SimulationConfig,
    position_config: PositionSizeConfig,
) -> dict[str, Any]:
    params = dict(position_config.params)
    if position_config.type == "fixed_lot":
        return {"lot_size": float(position_config.lot_size)}
    if position_config.type == "milestone":
        params.setdefault("initial_balance", float(config.account.initial_balance))
        params.setdefault("base_lot_size", float(position_config.lot_size))
    if position_config.type == "fixed_fractional":
        if "fraction" not in params and "fractional_factor" in params:
            params["fraction"] = params["fractional_factor"]
    if position_config.type == "fixed_percent":
        params.setdefault("use_dynamic_stop_loss", False)
    return params


def _position_sizing_input(
    config: SimulationConfig,
    prepared: PreparedSimulationData,
) -> dict[str, Any]:
    ticks = prepared.ticks
    if ticks is None or ticks.empty:
        raise SimulationPositionSizingError("position sizing requires prepared ticks")

    row = _first_trade_context_row(ticks)
    bid = _safe_float(row.get("bid"), 0.0)
    ask = _safe_float(row.get("ask"), bid)
    entry_signal = _safe_float(row.get("entry_signal"), 0.0)
    signal_type = "sell" if entry_signal < 0 else "buy"
    entry_price = ask if signal_type == "buy" else bid
    if entry_price <= 0.0:
        entry_price = max(bid, ask, 1.0)

    stop_loss = _safe_float(row.get("sl"), 0.0)
    context = dict(config.execution.position_size.params)
    if "atr" not in context:
        atr = _estimate_atr_from_ticks(ticks)
        if atr is not None:
            context["atr"] = atr

    return {
        "entry_price": float(entry_price),
        "stop_loss": None if stop_loss <= 0.0 else float(stop_loss),
        "context": context,
        "symbol": str(row.get("symbol") or config.data.symbols[0]),
        "signal_type": signal_type,
    }


def _first_trade_context_row(ticks: pd.DataFrame) -> Mapping[str, Any]:
    if "entry_signal" in ticks.columns:
        entries = ticks[ticks["entry_signal"].fillna(0.0).astype(float) != 0.0]
        if not entries.empty:
            return entries.iloc[0]
    return ticks.iloc[0]


def _estimate_atr_from_ticks(ticks: pd.DataFrame) -> Optional[float]:
    if not {"bid", "ask"}.issubset(set(ticks.columns)):
        return None
    mid = (ticks["bid"].astype(float) + ticks["ask"].astype(float)) / 2.0
    if mid.empty:
        return None
    high = float(mid.max())
    low = float(mid.min())
    atr = high - low
    return atr if atr > 0.0 else None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)
