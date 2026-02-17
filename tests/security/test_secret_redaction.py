import json
import sys
import types

import pytest

from apps.live.config import ConfigError, _append_privileged_audit_event, load_config_mapping


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


def test_keyring_secret_reference_is_resolved(tmp_path, monkeypatch):
    payload = _base_payload()
    payload["mt5"]["password"] = "keyring://hqt/mt5_demo"
    config_file = tmp_path / "config_secret.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    fake_keyring = types.SimpleNamespace(
        get_password=lambda service, account: "resolved-password"
        if (service, account) == ("hqt", "mt5_demo")
        else None
    )
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)

    loaded = load_config_mapping(config_file)
    assert loaded["mt5"]["password"] == "resolved-password"


def test_missing_keyring_secret_raises_config_error(tmp_path, monkeypatch):
    payload = _base_payload()
    payload["mt5"]["password"] = "keyring://hqt/missing_secret"
    config_file = tmp_path / "config_secret_missing.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    fake_keyring = types.SimpleNamespace(get_password=lambda service, account: None)
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)

    with pytest.raises(ConfigError, match="Secret resolution error"):
        load_config_mapping(config_file)


def test_privileged_audit_log_redacts_sensitive_values(tmp_path):
    audit_file = tmp_path / "audit.jsonl"
    _append_privileged_audit_event(
        audit_log_path=audit_file,
        event={
            "event": "live_config_mutation",
            "before": {"password": "plain-secret"},
            "after": {"api_key": "key-123"},
        },
    )

    row = json.loads(audit_file.read_text(encoding="utf-8").strip())
    assert row["before"]["password"] == "***REDACTED***"
    assert row["after"]["api_key"] == "***REDACTED***"

