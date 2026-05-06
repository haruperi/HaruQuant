"""Shared environment-scoped settings loader for HaruQuant services."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SUPPORTED_ENVIRONMENTS = {"dev", "test", "paper", "staging", "prod"}
DEFAULT_ENVIRONMENT = "dev"
DEFAULT_ENV_DIR = Path("config/environments")


class SettingsError(ValueError):
    """Raised when settings cannot be loaded or validated."""


class RuntimeSettings(BaseModel):
    """Validated runtime settings shared across new agentic services."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    environment: str = DEFAULT_ENVIRONMENT
    app_name: str = "haruquant"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    ui_origin: str = "http://localhost:3000"
    database_url: str = "sqlite:///data/database/haruquant.db"
    event_backend: str = "inmemory"
    log_level: str = "INFO"
    allow_live_mutations: bool = False
    mt5_enabled: bool = False
    extra_config: Dict[str, str] = Field(default_factory=dict)

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_ENVIRONMENTS:
            raise ValueError(
                f"Unsupported environment '{value}'. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_ENVIRONMENTS))}"
            )
        return normalized

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(
                f"Unsupported log level '{value}'. "
                f"Expected one of: {', '.join(sorted(allowed))}"
            )
        return normalized


def _parse_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")
    return values


def _collect_prefixed_values(
    source: Mapping[str, str],
    prefix: str,
) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for key, value in source.items():
        if key.startswith(prefix):
            values[key[len(prefix) :].lower()] = value
    return values


def _normalize_mapping(
    values: Mapping[str, Any],
    *,
    environment: Optional[str] = None,
) -> Dict[str, Any]:
    data = {str(key).lower(): value for key, value in values.items()}
    if environment is not None:
        data["environment"] = environment
    return data


def load_runtime_settings(
    *,
    environment: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    env_dir: Path = DEFAULT_ENV_DIR,
    prefix: str = "HQT_",
) -> RuntimeSettings:
    """Load settings from env template defaults plus environment overrides."""

    process_env = environ if environ is not None else os.environ
    selected_env = (
        environment or process_env.get(f"{prefix}ENVIRONMENT") or DEFAULT_ENVIRONMENT
    ).lower()

    file_values = _parse_env_file(env_dir / f"{selected_env}.env.example")
    merged: Dict[str, Any] = _normalize_mapping(file_values, environment=selected_env)
    merged.update(_collect_prefixed_values(process_env, prefix))
    merged.setdefault("environment", selected_env)

    extra = {
        key: value
        for key, value in merged.items()
        if key not in RuntimeSettings.model_fields
    }
    merged["extra_config"] = extra

    try:
        validated = RuntimeSettings.model_validate(merged)
        if not isinstance(validated, RuntimeSettings):
            raise SettingsError(
                "validated runtime settings did not produce RuntimeSettings"
            )
        return validated
    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc


def load_runtime_settings_from_mapping(
    values: Mapping[str, Any],
    *,
    environment: Optional[str] = None,
) -> RuntimeSettings:
    """Validate a prebuilt mapping as runtime settings."""

    normalized = _normalize_mapping(values, environment=environment)
    extra = {
        key: value
        for key, value in normalized.items()
        if key not in RuntimeSettings.model_fields
    }
    normalized["extra_config"] = {str(k): str(v) for k, v in extra.items()}

    try:
        validated = RuntimeSettings.model_validate(normalized)
        if not isinstance(validated, RuntimeSettings):
            raise SettingsError(
                "validated runtime settings did not produce RuntimeSettings"
            )
        return validated
    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc


def inject_runtime_settings(
    target: MutableMapping[str, Any],
    settings: RuntimeSettings,
) -> None:
    """Copy validated settings into a mutable container."""

    target.update(settings.model_dump())
