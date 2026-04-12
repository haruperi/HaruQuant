"""Typed configuration management for live trading.

Supports:
- TOML or JSON config files.
- ${ENV_VAR} substitution in file content.
- Environment overlay using `HQT_` prefix and `__` path separators.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from backend.services.live_trading.secrets import SecretProviderError, resolve_secret_reference
from backend.common.redaction import redact_mapping


class ConfigError(Exception):
    """Configuration error."""


SUPPORTED_SCHEMA_VERSIONS = {"1.0.0"}
DEFAULT_SCHEMA_VERSION = "1.0.0"
SUPPORTED_PROFILES = {"dev", "backtest", "paper", "live"}
DEFAULT_AUDIT_LOG_PATH = Path("artifacts/logs/security/secret_access_audit.json")

# Self-documenting schema metadata (FR-CONF-008)
CONFIG_SCHEMA_SPEC: Dict[str, Dict[str, str]] = {
    "mt5.login": {
        "description": "MT5 account login ID.",
        "safeguards": "Must be a valid positive account integer.",
        "units": "id",
    },
    "trading.volume": {
        "description": "Order volume (lot size).",
        "safeguards": "Must be > 0 and aligned with symbol constraints.",
        "units": "lots",
    },
    "logging.level": {
        "description": "Runtime logging severity threshold.",
        "safeguards": "Allowed levels: DEBUG/INFO/WARNING/ERROR/CRITICAL.",
        "units": "level",
    },
    "safety.max_positions": {
        "description": "Maximum open positions allowed.",
        "safeguards": "Must be >= 1.",
        "units": "positions",
    },
    "safety.max_daily_trades": {
        "description": "Maximum daily executed trades.",
        "safeguards": "Must be >= 0.",
        "units": "trades/day",
    },
}


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


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge overlay into base and return merged mapping."""
    out = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def _normalize_profile_name(profile: Optional[str]) -> Optional[str]:
    if profile is None:
        return None
    profile_name = profile.strip().lower()
    if not profile_name:
        return None
    return profile_name


def _apply_profile(data: Dict[str, Any], profile: Optional[str]) -> Dict[str, Any]:
    """
    Apply profile overlay from top-level `profiles` section if present.

    Precedence:
    - base config
    - selected profile overlay
    """
    profile_name = _normalize_profile_name(profile)
    if profile_name is None:
        return dict(data)

    if profile_name not in SUPPORTED_PROFILES:
        raise ConfigError(
            f"Unsupported profile: {profile_name}. "
            f"Supported profiles: {', '.join(sorted(SUPPORTED_PROFILES))}"
        )

    profiles_data = data.get("profiles")
    if profiles_data is None:
        return dict(data)
    if not isinstance(profiles_data, dict):
        raise ConfigError("Invalid profiles section: expected object")

    # Allow case-insensitive profile keys in config files.
    lookup: Dict[str, Any] = {str(k).strip().lower(): v for k, v in profiles_data.items()}
    if profile_name not in lookup:
        return dict(data)

    profile_overlay = lookup[profile_name]
    if not isinstance(profile_overlay, dict):
        raise ConfigError(f"Invalid profile data for '{profile_name}': expected object")

    base = dict(data)
    base.pop("profiles", None)
    return _deep_merge(base, profile_overlay)


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


