import pandas as pd
from typing import Dict, Any, Optional, Union
from haruquant.data import Data

class Strategy:
    """Wrapper for HaruQuant strategies to easily access signals."""
    
    def __init__(self, strategy_cls, params: Optional[Dict[str, Any]] = None):
        self.strategy_instance = strategy_cls(params or {})
        self.data: Optional[pd.DataFrame] = None
        
    def run(self, data: Union[pd.DataFrame, Data]) -> pd.DataFrame:
        """Run the strategy on the provided data."""
        if isinstance(data, Data):
            df = data.df
        else:
            df = data
            
        self.strategy_instance.on_init()
        self.data = self.strategy_instance.on_bar(df)
        return self.data
        
    @property
    def entries(self) -> pd.Series:
        """Returns the entry signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('entry_signal', pd.Series(0, index=self.data.index))
        
    @property
    def exits(self) -> pd.Series:
        """Returns the exit signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('exit_signal', pd.Series(0, index=self.data.index))
        
    @property
    def pendings(self) -> pd.Series:
        """Returns the pending signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('pending_signal', pd.Series(0, index=self.data.index))

# Import and expose specific strategies
from backend.data.strategies.trend_following import TrendFollowingStrategy as _TrendFollowingStrategy
from backend.data.strategies.breakout import BreakoutStrategy as _BreakoutStrategy
from backend.data.strategies.mean_reversion import MeanReversionStrategy as _MeanReversionStrategy
from backend.data.strategies.close_breakout import CloseBreakoutStrategy as _CloseBreakoutStrategy

class TrendFollowingStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_TrendFollowingStrategy, params)

class BreakoutStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_BreakoutStrategy, params)

class MeanReversionStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_MeanReversionStrategy, params)

class CloseBreakoutStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_CloseBreakoutStrategy, params)
