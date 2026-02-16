"""Typed configuration management for live trading.

Supports:
- TOML or JSON config files.
- ${ENV_VAR} substitution in file content.
- Environment overlay using `HQT_` prefix and `__` path separators.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


class ConfigError(Exception):
    """Configuration error."""


@dataclass
class MT5Config:
    login: int
    password: str
    server: str
    path: str = ""


@dataclass
class StrategyConfig:
    symbol: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradingConfig:
    timeframe: str
    volume: float
    magic_number: int
    initial_bars: int
    deviation: int = 10


@dataclass
class SafetyConfig:
    min_balance: float
    min_margin_level: float
    max_positions: int
    max_daily_trades: int


@dataclass
class NotificationConfig:
    enable_email: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    recipients: List[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    dir: str
    level: str = "INFO"


@dataclass
class StateConfig:
    file: str


@dataclass
class LiveConfigModel:
    mt5: MT5Config
    strategy: StrategyConfig
    trading: TradingConfig
    safety: SafetyConfig
    notifications: NotificationConfig
    logging: LoggingConfig
    state: StateConfig


def _substitute_env_vars(content: str) -> str:
    """Substitute environment variables in `${VAR_NAME}` format."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ConfigError(f"Environment variable not found: {var_name}")
        return value

    return re.sub(pattern, replacer, content)


def _parse_file(path: Path, content: str) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".toml":
            return dict(tomllib.loads(content))
        if suffix == ".json":
            return dict(json.loads(content))

        # Fallback by trying TOML first, then JSON.
        try:
            return dict(tomllib.loads(content))
        except Exception:
            return dict(json.loads(content))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file: {exc}") from exc
    except Exception as exc:
        kind = "TOML" if suffix == ".toml" else "config"
        raise ConfigError(f"Invalid {kind} in config file: {exc}") from exc


