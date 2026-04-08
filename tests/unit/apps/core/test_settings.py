from __future__ import annotations

from pathlib import Path

import pytest

from apps.core.settings import (
    DEFAULT_ENVIRONMENT,
    RuntimeSettings,
    SettingsError,
    inject_runtime_settings,
    load_runtime_settings,
    load_runtime_settings_from_mapping,
)


def test_load_runtime_settings_uses_environment_template(tmp_path: Path):
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    (env_dir / "dev.env.example").write_text(
        "\n".join(
            [
                "APP_NAME=haruquant-dev",
                "API_PORT=8100",
                "DATABASE_URL=sqlite:///tmp/dev.db",
                "ALLOW_LIVE_MUTATIONS=false",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_runtime_settings(env_dir=env_dir)

    assert settings.environment == DEFAULT_ENVIRONMENT
    assert settings.app_name == "haruquant-dev"
    assert settings.api_port == 8100
    assert settings.database_url == "sqlite:///tmp/dev.db"
    assert settings.allow_live_mutations is False


def test_load_runtime_settings_prefers_prefixed_environment_values(tmp_path: Path):
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    (env_dir / "paper.env.example").write_text(
        "ALLOW_LIVE_MUTATIONS=false\nMT5_ENABLED=false\n",
        encoding="utf-8",
    )

    settings = load_runtime_settings(
        environment="paper",
        env_dir=env_dir,
        environ={
            "HQT_ALLOW_LIVE_MUTATIONS": "true",
            "HQT_MT5_ENABLED": "true",
            "HQT_API_HOST": "0.0.0.0",
        },
    )

    assert settings.environment == "paper"
    assert settings.allow_live_mutations is True
    assert settings.mt5_enabled is True
    assert settings.api_host == "0.0.0.0"


def test_load_runtime_settings_from_mapping_validates_environment():
    with pytest.raises(SettingsError):
        load_runtime_settings_from_mapping({"environment": "qa"})


def test_inject_runtime_settings_copies_serialized_values():
    target: dict[str, object] = {}
    settings = RuntimeSettings(environment="test", api_port=9000)

    inject_runtime_settings(target, settings)

    assert target["environment"] == "test"
    assert target["api_port"] == 9000

