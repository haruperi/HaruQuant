"""Configuration Management.

Handles loading and validation of live trading configuration from JSON file
with environment variable substitution support.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict


class ConfigError(Exception):
    """Configuration error."""

    pass


class Config:
    """Configuration loader and manager."""

    def __init__(self, config_path: str):
        """Initialize configuration from JSON file.

        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")

        self._config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with env var substitution."""
        try:
            with open(self.config_path, "r") as f:
                content = f.read()

            # Substitute environment variables (${VAR_NAME})
            content = self._substitute_env_vars(content)

            config = json.loads(content)
            return dict(config)

        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")

    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in format ${VAR_NAME}."""
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ConfigError(f"Environment variable not found: {var_name}")
            return value

        return re.sub(pattern, replacer, content)

    def _validate_config(self):
        """Validate required configuration fields."""
        required_sections = [
            "mt5",
            "strategy",
            "trading",
            "safety",
            "notifications",
            "logging",
            "state",
        ]

        for section in required_sections:
            if section not in self._config:
                raise ConfigError(f"Missing required section: {section}")

        self._validate_mt5()
        self._validate_strategy()
        self._validate_trading()
        self._validate_safety()
        self._validate_logging()
        self._validate_state()

    def _validate_mt5(self):
        """Validate MT5 section."""
        required = ["login", "password", "server"]
        for field in required:
            if field not in self._config["mt5"]:
                raise ConfigError(f"Missing required field: mt5.{field}")

    def _validate_strategy(self):
        """Validate strategy section."""
        if "symbol" not in self._config["strategy"]:
            raise ConfigError("Missing required field: strategy.symbol")
        if "params" not in self._config["strategy"]:
            raise ConfigError("Missing required field: strategy.params")

    def _validate_trading(self):
        """Validate trading section."""
        required = ["timeframe", "volume", "magic_number", "initial_bars"]
        for field in required:
            if field not in self._config["trading"]:
                raise ConfigError(f"Missing required field: trading.{field}")

    def _validate_safety(self):
        """Validate safety section."""
        required = [
            "min_balance",
            "min_margin_level",
            "max_positions",
            "max_daily_trades",
        ]
        for field in required:
            if field not in self._config["safety"]:
                raise ConfigError(f"Missing required field: safety.{field}")

    def _validate_logging(self):
        """Validate logging section."""
        if "dir" not in self._config["logging"]:
            raise ConfigError("Missing required field: logging.dir")

    def _validate_state(self):
        """Validate state section."""
        if "file" not in self._config["state"]:
            raise ConfigError("Missing required field: state.file")

    # MT5 Configuration
    @property
    def mt5_login(self) -> int:
        """Get MT5 login ID."""
        return int(self._config["mt5"]["login"])

    @property
    def mt5_password(self) -> str:
        """Get MT5 password."""
        return str(self._config["mt5"]["password"])

    @property
    def mt5_server(self) -> str:
        """Get MT5 server."""
        return str(self._config["mt5"]["server"])

    @property
    def mt5_path(self) -> str:
        """Get custom MT5 terminal path."""
        return str(self._config["mt5"].get("path", ""))

    # Strategy Configuration
    @property
    def strategy_symbol(self) -> str:
        """Get trading symbol."""
        return str(self._config["strategy"]["symbol"])

    @property
    def strategy_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return dict(self._config["strategy"]["params"])

    # Trading Configuration
    @property
    def trading_timeframe(self) -> str:
        """Get trading timeframe."""
        return str(self._config["trading"]["timeframe"])

    @property
    def trading_volume(self) -> float:
        """Get fixed trading lot size."""
        return float(self._config["trading"]["volume"])

    @property
    def trading_magic_number(self) -> int:
        """Get expert magic number."""
        return int(self._config["trading"]["magic_number"])

    @property
    def trading_initial_bars(self) -> int:
        """Get number of historical bars to load."""
        return int(self._config["trading"]["initial_bars"])

    @property
    def trading_deviation(self) -> int:
        """Get maximum price deviation."""
        return int(self._config["trading"].get("deviation", 10))

    # Safety Configuration
    @property
    def safety_min_balance(self) -> float:
        """Get minimum required account balance."""
        return float(self._config["safety"]["min_balance"])

    @property
    def safety_min_margin_level(self) -> float:
        """Get minimum required margin level percentage."""
        return float(self._config["safety"]["min_margin_level"])

    @property
    def safety_max_positions(self) -> int:
        """Get maximum allowed open positions."""
        return int(self._config["safety"]["max_positions"])

    @property
    def safety_max_daily_trades(self) -> int:
        """Get maximum allowed trades per day."""
        return int(self._config["safety"]["max_daily_trades"])

    # Notification Configuration
    @property
    def notifications_enabled(self) -> bool:
        """Check if email notifications are enabled."""
        return bool(self._config["notifications"].get("enable_email", False))

    @property
    def smtp_host(self) -> str:
        """Get SMTP server host."""
        return str(self._config["notifications"].get("smtp_host", ""))

    @property
    def smtp_port(self) -> int:
        """Get SMTP server port."""
        return int(self._config["notifications"].get("smtp_port", 587))

    @property
    def smtp_user(self) -> str:
        """Get SMTP username."""
        return str(self._config["notifications"].get("smtp_user", ""))

    @property
    def smtp_password(self) -> str:
        """Get SMTP password."""
        return str(self._config["notifications"].get("smtp_password", ""))

    @property
    def email_recipients(self) -> list:
        """Get list of email recipients."""
        return list(self._config["notifications"].get("recipients", []))

    # Logging Configuration
    @property
    def logging_dir(self) -> str:
        """Get logging directory path."""
        return str(self._config["logging"]["dir"])

    @property
    def logging_level(self) -> str:
        """Get logging level."""
        return str(self._config["logging"].get("level", "INFO"))

    # State Configuration
    @property
    def state_file(self) -> str:
        """Get state file path."""
        return str(self._config["state"]["file"])

    def get(self, key: str, default=None) -> Any:
        """Get configuration value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'mt5.login')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def __repr__(self) -> str:
        """Return string representation of Config."""
        return f"Config(symbol={self.strategy_symbol}, timeframe={self.trading_timeframe}, volume={self.trading_volume})"
