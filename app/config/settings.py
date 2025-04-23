"""
Configuration settings management for HaruQuant trading bot.
"""

import os
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

def load_settings(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Load settings from config file and environment variables.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing all settings
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize config parser
    config = ConfigParser()
    config.read(config_path)
    
    # Create settings dictionary
    settings = {}
    
    # Load logging settings
    settings["logging"] = {
        "level": config.get("logging", "level", fallback="INFO"),
        "log_file": config.get("logging", "log_file", fallback="logs/harutrader.log")
    }
    
    # Load MT5 settings
    settings["mt5"] = {
        "terminal_path": config.get("mt5", "path"),
        "server": config.get("mt5", "server"),
        "login": int(config.get("mt5", "login")),
        "password": os.getenv("MT5_PASSWORD", config.get("mt5", "password")),
        "symbols": [s.strip() for s in config.get("mt5", "symbols").split(",")],
        "timeframe": config.get("mt5", "timeframe")
    }
    
    # Load database settings
    settings["database"] = {
        "host": config.get("database", "host"),
        "port": int(config.get("database", "port")),
        "name": config.get("database", "name"),
        "user": config.get("database", "user"),
        "password": os.getenv("DB_PASSWORD", config.get("database", "password"))
    }
    
    # Load dashboard settings
    settings["dashboard"] = {
        "host": config.get("dashboard", "host"),
        "port": int(config.get("dashboard", "port")),
        "secret_key": os.getenv("DASHBOARD_SECRET_KEY", config.get("dashboard", "secret_key"))
    }
    
    # Load API settings
    settings["api"] = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", config.get("api", "telegram_bot_token")),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", config.get("api", "telegram_chat_id")),
        "news_api_key": os.getenv("NEWS_API_KEY", config.get("api", "news_api_key"))
    }
    
    return settings

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