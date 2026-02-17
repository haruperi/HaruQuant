
import json
import os
import pytest
from apps.live.config import (
    Config,
    ConfigError,
    get_schema_spec,
    load_config_mapping,
)

def test_load_valid_config(tmp_path, mock_config_data):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    config = Config(str(config_file))
    
    # MT5
    assert config.mt5_login == 123456
    assert config.mt5_password == "password"
    assert config.mt5_server == "MetaQuotes-Demo"
    assert config.mt5_path == "C:/Program Files/MetaTrader 5/terminal64.exe"
    
    # Strategy
    assert config.strategy_symbol == "EURUSD"
    assert config.strategy_params == {"period": 14}
    
    # Trading
    assert config.trading_timeframe == "M15"
    assert config.trading_volume == 0.1
    assert config.trading_magic_number == 123456
    assert config.trading_initial_bars == 100
    assert config.trading_deviation == 20
    
    # Safety
    assert config.safety_min_balance == 1000.0
    assert config.safety_min_margin_level == 50.0
    assert config.safety_max_positions == 5
    assert config.safety_max_daily_trades == 10
    
    # Notifications
    assert config.notifications_enabled is True
    assert config.smtp_host == "smtp.example.com"
    assert config.smtp_port == 587
    assert config.smtp_user == "user@example.com"
    assert config.smtp_password == "password"
    assert config.email_recipients == ["admin@example.com"]
    
    # Logging
    assert config.logging_dir == "logs"
    assert config.logging_level == "DEBUG"
    
    # State
    assert config.state_file == "state.json"

def test_config_file_not_found():
    with pytest.raises(ConfigError, match="Config file not found"):
        Config("non_existent_file.json")

def test_invalid_json(tmp_path):
    config_file = tmp_path / "bad_config.json"
    config_file.write_text("{invalid json")
    
    with pytest.raises(ConfigError, match="Invalid JSON"):
        Config(str(config_file))

def test_env_var_substitution(tmp_path, mock_config_data):
    mock_config_data["mt5"]["password"] = "${MT5_PASSWORD}"
    config_file = tmp_path / "env_config.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    os.environ["MT5_PASSWORD"] = "secret_password"
    try:
        config = Config(str(config_file))
        assert config.mt5_password == "secret_password"
    finally:
        del os.environ["MT5_PASSWORD"]

def test_missing_env_var(tmp_path, mock_config_data):
    mock_config_data["mt5"]["password"] = "${MISSING_VAR}"
    config_file = tmp_path / "env_config_error.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    with pytest.raises(ConfigError, match="Environment variable not found"):
        Config(str(config_file))

def test_missing_section(tmp_path, mock_config_data):
    del mock_config_data["mt5"]
    config_file = tmp_path / "missing_section.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    with pytest.raises(ConfigError, match="Missing required section: mt5"):
        Config(str(config_file))

def test_missing_field(tmp_path, mock_config_data):
    del mock_config_data["mt5"]["login"]
    config_file = tmp_path / "missing_field.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    with pytest.raises(ConfigError, match="Missing required field: mt5.login"):
        Config(str(config_file))

def test_get_method(tmp_path, mock_config_data):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    config = Config(str(config_file))
    
    assert config.get("mt5.login") == 123456
    assert config.get("strategy.params") == {"period": 14}
    assert config.get("non.existent.key") is None
    assert config.get("non.existent.key", "default") == "default"

def test_repr(tmp_path, mock_config_data):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(mock_config_data))
    
    config = Config(str(config_file))
    assert "Config(symbol=EURUSD, timeframe=M15, volume=0.1)" in repr(config)

