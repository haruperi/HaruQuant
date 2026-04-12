"""Pydantic models for simulator API routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SimulationStartRequest(BaseModel):
    """Request to start a simulation session."""

    session_name: Optional[str] = None
    symbol: str
    timeframe: str = "M1"
    range_by: Optional[str] = "bars"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    number_of_bars: Optional[int] = None
    warmup_by: Optional[str] = "date"
    warmup_start_date: Optional[str] = None
    warmup_bars: Optional[int] = None
    initial_balance: float = 10000.0
    speed_multiplier: float = 1.0
    commission: float = 7.0
    leverage: int = 400
    slippage_type: str = "fixed"
    slippage: float = 0.0
    slippage_min: float = 0.0
    slippage_max: float = 10.0
    spread_type: str = "use-broker"
    spread: float = 20.0
    spread_min: float = 10.0
    spread_max: float = 50.0
    data_source: Optional[str] = "mt5"
    data_resolution: str = "trading_timeframe"
    position_sizing_method: Optional[str] = "fixed_lot"
    lot_size: float = 0.1
    risk_percent: float = 1.0
    base_lot_size: float = 0.1
    milestone_amount: float = 3000.0
    lot_increment: float = 0.2
    kelly_fraction_limit: float = 0.25
    fraction: float = 2.0
    fractional_factor: float = 2.0
    use_dynamic_stop_loss: bool = False
    atr_multiplier: float = 2.0
    win_rate: float = 0.55
    avg_win: float = 150.0
    avg_loss: float = 100.0
    risk_confidence_level: float = 0.95
    risk_horizon_unit: str = "days"
    risk_horizon_value: int = 1
    risk_vol_lookback: int = 20
    risk_corr_lookback: int = 60
    risk_var_cap_frac: float = 0.10
    risk_es_cap_frac: float = 0.15
    risk_delta_var_cap_frac: float = 0.02
    risk_delta_es_cap_frac: float = 0.03
    risk_max_margin_used_frac: float = 0.50
    risk_max_currency_exposure_frac: float = 0.20
    risk_max_single_rc_frac: float = 0.10
    risk_warning_utilization_frac: float = 0.90
    risk_limits_enforced: bool = True
    mode: str = Field(default="manual", description="manual | strategy | replay")
    strategy_id: Optional[int] = None
    strategy_version_id: Optional[int] = None
    strategy_params: Optional[Dict[str, Any]] = None
    replay_source: Optional[str] = None
    replay_backtest_id: Optional[int] = None
    replay_file_name: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    sma_period: Optional[int] = 14
    ema_period: Optional[int] = 14
    rsi_period: Optional[int] = 14
    indicators_enabled: bool = False
    indicator_sma_enabled: bool = False
    indicator_ema_enabled: bool = False
    indicator_rsi_enabled: bool = False


class SimulationUpdateRequest(BaseModel):
    """Request to update a simulation session."""

    speed_multiplier: Optional[float] = None
    paused: Optional[bool] = None
    indicators_enabled: Optional[bool] = None
    indicator_sma_enabled: Optional[bool] = None
    indicator_ema_enabled: Optional[bool] = None
    indicator_rsi_enabled: Optional[bool] = None


class ManualTradeRequest(BaseModel):
    """Request to execute a manual trade."""

    symbol: Optional[str] = None
    side: str = Field(..., description="buy | sell")
    volume: float = 0.1
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None
    manual_review_accepted: bool = False


class PendingOrderRequest(BaseModel):
    """Request to place a pending order."""

    symbol: Optional[str] = None
    type: str = Field(
        ...,
        description="buy_limit | sell_limit | buy_stop | sell_stop | buy_stop_limit | sell_stop_limit",
    )
    volume: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None
    expiry_date: Optional[str] = None
    expiration_mode: Optional[str] = "gtc"


class PositionModifyRequest(BaseModel):
    """Request to modify a position."""

    sl: Optional[float] = None
    tp: Optional[float] = None


class OrderModifyRequest(BaseModel):
    """Request to modify a pending order."""

    volume: Optional[float] = None
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class SeekRequest(BaseModel):
    """Request to seek to a bar index."""

    bar_index: Optional[int] = None
    target_time: Optional[str] = None


class AdvanceRequest(BaseModel):
    """Request to advance by N synchronized simulator frames."""

    count: int = 1


class WhatIfActionRequest(BaseModel):
    """One hypothetical non-mutating portfolio action."""

    action_type: str
    symbol: str
    delta_lots: Optional[float] = None
    target_lots: Optional[float] = None
    rationale: Optional[str] = None


class WhatIfRequest(BaseModel):
    """Request to evaluate a what-if scenario against the current simulator state."""

    actions: List[WhatIfActionRequest] = Field(default_factory=list)
    leverage_override: Optional[int] = None
