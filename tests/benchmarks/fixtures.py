"""
Benchmark Fixtures.

Provides shared fixtures for benchmark tests including:
- Standardized datasets (1K, 10K, 100K, 1M bars)
- Simple and complex strategies
- Reusable test configurations
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import pytest

from apps.strategy import BaseStrategy


# ============================================================================
# Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def sample_data_1k():
    """Generate 1,000 bars of random OHLCV data."""
    n = 1000
    np.random.seed(42)  # For reproducibility
    
    base_price = 100.0
    returns = np.random.randn(n) * 0.01  # 1% volatility
    close = base_price * (1 + returns).cumprod()
    
    # Generate OHLC from close
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    open_price = np.roll(close, 1)
    open_price[0] = base_price
    
    volume = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
    
    return df


@pytest.fixture(scope="session")
def sample_data_10k():
    """Generate 10,000 bars of random OHLCV data."""
    n = 10000
    np.random.seed(42)
    
    base_price = 100.0
    returns = np.random.randn(n) * 0.01
    close = base_price * (1 + returns).cumprod()
    
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    open_price = np.roll(close, 1)
    open_price[0] = base_price
    
    volume = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
    
    return df


@pytest.fixture(scope="session")
def sample_data_100k():
    """Generate 100,000 bars of random OHLCV data."""
    n = 100000
    np.random.seed(42)
    
    base_price = 100.0
    returns = np.random.randn(n) * 0.01
    close = base_price * (1 + returns).cumprod()
    
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    open_price = np.roll(close, 1)
    open_price[0] = base_price
    
    volume = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
    
    return df


@pytest.fixture(scope="session")
def sample_data_1m():
    """Generate 1,000,000 bars of random OHLCV data."""
    n = 1000000
    np.random.seed(42)
    
    base_price = 100.0
    returns = np.random.randn(n) * 0.01
    close = base_price * (1 + returns).cumprod()
    
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    open_price = np.roll(close, 1)
    open_price[0] = base_price
    
    volume = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
    
    return df


# ============================================================================
# Strategy Fixtures
# ============================================================================


class SimpleMAStrategy(BaseStrategy):
    """Simple moving average crossover strategy for benchmarking."""
    
    def __init__(self, params=None):
        params = params or {"symbol": "TEST", "fast_period": 10, "slow_period": 20}
        super().__init__(params=params)
        self.fast_period = self.params.get("fast_period", 10)
        self.slow_period = self.params.get("slow_period", 20)
    
    def on_init(self):
        """Initialize strategy."""
        pass
    
    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals."""
        # Calculate MAs
        data["fast_ma"] = data["close"].rolling(window=self.fast_period).mean()
        data["slow_ma"] = data["close"].rolling(window=self.slow_period).mean()
        
        # Generate signals
        data["entry_long"] = (data["fast_ma"] > data["slow_ma"]) & (
            data["fast_ma"].shift(1) <= data["slow_ma"].shift(1)
        )
        data["entry_short"] = (data["fast_ma"] < data["slow_ma"]) & (
            data["fast_ma"].shift(1) >= data["slow_ma"].shift(1)
        )
        
        # Build signal columns
        data["entry_signal"] = 0
        data.loc[data["entry_long"], "entry_signal"] = 1
        data.loc[data["entry_short"], "entry_signal"] = -1
        
        data["exit_signal"] = 0
        data.loc[data["entry_short"], "exit_signal"] = 1
        data.loc[data["entry_long"], "exit_signal"] = -1
        
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = data["close"]
        
        return data


class ComplexStrategy(BaseStrategy):
    """Complex multi-indicator strategy for benchmarking."""
    
    def __init__(self, params=None):
        params = params or {
            "symbol": "TEST",
            "fast_ma": 10,
            "slow_ma": 20,
            "rsi_period": 14,
            "bb_period": 20
        }
        super().__init__(params=params)
        self.fast_ma = self.params.get("fast_ma", 10)
        self.slow_ma = self.params.get("slow_ma", 20)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.bb_period = self.params.get("bb_period", 20)
    
    def on_init(self):
        """Initialize strategy."""
        pass
    
    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate signals with multiple indicators."""
        # Moving averages
        data["fast_ma"] = data["close"].rolling(window=self.fast_ma).mean()
        data["slow_ma"] = data["close"].rolling(window=self.slow_ma).mean()
        
        # RSI
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        data["rsi"] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        data["bb_middle"] = data["close"].rolling(window=self.bb_period).mean()
        data["bb_std"] = data["close"].rolling(window=self.bb_period).std()
        data["bb_upper"] = data["bb_middle"] + (data["bb_std"] * 2)
        data["bb_lower"] = data["bb_middle"] - (data["bb_std"] * 2)
        
        # Complex entry logic
        data["entry_long"] = (
            (data["fast_ma"] > data["slow_ma"]) &
            (data["rsi"] < 30) &
            (data["close"] < data["bb_lower"])
        )
        
        data["entry_short"] = (
            (data["fast_ma"] < data["slow_ma"]) &
            (data["rsi"] > 70) &
            (data["close"] > data["bb_upper"])
        )
        
        # Build signal columns
        data["entry_signal"] = 0
        data.loc[data["entry_long"], "entry_signal"] = 1
        data.loc[data["entry_short"], "entry_signal"] = -1
        
        data["exit_signal"] = 0
        data.loc[data["entry_short"], "exit_signal"] = 1
        data.loc[data["entry_long"], "exit_signal"] = -1
        
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = data["close"]
        
        return data


@pytest.fixture
def simple_strategy():
    """Simple MA crossover strategy."""
    return SimpleMAStrategy()


@pytest.fixture
def complex_strategy():
    """Complex multi-indicator strategy."""
    return ComplexStrategy()


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def engine_config_minimal():
    """Minimal engine configuration."""
    return {
        "initial_balance": 10000.0,
        "commission": 0.0,
        "slippage_points": 0.0
    }


@pytest.fixture
def engine_config_realistic():
    """Realistic engine configuration with costs."""
    return {
        "initial_balance": 10000.0,
        "commission": 7.0,
        "slippage_points": 0.0001
    }
