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
        "terminal_path": config.get("mt5", "terminal_path"),
        "server": config.get("mt5", "server"),
        "login": int(config.get("mt5", "login")),
        "password": os.getenv("MT5_PASSWORD", ""),
        "symbols": [s.strip() for s in config.get("mt5", "symbols").split(",")]
    }
    
    # Load trading settings
    settings["trading"] = {
        "risk_per_trade": float(config.get("trading", "risk_per_trade")),
        "max_open_trades": int(config.get("trading", "max_open_trades")),
        "stop_loss_pips": int(config.get("trading", "stop_loss_pips")),
        "take_profit_pips": int(config.get("trading", "take_profit_pips"))
    }
    
    # Load backtesting settings
    settings["backtesting"] = {
        "start_date": config.get("backtesting", "start_date"),
        "end_date": config.get("backtesting", "end_date"),
        "initial_balance": float(config.get("backtesting", "initial_balance")),
        "commission_rate": float(config.get("backtesting", "commission_rate"))
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