def test_load_valid_toml_config(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[mt5]
login = 123456
password = "password"
server = "MetaQuotes-Demo"
path = "C:/Program Files/MetaTrader 5/terminal64.exe"

[strategy]
symbol = "EURUSD"

[strategy.params]
period = 14

[trading]
timeframe = "M15"
volume = 0.1
magic_number = 123456
initial_bars = 100
deviation = 20

[safety]
min_balance = 1000.0
min_margin_level = 50.0
max_positions = 5
max_daily_trades = 10

[notifications]
enable_email = true
smtp_host = "smtp.example.com"
smtp_port = 587
smtp_user = "user@example.com"
smtp_password = "password"
recipients = ["admin@example.com"]

[logging]
dir = "logs"
level = "DEBUG"

[state]
file = "state.json"
"""
    )

    config = Config(str(config_file))
    assert config.mt5_login == 123456
    assert config.trading_volume == 0.1
    assert config.logging_level == "DEBUG"

def test_env_overlay_precedence(tmp_path, mock_config_data):
    config_file = tmp_path / "overlay_config.json"
    config_file.write_text(json.dumps(mock_config_data))

    os.environ["HQT_TRADING__VOLUME"] = "0.25"
    os.environ["HQT_MT5__LOGIN"] = "777777"
    try:
        config = Config(str(config_file))
        assert config.trading_volume == 0.25
        assert config.mt5_login == 777777
    finally:
        del os.environ["HQT_TRADING__VOLUME"]
        del os.environ["HQT_MT5__LOGIN"]


def test_profile_overlay_applies_from_file(tmp_path, mock_config_data):
    payload = dict(mock_config_data)
    payload["profiles"] = {
        "dev": {"trading": {"volume": 0.05}, "logging": {"level": "DEBUG"}},
        "live": {"trading": {"volume": 0.2}, "logging": {"level": "WARNING"}},
    }
    config_file = tmp_path / "profile_config.json"
    config_file.write_text(json.dumps(payload))

    config = Config(str(config_file), profile="live")
    assert config.trading_volume == 0.2
    assert config.logging_level == "WARNING"
    assert config.active_profile == "live"


def test_precedence_runtime_overrides_highest(tmp_path, mock_config_data):
    payload = dict(mock_config_data)
    payload["profiles"] = {"paper": {"trading": {"volume": 0.15}}}
    config_file = tmp_path / "precedence_config.json"
    config_file.write_text(json.dumps(payload))

    os.environ["HQT_TRADING__VOLUME"] = "0.25"
    try:
        config = Config(
            str(config_file),
            profile="paper",
            runtime_overrides={"trading.volume": 0.33},
        )
        assert config.trading_volume == 0.33
    finally:
        del os.environ["HQT_TRADING__VOLUME"]


def test_invalid_schema_version_rejected(tmp_path, mock_config_data):
    payload = dict(mock_config_data)
    payload["schema_version"] = "9.9.9"
    config_file = tmp_path / "bad_schema_version.json"
    config_file.write_text(json.dumps(payload))

    with pytest.raises(ConfigError, match="Unsupported schema_version"):
        Config(str(config_file))


def test_schema_version_defaults_when_missing(tmp_path, mock_config_data):
    config_file = tmp_path / "default_schema_version.json"
    config_file.write_text(json.dumps(mock_config_data))
    config = Config(str(config_file))
    assert config.schema_version == "1.0.0"


def test_runtime_reload_non_critical(tmp_path, mock_config_data):
    config_file = tmp_path / "reload_non_critical.json"
    config_file.write_text(json.dumps(mock_config_data))

    config = Config(str(config_file))
    assert config.logging_level == "DEBUG"
    assert config.safety_max_positions == 5

    payload = dict(mock_config_data)
    payload["logging"] = dict(payload["logging"])
    payload["safety"] = dict(payload["safety"])
    payload["logging"]["level"] = "ERROR"
    payload["safety"]["max_positions"] = 7
    config_file.write_text(json.dumps(payload))

    changed = config.reload_non_critical()
    assert "logging.level" in changed
    assert "safety.max_positions" in changed
    assert config.logging_level == "ERROR"
    assert config.safety_max_positions == 7


def test_schema_spec_is_self_documenting():
    spec = get_schema_spec()
    assert "logging.level" in spec
    assert "description" in spec["logging.level"]
    assert "safeguards" in spec["logging.level"]
    assert "units" in spec["logging.level"]


def test_hqt_profile_env_is_used_when_profile_not_passed(tmp_path, mock_config_data):
    payload = dict(mock_config_data)
    payload["profiles"] = {"backtest": {"trading": {"volume": 0.07}}}
    config_file = tmp_path / "env_profile.json"
    config_file.write_text(json.dumps(payload))

    os.environ["HQT_PROFILE"] = "BACKTEST"
    try:
        loaded = load_config_mapping(str(config_file))
        assert loaded["trading"]["volume"] == 0.07
    finally:
        del os.environ["HQT_PROFILE"]
