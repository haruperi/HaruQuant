"""
Utility functions and helper methods for the trading system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
from functools import wraps

from utils import get_logger

logger = get_logger(__name__)

def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying a function on exception with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {str(e)}",
                            exc_info=True
                        )
                        raise last_exception
            return None
        return wrapper
    return decorator

def format_price(price: Union[float, Decimal], precision: int = 5) -> str:
    """
    Format a price with the specified precision.
    
    Args:
        price: Price to format
        precision: Number of decimal places
        
    Returns:
        Formatted price string
    """
    return f"{float(price):.{precision}f}"

def calculate_pip_value(
    symbol: str,
    price: float,
    lot_size: float = 1.0,
    account_currency: str = "USD"
) -> float:
    """
    Calculate the pip value for a given symbol and price.
    
    Args:
        symbol: Trading symbol
        price: Current price
        lot_size: Size of the lot
        account_currency: Account currency
        
    Returns:
        Pip value in account currency
    """
    # Base pip value calculation
    pip_value = 0.0001  # Standard pip value for most pairs
    
    # Adjust for JPY pairs
    if symbol.endswith("JPY"):
        pip_value = 0.01
    
    # Calculate pip value in account currency
    if account_currency == "USD":
        if symbol.startswith("USD"):
            return pip_value * lot_size
        elif symbol.endswith("USD"):
            return pip_value * lot_size / price
        else:
            # For cross pairs, we need to convert through USD
            # This is a simplified version - in production, you'd want to
            # handle all currency conversions properly
            return pip_value * lot_size / price
    
    # Add more currency handling as needed
    return pip_value * lot_size

def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    symbol: str,
    price: float,
    account_currency: str = "USD"
) -> float:
    """
    Calculate position size based on risk management parameters.
    
    Args:
        account_balance: Account balance in account currency
        risk_percent: Maximum risk percentage
        stop_loss_pips: Stop loss in pips
        symbol: Trading symbol
        price: Current price
        account_currency: Account currency
        
    Returns:
        Position size in lots
    """
    # Calculate risk amount in account currency
    risk_amount = account_balance * (risk_percent / 100)
    
    # Calculate pip value
    pip_value = calculate_pip_value(symbol, price, 1.0, account_currency)
    
    # Calculate position size
    position_size = risk_amount / (stop_loss_pips * pip_value)
    
    # Round to standard lot sizes
    return round(position_size, 2)
