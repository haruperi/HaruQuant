import json

import pytest

from apps.live.config import ConfigError, load_config_mapping


def _base_payload():
    return {
        "schema_version": "1.0.0",
        "mt5": {
            "login": 123456,
            "password": "password",
            "server": "MetaQuotes-Demo",
            "path": "C:/Program Files/MetaTrader 5/terminal64.exe",
        },
        "strategy": {"symbol": "EURUSD", "params": {"period": 14}},
        "trading": {
            "timeframe": "M15",
            "volume": 0.1,
            "magic_number": 123456,
            "initial_bars": 100,
            "deviation": 20,
        },
        "safety": {
            "min_balance": 1000.0,
            "min_margin_level": 50.0,
            "max_positions": 5,
            "max_daily_trades": 10,
        },
        "notifications": {
            "enable_email": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user@example.com",
            "smtp_password": "password",
            "recipients": ["admin@example.com"],
        },
        "logging": {"dir": "logs", "level": "DEBUG"},
        "state": {"file": "state.json"},
    }


def test_config_schema_version_supported(tmp_path):
    config_file = tmp_path / "schema_supported.json"
    config_file.write_text(json.dumps(_base_payload()))
    loaded = load_config_mapping(config_file)
    assert loaded["schema_version"] == "1.0.0"


def test_config_schema_version_unsupported_rejected(tmp_path):
    payload = _base_payload()
    payload["schema_version"] = "2.0.0"
    config_file = tmp_path / "schema_unsupported.json"
    config_file.write_text(json.dumps(payload))
    with pytest.raises(ConfigError, match="Unsupported schema_version"):
        load_config_mapping(config_file)

