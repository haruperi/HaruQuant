"""Versioned schema registry and message contracts (IP-12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SchemaModel = Type[BaseModel]


class SchemaRegistryError(Exception):
    """Raised when schema registration/lookup/compatibility checks fail."""


@dataclass(frozen=True)
class SchemaRegistration:
    """One registry entry."""

    name: str
    version: str
    model: SchemaModel


def _normalize_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TickMessage(BaseModel):
    """Canonical tick event contract."""

    model_config = ConfigDict(extra="allow")

    provider: str = "mt5_ea"
    schema_version: str = "1.0"
    symbol: str = Field(min_length=1)
    timestamp: datetime
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    last: Optional[float] = Field(default=None, gt=0)
    volume: float = Field(ge=0, default=0.0)
    sequence: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, value: Any) -> datetime:
        return _normalize_dt(value)

    @field_validator("ask")
    @classmethod
    def _ask_ge_bid(cls, ask: float, info: Any) -> float:
        bid = info.data.get("bid")
        if bid is not None and ask < bid:
            raise ValueError("ask must be greater than or equal to bid")
        return ask


class BarMessage(BaseModel):
    """Canonical bar event contract."""

    model_config = ConfigDict(extra="allow")

    provider: str = "mt5_ea"
    schema_version: str = "1.0"
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0, default=0.0)
    sequence: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, value: Any) -> datetime:
        return _normalize_dt(value)

    @field_validator("high")
    @classmethod
    def _high_ge_low(cls, high: float, info: Any) -> float:
        low = info.data.get("low")
        if low is not None and high < low:
            raise ValueError("high must be greater than or equal to low")
        return high

    @field_validator("close")
    @classmethod
    def _close_range(cls, close: float, info: Any) -> float:
        high = info.data.get("high")
        low = info.data.get("low")
        if high is not None and low is not None and (close > high or close < low):
            raise ValueError("close must be within [low, high]")
        return close


class OrderMessage(BaseModel):
    """Canonical order API/storage contract."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    order_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: str = Field(pattern="^(BUY|SELL)$")
    order_type: str = Field(pattern="^(MARKET|LIMIT|STOP)$")
    volume: float = Field(gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    status: str = Field(default="NEW", min_length=1)
    submitted_at: datetime

    @field_validator("submitted_at", mode="before")
    @classmethod
    def _submitted_at(cls, value: Any) -> datetime:
        return _normalize_dt(value)


class FillMessage(BaseModel):
    """Canonical fill API/storage contract."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    fill_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = 0.0
    slippage: float = 0.0
    filled_at: datetime

    @field_validator("filled_at", mode="before")
    @classmethod
    def _filled_at(cls, value: Any) -> datetime:
        return _normalize_dt(value)


class PositionMessage(BaseModel):
    """Canonical position storage/API contract."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    position_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: str = Field(pattern="^(BUY|SELL)$")
    volume: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    current_price: Optional[float] = Field(default=None, gt=0)
    unrealized_pnl: float = 0.0
    status: str = Field(default="OPEN", min_length=1)
    opened_at: datetime
    closed_at: Optional[datetime] = None

    @field_validator("opened_at", "closed_at", mode="before")
    @classmethod
    def _time_fields(cls, value: Any) -> Any:
        if value is None:
            return None
        return _normalize_dt(value)


class RunManifestSchema(BaseModel):
    """Run manifest contract for reproducibility metadata."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    run_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    started_at: datetime
    ended_at: Optional[datetime] = None
    environment: str = Field(min_length=1)
    symbols: list[str] = Field(default_factory=list)
    timeframe: str = Field(min_length=1)
    config_hash: str = Field(min_length=1)
    code_version: Optional[str] = None
    seed: Optional[int] = None

    @field_validator("started_at", "ended_at", mode="before")
    @classmethod
    def _manifest_times(cls, value: Any) -> Any:
        if value is None:
            return None
        return _normalize_dt(value)


class RunReportSchema(BaseModel):
    """Run report contract for persisted outcomes."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    run_id: str = Field(min_length=1)
    generated_at: datetime
    status: str = Field(min_length=1)
    total_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=1)
    net_profit: float
    max_drawdown: float = Field(ge=0)
    metrics: Dict[str, Union[int, float, str]] = Field(default_factory=dict)

    @field_validator("generated_at", mode="before")
    @classmethod
    def _generated_at(cls, value: Any) -> datetime:
        return _normalize_dt(value)


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin in (Union,):
        args = get_args(annotation)
        return type(None) in args
    return False


