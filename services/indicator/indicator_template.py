"""Indicator template for HaruQuant.

Follow this structure when creating new trend, momentum, or other indicators.
"""

import pandas as pd

from services.utils.logger import logger
from services.indicator.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
    # require_positive_float, # Use if needed for multipliers/sigmas
)


def indicator_name(
    data: pd.DataFrame, 
    period: int = 14, 
    price_col: str = "close"
) -> pd.DataFrame:
    """Compute the [Indicator Name] ([ABBR]) indicator.

    Detailed explanation of what the indicator does, how it is interpreted,
    and any specific logic used in this implementation.

    Calculation steps:
        1. [Step 1 description]
        2. [Step 2 description]
        3. ...

    Args:
        data: DataFrame containing the necessary market data (OHLCV).
        period: Lookback period or primary smoothing parameter (default: 14).
        price_col: Column name to use for calculations (default: "close").

    Returns:
        DataFrame with the new indicator column(s) appended.
        Example column name: `indicator_{period}`

    Raises:
        ValueError: If parameters are invalid or required columns are missing.
        TypeError: If input types are incorrect.
    """
    # 1. Validation
    require_dataframe(data)
    require_positive_int(period, name="period")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating [Indicator Name] with period={period} on column '{price_col}'")

    # 2. Extract series and prepare for calculation
    # Example: close = data[price_col]

    # 3. Core Calculation Logic
    # Replace this with the actual indicator formula
    # indicator_values = ...

    # 4. Finalize result
    result = data.copy()
    
    # Standard naming convention: {indicator}_{params}
    col_name = f"indicator_{period}"
    result[col_name] = 0.0 # Placeholder for actual values

    logger.success(f"[Indicator Name] calculation complete: {col_name}")
    return result
