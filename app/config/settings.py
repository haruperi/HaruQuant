"""
Configuration management system for HaruQuant trading bot.
"""

import os
import json
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar, Union
from datetime import datetime

from dotenv import load_dotenv

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    pass

class ConfigurationManager:
    """Manages configuration loading, validation, and access."""
    
    def __init__(self, 
                 config_path: str = "config.ini",
                 env_prefix: str = "HARUQUANT_",
                 default_config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to the configuration file
            env_prefix: Prefix for environment variables
            default_config: Default configuration values
        """
        self.config_path = Path(config_path)
        self.env_prefix = env_prefix
        self.default_config = default_config or {}
        self._config: Dict[str, Any] = {}
        self._config_version = "1.0.0"
        self._last_loaded = None
        
    def load(self) -> None:
        """Load configuration from all sources."""
        try:
            # Load environment variables
            load_dotenv()
            
            # Initialize with defaults
            self._config = self.default_config.copy()
            
            # Load from INI file if exists
            if self.config_path.exists():
                self._load_ini_config()
                
            # Override with environment variables
            self._load_env_config()
            
            # Validate configuration
            self._validate_config()
            
            # Update last loaded timestamp
            self._last_loaded = datetime.now()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
            
    def _load_ini_config(self) -> None:
        """Load configuration from INI file."""
        config = ConfigParser()
        config.read(self.config_path)
        
        for section in config.sections():
            if section not in self._config:
                self._config[section] = {}
                
            for key, value in config[section].items():
                # Try to convert to appropriate type
                try:
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif value.replace('.', '', 1).isdigit():
                        value = float(value)
                except (ValueError, AttributeError):
                    pass
                    
                self._config[section][key] = value
                
    def _load_env_config(self) -> None:
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Convert env key to section.key format
                parts = key[len(self.env_prefix):].lower().split('_')
                if len(parts) >= 2:
                    section = parts[0]
                    key = '_'.join(parts[1:])
                    
                    if section not in self._config:
                        self._config[section] = {}
                        
                    self._config[section][key] = value
                    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        required_sections = ['logging', 'mt5', 'database']
        for section in required_sections:
            if section not in self._config:
                raise ConfigurationError(f"Missing required configuration section: {section}")
                
        # Validate MT5 configuration
        mt5_config = self._config.get('mt5', {})
        required_mt5_keys = ['terminal_path', 'server', 'login', 'password']
        for key in required_mt5_keys:
            if key not in mt5_config:
                raise ConfigurationError(f"Missing required MT5 configuration: {key}")
                
        # Validate database configuration
        db_config = self._config.get('database', {})
        required_db_keys = ['host', 'port', 'name', 'user', 'password']
        for key in required_db_keys:
            if key not in db_config:
                raise ConfigurationError(f"Missing required database configuration: {key}")
                
    def get(self, 
            section: str, 
            key: str, 
            default: Optional[Any] = None,
            type_hint: Optional[Type[T]] = None) -> Union[Any, T]:
        """
        Get a configuration value with type hinting.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            type_hint: Expected type of the value
            
        Returns:
            The configuration value
        """
        try:
            value = self._config[section][key]
            if type_hint and value is not None:
                return type_hint(value)
            return value
        except (KeyError, ValueError):
            if default is not None:
                return default
            raise ConfigurationError(f"Configuration not found: {section}.{key}")
            
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: New value
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        
    def save(self) -> None:
        """Save configuration to file."""
        try:
            config = ConfigParser()
            
            for section, items in self._config.items():
                config[section] = {}
                for key, value in items.items():
                    config[section][key] = str(value)
                    
            with open(self.config_path, 'w') as f:
                config.write(f)
                
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}")
            
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Configuration section name
            
        Returns:
            Dictionary of section settings
        """
        return self._config.get(section, {}).copy()
        
    def update_section(self, section: str, values: Dict[str, Any]) -> None:
        """
        Update an entire configuration section.
        
        Args:
            section: Configuration section name
            values: New section values
        """
        self._config[section] = values.copy()
        
    def to_dict(self) -> Dict[str, Any]:
        """Get the entire configuration as a dictionary."""
        return self._config.copy()
        
    def from_dict(self, config: Dict[str, Any]) -> None:
        """
        Load configuration from a dictionary.
        
        Args:
            config: Configuration dictionary
        """
        self._config = config.copy()
        self._validate_config()
        
    def get_version(self) -> str:
        """Get the configuration version."""
        return self._config_version
        
    def get_last_loaded(self) -> Optional[datetime]:
        """Get the timestamp when configuration was last loaded."""
        return self._last_loaded

# Create a global instance
config_manager = ConfigurationManager()

def load_settings(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Load settings from config file and environment variables.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing all settings
    """
    global config_manager
    config_manager = ConfigurationManager(config_path=config_path)
    config_manager.load()
    return config_manager.to_dict()

def get_setting(section: str, key: str, settings: Optional[Dict[str, Any]] = None) -> Any:
    """
    Get a specific setting value.
    
    Args:
        section: Configuration section name
        key: Setting key name
        settings: Optional settings dictionary (will load if not provided)
        
    Returns:
        The setting value
    """
    if settings is None:
        settings = load_settings()
    return settings[section][key] 