def _annotation_key(annotation: Any) -> str:
    return str(annotation)


def is_backward_compatible(old_model: SchemaModel, new_model: SchemaModel) -> Tuple[bool, str]:
    """
    Backward compatibility check using conservative rules:
    - all old fields must exist in new
    - field requiredness cannot become stricter (optional -> required is breaking)
    - field annotation must stay equal (type changes are breaking)
    """
    old_fields = old_model.model_fields
    new_fields = new_model.model_fields

    for field_name, old_field in old_fields.items():
        if field_name not in new_fields:
            return False, f"missing field in new schema: {field_name}"
        new_field = new_fields[field_name]

        old_required = old_field.is_required()
        new_required = new_field.is_required()
        if (not old_required) and new_required:
            return False, f"field became required: {field_name}"

        old_ann = _annotation_key(old_field.annotation)
        new_ann = _annotation_key(new_field.annotation)
        if old_ann != new_ann:
            return False, f"field type changed: {field_name} ({old_ann} -> {new_ann})"

        # Optional/None acceptance guard for annotated unions.
        old_opt = _is_optional(old_field.annotation)
        new_opt = _is_optional(new_field.annotation)
        if old_opt and not new_opt:
            return False, f"optional field became non-optional: {field_name}"

    return True, "compatible"


class SchemaRegistry:
    """In-memory versioned schema registry with compatibility checks."""

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], SchemaRegistration] = {}

    def register(
        self,
        *,
        name: str,
        version: str,
        model: SchemaModel,
        enforce_backward_compat_with: Optional[str] = None,
    ) -> None:
        key = (name, version)
        if key in self._entries:
            raise SchemaRegistryError(f"schema already registered: {name}:{version}")

        if enforce_backward_compat_with is not None:
            old = self.get(name=name, version=enforce_backward_compat_with)
            ok, message = is_backward_compatible(old.model, model)
            if not ok:
                raise SchemaRegistryError(
                    f"backward compatibility failed for {name}:{version}: {message}"
                )

        self._entries[key] = SchemaRegistration(name=name, version=version, model=model)

    def get(self, *, name: str, version: str) -> SchemaRegistration:
        key = (name, version)
        entry = self._entries.get(key)
        if entry is None:
            raise SchemaRegistryError(f"schema not found: {name}:{version}")
        return entry

    def list_versions(self, *, name: str) -> list[str]:
        versions = [v for (n, v) in self._entries.keys() if n == name]
        return sorted(versions)

    def validate(
        self,
        *,
        name: str,
        version: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, str]:
        try:
            schema = self.get(name=name, version=version)
            schema.model.model_validate(payload)
            return True, "ok"
        except (SchemaRegistryError, ValidationError) as exc:
            return False, str(exc)

    def entries(self) -> Iterable[SchemaRegistration]:
        return self._entries.values()


def create_default_schema_registry() -> SchemaRegistry:
    """Create registry with built-in canonical contracts."""
    reg = SchemaRegistry()
    reg.register(name="event.tick", version="1.0", model=TickMessage)
    reg.register(name="event.bar", version="1.0", model=BarMessage)
    reg.register(name="api.order", version="1.0", model=OrderMessage)
    reg.register(name="api.fill", version="1.0", model=FillMessage)
    reg.register(name="storage.position", version="1.0", model=PositionMessage)
    reg.register(name="storage.run_manifest", version="1.0", model=RunManifestSchema)
    reg.register(name="storage.run_report", version="1.0", model=RunReportSchema)
    return reg
