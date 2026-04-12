"""Live Trading Domain Models."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class SignalType(str, Enum):
    """Signal types."""

    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    CLOSE_BUY = "close buy"
    CLOSE_SELL = "close sell"


class Signal(BaseModel):
    """Standardized Trading Signal."""

    symbol: str
    timeframe: str
    signal_type: str  # buy, sell, etc.
    signal_time: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # Risk management fields
    risk_pips: Optional[float] = None
    risk_usd: Optional[float] = None
    position_size: Optional[float] = None
    reward_risk_ratio: Optional[float] = None

    class Config:
        """Pydantic config."""

        use_enum_values = True
