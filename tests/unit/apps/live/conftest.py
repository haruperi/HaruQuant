
import pytest

@pytest.fixture
def mock_config_data():
    return {
        "mt5": {
            "login": 123456,
            "password": "password",
            "server": "MetaQuotes-Demo",
            "path": "C:/Program Files/MetaTrader 5/terminal64.exe"
        },
        "strategy": {
            "symbol": "EURUSD",
            "params": {"period": 14}
        },
        "trading": {
            "timeframe": "M15",
            "volume": 0.1,
            "magic_number": 123456,
            "initial_bars": 100,
            "deviation": 20
        },
        "safety": {
            "min_balance": 1000.0,
            "min_margin_level": 50.0,
            "max_positions": 5,
            "max_daily_trades": 10
        },
        "notifications": {
            "enable_email": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user@example.com",
            "smtp_password": "password",
            "recipients": ["admin@example.com"]
        },
        "logging": {
            "dir": "logs",
            "level": "DEBUG"
        },
        "state": {
            "file": "state.json"
        }
    }
