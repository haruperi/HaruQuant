from datetime import datetime, timezone

from apps.utils.validate import (
    validate_config_schema,
    validate_market_schema,
    validate_trade_schema,
)


def test_validate_market_schema_valid_payload():
    payload = {
        "symbol": "EURUSD",
        "timestamp": datetime.now(timezone.utc),
        "bid": 1.1,
        "ask": 1.1002,
        "last": 1.1001,
        "volume": 1234.0,
    }
    ok, msg = validate_market_schema(payload)
    assert ok is True
    assert "valid" in msg.lower()


def test_validate_market_schema_rejects_ask_below_bid():
    payload = {
        "symbol": "EURUSD",
        "timestamp": datetime.now(timezone.utc),
        "bid": 1.2,
        "ask": 1.1,
        "volume": 100.0,
    }
    ok, msg = validate_market_schema(payload)
    assert ok is False
    assert "ask" in msg.lower()


def test_validate_trade_schema_valid_payload():
    payload = {
        "symbol": "EURUSD",
        "side": "buy",
        "order_type": "market",
        "volume": 0.1,
        "price": 1.1001,
        "stop_loss": 1.09,
        "take_profit": 1.12,
        "magic": 12345,
        "deviation": 10,
    }
    ok, msg = validate_trade_schema(payload)
    assert ok is True
    assert "valid" in msg.lower()


def test_validate_trade_schema_rejects_invalid_side():
    payload = {
        "symbol": "EURUSD",
        "side": "HOLD",
        "order_type": "MARKET",
        "volume": 0.1,
    }
    ok, msg = validate_trade_schema(payload)
    assert ok is False
    assert "side" in msg.lower()


def test_validate_config_schema_valid_payload():
    payload = {
        "mode": "paper",
        "logging": {
            "level": "warn",
            "component_levels": {"risk": "ERROR"},
            "stderr_enabled": True,
        },
        "risk": {
            "max_positions": 5,
            "max_drawdown_pct": 20.0,
            "max_risk_per_trade_pct": 2.0,
        },
    }
    ok, msg = validate_config_schema(payload)
    assert ok is True
    assert "valid" in msg.lower()


def test_validate_config_schema_rejects_invalid_mode():
    payload = {
        "mode": "demo",
        "logging": {"level": "INFO", "component_levels": {}, "stderr_enabled": True},
        "risk": {
            "max_positions": 5,
            "max_drawdown_pct": 20.0,
            "max_risk_per_trade_pct": 2.0,
        },
    }
    ok, msg = validate_config_schema(payload)
    assert ok is False
    assert "mode" in msg.lower()