def _set_nested(data: Dict[str, Any], path: List[str], value: Any) -> None:
    cursor: Dict[str, Any] = data
    for key in path[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[path[-1]] = value


def _get_nested(data: Dict[str, Any], path: List[str]) -> Any:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _convert_overlay_value(raw: str, reference: Any) -> Any:
    if isinstance(reference, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(raw.strip())
    if isinstance(reference, float):
        return float(raw.strip())
    if isinstance(reference, list):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def _apply_env_overlay(data: Dict[str, Any], prefix: str = "HQT_") -> Dict[str, Any]:
    """Apply env overlay.

    Example:
        HQT_MT5__PASSWORD=secret
        HQT_TRADING__VOLUME=0.2
    """
    out = dict(data)
    for key, raw_val in os.environ.items():
        if not key.startswith(prefix):
            continue
        path_tokens = key[len(prefix) :].split("__")
        path = [token.strip().lower() for token in path_tokens if token.strip()]
        if not path:
            continue
        current = _get_nested(out, path)
        converted = _convert_overlay_value(raw_val, current)
        _set_nested(out, path, converted)
    return out


def load_config_mapping(config_path: str | Path) -> Dict[str, Any]:
    """Load raw config mapping from TOML/JSON with env substitution + overlay."""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        content = path.read_text(encoding="utf-8")
        content = _substitute_env_vars(content)
        loaded = _parse_file(path, content)
        return _apply_env_overlay(loaded)
    except ConfigError:
        raise
    except Exception as exc:
        raise ConfigError(f"Failed to load config: {exc}") from exc


def _require_section(data: Dict[str, Any], section: str) -> Dict[str, Any]:
    if section not in data:
        raise ConfigError(f"Missing required section: {section}")
    section_value = data[section]
    if not isinstance(section_value, dict):
        raise ConfigError(f"Invalid section type for {section}: expected object")
    return section_value


def _require_field(section_name: str, section_data: Dict[str, Any], field_name: str) -> Any:
    if field_name not in section_data:
        raise ConfigError(f"Missing required field: {section_name}.{field_name}")
    return section_data[field_name]


def _to_int(section_name: str, field_name: str, value: Any) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise ConfigError(f"Invalid value for {section_name}.{field_name}: {value!r}") from exc


def _to_float(section_name: str, field_name: str, value: Any) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise ConfigError(f"Invalid value for {section_name}.{field_name}: {value!r}") from exc


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_list_str(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def parse_live_config(data: Dict[str, Any]) -> LiveConfigModel:
    """Validate and parse mapping into typed live config model."""
    mt5_data = _require_section(data, "mt5")
    strategy_data = _require_section(data, "strategy")
    trading_data = _require_section(data, "trading")
    safety_data = _require_section(data, "safety")
    notifications_data = _require_section(data, "notifications")
    logging_data = _require_section(data, "logging")
    state_data = _require_section(data, "state")

    model = LiveConfigModel(
        mt5=MT5Config(
            login=_to_int("mt5", "login", _require_field("mt5", mt5_data, "login")),
            password=str(_require_field("mt5", mt5_data, "password")),
            server=str(_require_field("mt5", mt5_data, "server")),
            path=str(mt5_data.get("path", "")),
        ),
        strategy=StrategyConfig(
            symbol=str(_require_field("strategy", strategy_data, "symbol")),
            params=dict(_require_field("strategy", strategy_data, "params")),
        ),
        trading=TradingConfig(
            timeframe=str(_require_field("trading", trading_data, "timeframe")),
            volume=_to_float(
                "trading", "volume", _require_field("trading", trading_data, "volume")
            ),
            magic_number=_to_int(
                "trading",
                "magic_number",
                _require_field("trading", trading_data, "magic_number"),
            ),
            initial_bars=_to_int(
                "trading",
                "initial_bars",
                _require_field("trading", trading_data, "initial_bars"),
            ),
            deviation=_to_int("trading", "deviation", trading_data.get("deviation", 10)),
        ),
        safety=SafetyConfig(
            min_balance=_to_float(
                "safety",
                "min_balance",
                _require_field("safety", safety_data, "min_balance"),
            ),
            min_margin_level=_to_float(
                "safety",
                "min_margin_level",
                _require_field("safety", safety_data, "min_margin_level"),
            ),
            max_positions=_to_int(
                "safety",
                "max_positions",
                _require_field("safety", safety_data, "max_positions"),
            ),
            max_daily_trades=_to_int(
                "safety",
                "max_daily_trades",
                _require_field("safety", safety_data, "max_daily_trades"),
            ),
        ),
        notifications=NotificationConfig(
            enable_email=_to_bool(notifications_data.get("enable_email", False)),
            smtp_host=str(notifications_data.get("smtp_host", "")),
            smtp_port=_to_int("notifications", "smtp_port", notifications_data.get("smtp_port", 587)),
            smtp_user=str(notifications_data.get("smtp_user", "")),
            smtp_password=str(notifications_data.get("smtp_password", "")),
            recipients=_to_list_str(notifications_data.get("recipients", [])),
        ),
        logging=LoggingConfig(
            dir=str(_require_field("logging", logging_data, "dir")),
            level=str(logging_data.get("level", "INFO")),
        ),
        state=StateConfig(file=str(_require_field("state", state_data, "file"))),
    )
    return model


class Config:
    """Typed configuration loader for single-strategy live runtime."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        loaded = load_config_mapping(self.config_path)
        self._model = parse_live_config(loaded)
        self._config = loaded

    # MT5 Configuration
    @property
    def mt5_login(self) -> int:
        return self._model.mt5.login

    @property
    def mt5_password(self) -> str:
        return self._model.mt5.password

    @property
    def mt5_server(self) -> str:
        return self._model.mt5.server

    @property
    def mt5_path(self) -> str:
        return self._model.mt5.path

    # Strategy Configuration
    @property
    def strategy_symbol(self) -> str:
        return self._model.strategy.symbol

    @property
    def strategy_params(self) -> Dict[str, Any]:
        return dict(self._model.strategy.params)

    # Trading Configuration
    @property
    def trading_timeframe(self) -> str:
        return self._model.trading.timeframe

    @property
    def trading_volume(self) -> float:
        return self._model.trading.volume

    @property
    def trading_magic_number(self) -> int:
        return self._model.trading.magic_number

    @property
    def trading_initial_bars(self) -> int:
        return self._model.trading.initial_bars

    @property
    def trading_deviation(self) -> int:
        return self._model.trading.deviation

    # Safety Configuration
    @property
    def safety_min_balance(self) -> float:
        return self._model.safety.min_balance

    @property
    def safety_min_margin_level(self) -> float:
        return self._model.safety.min_margin_level

    @property
    def safety_max_positions(self) -> int:
        return self._model.safety.max_positions

    @property
    def safety_max_daily_trades(self) -> int:
        return self._model.safety.max_daily_trades

    # Notification Configuration
    @property
    def notifications_enabled(self) -> bool:
        return self._model.notifications.enable_email

    @property
    def smtp_host(self) -> str:
        return self._model.notifications.smtp_host

    @property
    def smtp_port(self) -> int:
        return self._model.notifications.smtp_port

    @property
    def smtp_user(self) -> str:
        return self._model.notifications.smtp_user

    @property
    def smtp_password(self) -> str:
        return self._model.notifications.smtp_password

    @property
    def email_recipients(self) -> List[str]:
        return list(self._model.notifications.recipients)

    # Logging Configuration
    @property
    def logging_dir(self) -> str:
        return self._model.logging.dir

    @property
    def logging_level(self) -> str:
        return self._model.logging.level

    # State Configuration
    @property
    def state_file(self) -> str:
        return self._model.state.file

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def __repr__(self) -> str:
        return (
            f"Config(symbol={self.strategy_symbol}, "
            f"timeframe={self.trading_timeframe}, "
            f"volume={self.trading_volume})"
        )
