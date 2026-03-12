"""Pydantic models for API requests and responses."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""

    username: str
    password: str


class UserResponse(BaseModel):
    """User data response."""

    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool


class AuthResponse(BaseModel):
    """Authentication response with token and user data."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str


class UserSettingsResponse(BaseModel):
    """User settings response."""

    user_id: int
    theme: str = "system"
    language: str = "en"
    timezone: str = "UTC"
    log_verbosity: str = "info"
    performance_mode: str = "balanced"
    broker_credentials: Optional[Union[Dict[str, Any], List[Any]]] = {}
    trading_preferences: Optional[Union[Dict[str, Any], List[Any]]] = {}
    notifications: Optional[Union[Dict[str, Any], List[Any]]] = {}
    alert_triggers: Optional[Union[Dict[str, Any], List[Any]]] = {}


class UpdateUserSettingsRequest(BaseModel):
    """Update user settings request."""

    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    log_verbosity: Optional[str] = None
    performance_mode: Optional[str] = None
    broker_credentials: Optional[Union[Dict[str, Any], List[Any], str]] = None
    trading_preferences: Optional[Union[Dict[str, Any], List[Any], str]] = None
    notifications: Optional[Union[Dict[str, Any], List[Any], str]] = None
    alert_triggers: Optional[Union[Dict[str, Any], List[Any], str]] = None


class BrokerStatusResponse(BaseModel):
    """Broker status response."""

    status: str
    broker_name: str
    equity: float
    balance: float
    margin_level: float
    free_margin: float


class DashboardEquityPoint(BaseModel):
    """Single dashboard equity point."""

    timestamp: str
    equity: float


class DashboardEquityCurveResponse(BaseModel):
    """Dashboard equity curve response."""

    points: List[DashboardEquityPoint]
    history_span_seconds: float = 0.0
    point_count: int = 0


class DashboardDailyPnlPoint(BaseModel):
    """Single daily PnL point for the dashboard."""

    day: str
    pnl: float


class DashboardActiveStrategyItem(BaseModel):
    """Active strategy row for the dashboard."""

    name: str
    market: str
    status: str
    timeframe: str
    session_name: str


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary response."""

    daily_pnl: List[DashboardDailyPnlPoint]
    weekly_pnl_total: float = 0.0
    weekly_best_day: float = 0.0
    weekly_worst_day: float = 0.0
    win_rate: float = 0.0
    closed_trade_count: int = 0
    winning_trade_count: int = 0
    active_strategy_count: int = 0
    active_strategies: List[DashboardActiveStrategyItem]


class MarketStatus(BaseModel):
    """Market status details."""

    name: str
    status: str
    message: str  # e.g. "Opening in 2h 15m" or "Closing in 30m"
    open: str
    close: str
    local_time: str


class MarketHoursResponse(BaseModel):
    """Response model for market hours."""

    markets: List[MarketStatus]


class SystemStatusResponse(BaseModel):
    """System status response."""

    backend: str
    database: str
    message: str


class ResourceUsageResponse(BaseModel):
    """Resource usage response."""

    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
