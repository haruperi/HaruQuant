"""Typed configuration contract for simulation backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Optional, Sequence


SUPPORTED_ENGINE_TYPES = {"vectorized", "event_driven"}
SUPPORTED_DATA_SOURCES = {"metatrader", "dukascopy"}
SUPPORTED_TICK_MODELS = {"timeframe_ticks", "m1_ticks", "real_ticks", "synthetic_ticks"}
SUPPORTED_SPREAD_MODELS = {"native_spread", "fixed_spread", "variable_spread"}
SUPPORTED_SLIPPAGE_MODELS = {"none", "fixed", "dynamic"}
SUPPORTED_POSITION_SIZE_TYPES = {"fixed_lot", "fixed_percent", "milestone", "kelly_criterion", "volatility_adjusted_atr", "fixed_fractional"}


class SimulationConfigError(ValueError):
    """Raised when a simulation config is missing or invalid."""


@dataclass(frozen=True)
class AccountConfig:
    initial_balance: float
    commission: float = 0.0
    leverage: int = 400
    currency: str = "USD"

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AccountConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("account must be an object")
        initial_balance = _required_float(raw, "account.initial_balance")
        if initial_balance <= 0.0:
            raise SimulationConfigError("account.initial_balance must be > 0")
        commission = _optional_float(raw, "commission", default=0.0)
        if commission < 0.0:
            raise SimulationConfigError("account.commission must be >= 0")
        leverage = int(_optional_float(raw, "leverage", default=400.0))
        if leverage <= 0:
            raise SimulationConfigError("account.leverage must be > 0")
        currency = str(raw.get("currency", "USD") or "USD").strip().upper()
        if not currency:
            raise SimulationConfigError("account.currency must be non-empty")
        return cls(
            initial_balance=initial_balance,
            commission=commission,
            leverage=leverage,
            currency=currency,
        )


@dataclass(frozen=True)
class DataConfig:
    source: str
    symbols: tuple[str, ...]
    timeframe: str
    start: datetime
    end: datetime
    warmup_start: datetime

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DataConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("data must be an object")
        source = _normalize_choice(
            _required_str(raw, "data.source"),
            SUPPORTED_DATA_SOURCES,
            "data.source",
        )
        symbols = _normalize_symbols(raw.get("symbols"))
        timeframe = _required_str(raw, "data.timeframe").strip().upper()
        if not timeframe:
            raise SimulationConfigError("data.timeframe must be non-empty")
        start = _required_datetime(raw, "data.start")
        end = _required_datetime(raw, "data.end")
        warmup_start = _required_datetime(raw, "data.warmup_start")
        if warmup_start > start:
            raise SimulationConfigError("data.warmup_start must be <= data.start")
        if start > end:
            raise SimulationConfigError("data.start must be <= data.end")
        return cls(
            source=source,
            symbols=symbols,
            timeframe=timeframe,
            start=start,
            end=end,
            warmup_start=warmup_start,
        )


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    params: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "StrategyConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("strategy must be an object")
        name = _required_str(raw, "strategy.name").strip()
        if not name:
            raise SimulationConfigError("strategy.name must be non-empty")
        params = raw.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, Mapping):
            raise SimulationConfigError("strategy.params must be an object")
        return cls(name=name, params=dict(params))


@dataclass(frozen=True)
class PositionSizeConfig:
    type: str
    lot_size: float
    params: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PositionSizeConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("execution.position_size must be an object")
        size_type = _normalize_choice(
            _required_str(raw, "execution.position_size.type"),
            SUPPORTED_POSITION_SIZE_TYPES,
            "execution.position_size.type",
        )
        if size_type != "fixed_lot":
            raise SimulationConfigError(
                f"unsupported execution.position_size.type: {size_type}"
            )
        lot_size = _required_float(raw, "execution.position_size.lot_size")
        if lot_size <= 0.0:
            raise SimulationConfigError("execution.position_size.lot_size must be > 0")
        return cls(type=size_type, lot_size=lot_size, params=dict(raw))


@dataclass(frozen=True)
class ExecutionConfig:
    tick_model: str
    spread_model: str
    contract_size: float
    position_size: PositionSizeConfig
    slippage_model: str = "none"
    slippage_points: float = 0.0
    spread_points: Optional[float] = None
    spread_min: Optional[float] = None
    spread_max: Optional[float] = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExecutionConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("execution must be an object")
        tick_model = _normalize_choice(
            str(raw.get("tick_model", "timeframe_ticks")),
            SUPPORTED_TICK_MODELS,
            "execution.tick_model",
        )
        spread_model = _normalize_choice(
            str(raw.get("spread_model", "native_spread")),
            SUPPORTED_SPREAD_MODELS,
            "execution.spread_model",
        )
        slippage_model = _normalize_choice(
            str(raw.get("slippage_model", "none")),
            SUPPORTED_SLIPPAGE_MODELS,
            "execution.slippage_model",
        )
        contract_size = _optional_float(raw, "contract_size", default=100000.0)
        if contract_size <= 0.0:
            raise SimulationConfigError("execution.contract_size must be > 0")
        if "position_size" not in raw:
            raise SimulationConfigError("execution.position_size is required")
        position_size = PositionSizeConfig.from_dict(raw["position_size"])

        slippage_points = _optional_float(raw, "slippage_points", default=0.0)
        if slippage_points < 0.0:
            raise SimulationConfigError("execution.slippage_points must be >= 0")
        if slippage_model == "fixed" and "slippage_points" not in raw:
            raise SimulationConfigError(
                "execution.slippage_points is required for fixed slippage"
            )

        spread_points = _optional_float_or_none(raw, "spread_points")
        spread_min = _optional_float_or_none(raw, "spread_min")
        spread_max = _optional_float_or_none(raw, "spread_max")
        if spread_model == "fixed_spread":
            if spread_points is None:
                raise SimulationConfigError(
                    "execution.spread_points is required for fixed_spread"
                )
            if spread_points < 0.0:
                raise SimulationConfigError("execution.spread_points must be >= 0")
        if spread_model == "variable_spread":
            if spread_min is None or spread_max is None:
                raise SimulationConfigError(
                    "execution.spread_min and execution.spread_max are required "
                    "for variable_spread"
                )
            if spread_min < 0.0 or spread_max < 0.0:
                raise SimulationConfigError(
                    "execution.spread_min and execution.spread_max must be >= 0"
                )
            if spread_min > spread_max:
                raise SimulationConfigError(
                    "execution.spread_min must be <= execution.spread_max"
                )

        return cls(
            tick_model=tick_model,
            spread_model=spread_model,
            contract_size=contract_size,
            position_size=position_size,
            slippage_model=slippage_model,
            slippage_points=slippage_points,
            spread_points=spread_points,
            spread_min=spread_min,
            spread_max=spread_max,
        )


@dataclass(frozen=True)
class ReportingConfig:
    print_summary: bool = False
    save_to_db: bool = False
    alias: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Optional[Mapping[str, Any]]) -> "ReportingConfig":
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("reporting must be an object")
        alias = raw.get("alias")
        description = raw.get("description")
        return cls(
            print_summary=bool(raw.get("print_summary", False)),
            save_to_db=bool(raw.get("save_to_db", False)),
            alias=None if alias is None else str(alias),
            description=None if description is None else str(description),
        )


@dataclass(frozen=True)
class SimulationConfig:
    engine_type: str
    account: AccountConfig
    data: DataConfig
    strategy: StrategyConfig
    execution: ExecutionConfig
    reporting: ReportingConfig = field(default_factory=ReportingConfig)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SimulationConfig":
        if not isinstance(raw, Mapping):
            raise SimulationConfigError("simulation config must be an object")
        engine_type = _normalize_choice(
            str(raw.get("engine_type", "vectorized")),
            SUPPORTED_ENGINE_TYPES,
            "engine_type",
        )
        account = AccountConfig.from_dict(_required_mapping(raw, "account"))
        data = DataConfig.from_dict(_required_mapping(raw, "data"))
        strategy = StrategyConfig.from_dict(_required_mapping(raw, "strategy"))
        execution = ExecutionConfig.from_dict(_required_mapping(raw, "execution"))
        reporting = ReportingConfig.from_dict(raw.get("reporting"))
        return cls(
            engine_type=engine_type,
            account=account,
            data=data,
            strategy=strategy,
            execution=execution,
            reporting=reporting,
        )


def _required_mapping(raw: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    if key not in raw:
        raise SimulationConfigError(f"{key} is required")
    value = raw[key]
    if not isinstance(value, Mapping):
        raise SimulationConfigError(f"{key} must be an object")
    return value


def _required_str(raw: Mapping[str, Any], dotted_key: str) -> str:
    key = dotted_key.rsplit(".", 1)[-1]
    if key not in raw:
        raise SimulationConfigError(f"{dotted_key} is required")
    value = raw[key]
    if value is None:
        raise SimulationConfigError(f"{dotted_key} is required")
    return str(value)


def _required_float(raw: Mapping[str, Any], dotted_key: str) -> float:
    key = dotted_key.rsplit(".", 1)[-1]
    if key not in raw:
        raise SimulationConfigError(f"{dotted_key} is required")
    try:
        return float(raw[key])
    except (TypeError, ValueError) as exc:
        raise SimulationConfigError(f"{dotted_key} must be numeric") from exc


def _optional_float(raw: Mapping[str, Any], key: str, default: float) -> float:
    if key not in raw or raw[key] is None:
        return float(default)
    try:
        return float(raw[key])
    except (TypeError, ValueError) as exc:
        raise SimulationConfigError(f"{key} must be numeric") from exc


def _optional_float_or_none(raw: Mapping[str, Any], key: str) -> Optional[float]:
    if key not in raw or raw[key] is None:
        return None
    try:
        return float(raw[key])
    except (TypeError, ValueError) as exc:
        raise SimulationConfigError(f"{key} must be numeric") from exc


def _required_datetime(raw: Mapping[str, Any], dotted_key: str) -> datetime:
    key = dotted_key.rsplit(".", 1)[-1]
    if key not in raw:
        raise SimulationConfigError(f"{dotted_key} is required")
    return _parse_datetime(raw[key], dotted_key)


def _parse_datetime(value: Any, dotted_key: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise SimulationConfigError(f"{dotted_key} must be a datetime")
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SimulationConfigError(
                f"{dotted_key} must be ISO datetime/date text"
            ) from exc
    raise SimulationConfigError(f"{dotted_key} must be a datetime")


def _normalize_symbols(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        symbols: Sequence[Any] = [value]
    elif isinstance(value, Sequence):
        symbols = value
    else:
        raise SimulationConfigError("data.symbols must be a non-empty list")
    normalized = tuple(str(symbol).strip() for symbol in symbols if str(symbol).strip())
    if not normalized:
        raise SimulationConfigError("data.symbols must be non-empty")
    if len(set(normalized)) != len(normalized):
        raise SimulationConfigError("data.symbols must not contain duplicates")
    return normalized


def _normalize_choice(value: str, supported: set[str], dotted_key: str) -> str:
    normalized = value.strip().lower()
    if normalized not in supported:
        supported_text = ", ".join(sorted(supported))
        raise SimulationConfigError(
            f"{dotted_key} must be one of [{supported_text}], got {value!r}"
        )
    return normalized
