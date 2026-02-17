import json
from types import SimpleNamespace

import pytest

from apps.live.config import Config, ConfigError


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


def _patch_auth(monkeypatch, *, user_id: int | None, is_superuser: bool):
    import apps.api.auth_utils as auth_utils
    import apps.sqlite.database_operations as database_operations

    class _FakeDB:
        def get_user(self, user_id=None, username=None, email=None):
            if user_id is None:
                return None
            return {
                "id": int(user_id),
                "username": "admin" if is_superuser else "viewer",
                "is_superuser": is_superuser,
            }

    monkeypatch.setattr(
        auth_utils,
        "verify_token",
        lambda token, db: user_id,
    )
    monkeypatch.setattr(database_operations, "DatabaseManager", _FakeDB)


def test_privileged_live_mutation_requires_superuser(tmp_path, monkeypatch):
    config_file = tmp_path / "live_config.json"
    config_file.write_text(json.dumps(_base_payload()), encoding="utf-8")

    _patch_auth(monkeypatch, user_id=1, is_superuser=False)
    config = Config(str(config_file), profile="live")

    with pytest.raises(ConfigError, match="superuser role required"):
        config.apply_privileged_mutation(
            "logging.level",
            "ERROR",
            authorization_token="Bearer token",
            reason="incident response",
            audit_log_path=tmp_path / "audit.jsonl",
        )


def test_privileged_live_mutation_applies_and_audits(tmp_path, monkeypatch):
    config_file = tmp_path / "live_config_ok.json"
    config_file.write_text(json.dumps(_base_payload()), encoding="utf-8")
    audit_file = tmp_path / "audit.jsonl"

    _patch_auth(monkeypatch, user_id=7, is_superuser=True)
    config = Config(str(config_file), profile="live")

    config.apply_privileged_mutation(
        "logging.level",
        "ERROR",
        authorization_token="Bearer valid-token",
        reason="reduce noisy logs",
        audit_log_path=audit_file,
    )

    assert config.logging_level == "ERROR"
    lines = [line.strip() for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "live_config_mutation"
    assert record["key"] == "logging.level"
    assert record["user_id"] == 7


def test_non_live_profile_mutation_skips_role_gate(tmp_path):
    config_file = tmp_path / "paper_config.json"
    config_file.write_text(json.dumps(_base_payload()), encoding="utf-8")
    config = Config(str(config_file), profile="paper")

    config.apply_privileged_mutation(
        "trading.volume",
        0.25,
        authorization_token="token-not-checked-for-paper",
        reason="paper tuning",
        audit_log_path=tmp_path / "paper_audit.jsonl",
    )

    assert config.trading_volume == 0.25

