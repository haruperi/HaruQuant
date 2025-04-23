"""
Configuration settings management
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
import configparser

from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class Settings:
    """Configuration settings manager."""
    
    def __init__(self):
        """Initialize the settings manager."""
        self._config = configparser.ConfigParser()
        self._env_vars: Dict[str, Any] = {}
        
    def load(self) -> None:
        """Load configuration from files and environment variables."""
        try:
            # Load environment variables
            load_dotenv()
            
            # Load config file
            config_path = Path("config.ini")
            if config_path.exists():
                self._config.read(config_path)
                
            # Load environment variables
            self._load_env_vars()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.exception("Error loading configuration")
            raise ConfigurationError("Failed to load configuration") from e
            
    def _load_env_vars(self) -> None:
        """Load environment variables."""
        self._env_vars = {
            "MT5_LOGIN": os.getenv("MT5_LOGIN"),
            "MT5_PASSWORD": os.getenv("MT5_PASSWORD"),
            "MT5_SERVER": os.getenv("MT5_SERVER"),
            "MT5_PATH": os.getenv("MT5_PATH"),
            "DB_HOST": os.getenv("DB_HOST"),
            "DB_PORT": os.getenv("DB_PORT"),
            "DB_NAME": os.getenv("DB_NAME"),
            "DB_USER": os.getenv("DB_USER"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
            "NEWS_API_KEY": os.getenv("NEWS_API_KEY"),
        }
        
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: The configuration section
            key: The configuration key
            default: Default value if not found
            
        Returns:
            The configuration value
        """
        try:
            # Try to get from config file
            if self._config.has_section(section):
                if self._config.has_option(section, key):
                    return self._config.get(section, key)
                    
            # Try to get from environment variables
            env_key = f"{section}_{key}".upper()
            if env_key in self._env_vars:
                return self._env_vars[env_key]
                
            return default
            
        except Exception as e:
            logger.exception(f"Error getting configuration value: {section}.{key}")
            return default
            
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            section: The configuration section
            key: The configuration key
            value: The configuration value
        """
        try:
            if not self._config.has_section(section):
                self._config.add_section(section)
            self._config.set(section, key, str(value))
            
            # Save to config file
            with open("config.ini", "w") as f:
                self._config.write(f)
                
            logger.debug(f"Configuration value set: {section}.{key}")
            
        except Exception as e:
            logger.exception(f"Error setting configuration value: {section}.{key}")
            raise ConfigurationError(f"Failed to set configuration value: {section}.{key}") from e 