def _apply_runtime_overrides(
    data: Dict[str, Any], runtime_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply runtime overrides.

    Supports two styles:
    - dotted path keys: {"logging.level": "DEBUG"}
    - nested mapping: {"logging": {"level": "DEBUG"}}
    """
    if not runtime_overrides:
        return dict(data)

    out = dict(data)
    for key, value in runtime_overrides.items():
        if isinstance(value, dict) and "." not in key:
            current = _get_nested(out, [key])
            current_dict = current if isinstance(current, dict) else {}
            _set_nested(out, [key], _deep_merge(current_dict, value))
            continue

        path = [token.strip().lower() for token in str(key).split(".") if token.strip()]
        if not path:
            continue
        _set_nested(out, path, value)
    return out


def _resolve_secret_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_secret_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_secret_values(v) for v in value]
    if isinstance(value, str):
        return resolve_secret_reference(value)
    return value


def _resolve_secrets_in_mapping(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resolved = _resolve_secret_values(data)
        if not isinstance(resolved, dict):
            raise ConfigError("Failed to resolve secrets: invalid mapping structure")
        return resolved
    except SecretProviderError as exc:
        raise ConfigError(f"Secret resolution error: {exc}") from exc


def _validate_schema_version(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    version = out.get("schema_version", DEFAULT_SCHEMA_VERSION)
    version_text = str(version).strip()
    if version_text not in SUPPORTED_SCHEMA_VERSIONS:
        raise ConfigError(
            f"Unsupported schema_version: {version_text}. "
            f"Supported: {', '.join(sorted(SUPPORTED_SCHEMA_VERSIONS))}"
        )
    out["schema_version"] = version_text
    return out


def _validate_schema_spec() -> None:
    required_meta = {"description", "safeguards", "units"}
    for key, metadata in CONFIG_SCHEMA_SPEC.items():
        if not isinstance(metadata, dict):
            raise ConfigError(f"Invalid schema metadata for {key}: expected object")
        missing = required_meta - set(metadata.keys())
        if missing:
            raise ConfigError(
                f"Schema metadata for {key} missing: {', '.join(sorted(missing))}"
            )


def get_schema_spec() -> Dict[str, Dict[str, str]]:
    """Return self-documenting schema metadata."""
    return deepcopy(CONFIG_SCHEMA_SPEC)


def load_config_mapping(
    config_path: str | Path,
    *,
    profile: Optional[str] = None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Load raw config mapping from TOML/JSON with precedence layers.

    Precedence:
    - base file config
    - selected profile overlay (`profiles.<profile>`)
    - environment overlay (`HQT_` variables)
    - runtime overrides
    """
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        content = path.read_text(encoding="utf-8")
        content = _substitute_env_vars(content)
        loaded = _parse_file(path, content)
        loaded = _validate_schema_version(loaded)
        _validate_schema_spec()

        # Profile can be passed explicitly, via HQT_PROFILE, or `profile` key in file.
        profile_name = (
            _normalize_profile_name(profile)
            or _normalize_profile_name(os.environ.get("HQT_PROFILE"))
            or _normalize_profile_name(str(loaded.get("profile", "")))
        )

        with_profile = _apply_profile(loaded, profile_name)
        with_env = _apply_env_overlay(with_profile)
        with_runtime = _apply_runtime_overrides(with_env, runtime_overrides)
        with_secrets = _resolve_secrets_in_mapping(with_runtime)
        return with_secrets
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

    _NON_CRITICAL_RUNTIME_KEYS = (
        "logging.level",
        "safety.max_positions",
        "safety.max_daily_trades",
        "safety.min_balance",
        "safety.min_margin_level",
        "trading.volume",
        "trading.deviation",
    )
    _PRIVILEGED_MUTABLE_KEYS = frozenset(_NON_CRITICAL_RUNTIME_KEYS)
    _RISK_OVERRIDE_KEYS = frozenset(
        (
            "safety.max_positions",
            "safety.max_daily_trades",
            "safety.min_balance",
            "safety.min_margin_level",
        )
    )

    def __init__(
        self,
        config_path: str,
        *,
        profile: Optional[str] = None,
        runtime_overrides: Optional[Dict[str, Any]] = None,
    ):
        self.config_path = Path(config_path)
        self._profile = _normalize_profile_name(profile)
        self._runtime_overrides: Dict[str, Any] = dict(runtime_overrides or {})
        self._config = self._load_current_mapping()
        self._model = parse_live_config(self._config)

    def _load_current_mapping(self) -> Dict[str, Any]:
        return load_config_mapping(
            self.config_path,
            profile=self._profile,
            runtime_overrides=self._runtime_overrides,
        )

    def reload(self) -> None:
        """Reload entire config with current profile/env/runtime precedence."""
        loaded = self._load_current_mapping()
        self._model = parse_live_config(loaded)
        self._config = loaded

    def set_runtime_override(self, key: str, value: Any) -> None:
        """Set runtime override using dotted-path key syntax."""
        key_text = str(key).strip()
        if not key_text:
            raise ConfigError("Runtime override key cannot be empty")
        self._runtime_overrides[key_text] = value
        self.reload()

    def clear_runtime_override(self, key: Optional[str] = None) -> None:
        """Clear one runtime override by key, or all when key is None."""
        if key is None:
            self._runtime_overrides.clear()
        else:
            self._runtime_overrides.pop(str(key).strip(), None)
        self.reload()

    def apply_privileged_mutation(
        self,
        key: str,
        value: Any,
        *,
        authorization_token: str,
        reason: str,
        actor: Optional[str] = None,
        audit_log_path: str | Path = DEFAULT_AUDIT_LOG_PATH,
    ) -> None:
        """
        Apply a runtime config mutation under privileged controls.

        Live profile requires explicit authorization and emits audit logs.
        """
        key_text = str(key).strip()
        if key_text not in self._PRIVILEGED_MUTABLE_KEYS:
            raise ConfigError(
                f"Key not allowed for privileged mutation: {key_text}. "
                f"Allowed: {', '.join(sorted(self._PRIVILEGED_MUTABLE_KEYS))}"
            )
        reason_text = str(reason).strip()
        if not reason_text:
            raise ConfigError("Privileged mutation requires non-empty reason")

        token = str(authorization_token).strip()
        if not token:
            raise ConfigError("authorization_token is required for privileged mutation")

        user_id = None
        username = actor
        if self.active_profile == "live":
            user_id, username = _authorize_privileged_actor(token, actor)

        before_value = self.get(key_text)
        self.set_runtime_override(key_text, value)
        after_value = self.get(key_text)

        _append_privileged_audit_event(
            audit_log_path=Path(audit_log_path),
            event={
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "event": "live_config_mutation",
                "profile": self.active_profile or "",
                "key": key_text,
                "reason": reason_text,
                "user_id": user_id,
                "actor": username or "",
                "before": before_value,
                "after": after_value,
            },
        )

    def apply_risk_override(
        self,
        key: str,
        value: Any,
        *,
        authorization_token: str,
        reason: str,
        actor: Optional[str] = None,
        audit_log_path: str | Path = DEFAULT_AUDIT_LOG_PATH,
    ) -> None:
        """
        Apply a role-bound risk override and emit immutable audit metadata.

        This is stricter than generic privileged mutation and only allows
        safety/risk keys used for live risk controls.
        """
        key_text = str(key).strip()
        if key_text not in self._RISK_OVERRIDE_KEYS:
            raise ConfigError(
                f"Key not allowed for risk override: {key_text}. "
                f"Allowed: {', '.join(sorted(self._RISK_OVERRIDE_KEYS))}"
            )

        reason_text = str(reason).strip()
        if not reason_text:
            raise ConfigError("Risk override requires non-empty reason")

        token = str(authorization_token).strip()
        if not token:
            raise ConfigError("authorization_token is required for risk override")

        user_id = None
        username = actor
        if self.active_profile == "live":
            user_id, username = _authorize_privileged_actor(token, actor)

        before_value = self.get(key_text)
        self.set_runtime_override(key_text, value)
        after_value = self.get(key_text)

        _append_privileged_audit_event(
            audit_log_path=Path(audit_log_path),
            event={
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "event": "risk_override",
                "profile": self.active_profile or "",
                "key": key_text,
                "reason": reason_text,
                "user_id": user_id,
                "actor": username or "",
                "before": before_value,
                "after": after_value,
            },
        )

    def reload_non_critical(self) -> List[str]:
        """
        Reload only non-critical config keys (logging levels, safety/risk limits).

        Returns:
            List of keys that changed.
        """
        loaded = self._load_current_mapping()
        changed: List[str] = []

        updated_config = deepcopy(self._config)
        for key in self._NON_CRITICAL_RUNTIME_KEYS:
            path = [token.strip() for token in key.split(".") if token.strip()]
            old_value = _get_nested(updated_config, path)
            new_value = _get_nested(loaded, path)
            if old_value != new_value:
                _set_nested(updated_config, [p.lower() for p in path], new_value)
                changed.append(key)

        self._model = parse_live_config(updated_config)
        self._config = updated_config
        return changed

    @property
    def schema_version(self) -> str:
        return str(self._config.get("schema_version", DEFAULT_SCHEMA_VERSION))

    @property
    def active_profile(self) -> Optional[str]:
        return self._profile

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


def _authorize_privileged_actor(
    authorization_token: str, actor: Optional[str] = None
) -> tuple[int, str]:
    try:
        from backend.api.main_app.auth_utils import verify_token
        from backend.db.sqlite.database_operations import DatabaseManager
    except Exception as exc:  # pragma: no cover - import environment specific
        raise ConfigError(f"Authorization subsystem unavailable: {exc}") from exc

    token = str(authorization_token).strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    db = DatabaseManager()
    user_id = verify_token(token, db)
    if not user_id:
        raise ConfigError("Unauthorized privileged mutation: invalid or expired token")

    user = db.get_user(user_id=int(user_id))
    if not user:
        raise ConfigError("Unauthorized privileged mutation: actor not found")
    if not bool(user.get("is_superuser", False)):
        raise ConfigError("Unauthorized privileged mutation: superuser role required")

    username = actor or str(user.get("username", ""))
    return int(user_id), username


def _append_privileged_audit_event(audit_log_path: Path, event: Dict[str, Any]) -> None:
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    safe_event = redact_mapping(dict(event))
    line = json.dumps(safe_event, ensure_ascii=True)
    with audit_log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
