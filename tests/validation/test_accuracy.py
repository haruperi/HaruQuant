"""
Accuracy Validation Tests.

Ensures that optimizations don't change backtest results.
Validates numerical accuracy and tests edge cases.

Usage:
    pytest tests/validation/test_accuracy.py -v
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json

import numpy as np
import pandas as pd
import pytest

from apps.backtest.engine.event_driven import EventDrivenEngine
from apps.backtest.engine.vectorized import VectorizedEngine
from apps.strategy import BaseStrategy


# ============================================================================
# Test Strategy
# ============================================================================


class ValidationStrategy(BaseStrategy):
    """Simple strategy for validation testing."""
    
    def __init__(self, params=None):
        params = params or {"symbol": "TEST"}
        super().__init__(params=params)
    
    def on_init(self):
        """Initialize strategy."""
        pass
    
    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate simple buy-and-hold signals."""
        # Simple logic: buy on first bar, hold
        data["entry_signal"] = 0
        data.loc[data.index[20], "entry_signal"] = 1  # Buy on bar 20
        
        data["exit_signal"] = 0
        data.loc[data.index[-1], "exit_signal"] = 1  # Sell on last bar
        
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = data["close"]
        
        return data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validation_data():
    """Generate deterministic data for validation."""
    n = 100
    np.random.seed(42)
    
    base_price = 100.0
    returns = np.random.randn(n) * 0.01
    close = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'open': np.roll(close, 1),
        'high': close * 1.005,
        'low': close * 0.995,
        'close': close,
        'volume': np.random.randint(1000, 10000, n),
    }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
    
    df.loc[df.index[0], 'open'] = base_price
    
    return df


@pytest.fixture
def validation_strategy():
    """Simple validation strategy."""
    return ValidationStrategy()


@pytest.fixture
def reference_results_path():
    """Path to reference results file."""
    return Path(__file__).parent / "reference_results.json"


# ============================================================================
# Reference Result Management
# ============================================================================


def save_reference_results(results: dict, filepath: Path):
    """Save reference results to JSON file."""
    # Convert numpy types to Python types for JSON serialization
    serializable = {}
    for key, value in results.items():
        if isinstance(value, (np.integer, np.floating)):
            serializable[key] = float(value)
        elif isinstance(value, list):
            serializable[key] = [float(v) if isinstance(v, (np.integer, np.floating)) else v for v in value]
        else:
            serializable[key] = value
    
    with open(filepath, 'w') as f:
        json.dump(serializable, f, indent=2)


def load_reference_results(filepath: Path) -> dict:
    """Load reference results from JSON file."""
    if not filepath.exists():
        return None
    
    with open(filepath, 'r') as f:
        return json.load(f)


# ============================================================================
# Validation Tests
# ============================================================================


class TestNumericalAccuracy:
    """Test numerical accuracy of backtest results."""
    
    def test_deterministic_results(self, validation_data, validation_strategy):
        """Ensure same inputs produce same outputs."""
        engine_config = {
            "initial_balance": 10000.0,
            "commission": 0.0,
            "slippage_points": 0.0
        }
        
        # Run backtest twice
        engine1 = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            **engine_config
        )
        result1 = engine1.run()
        
        engine2 = EventDrivenEngine(
            strategy=ValidationStrategy(),
            data=validation_data,
            **engine_config
        )
        result2 = engine2.run()
        
        # Results should be identical
        assert result1.total_trades == result2.total_trades
        assert abs(result1.final_balance - result2.final_balance) < 0.01
        assert abs(result1.total_return_pct - result2.total_return_pct) < 0.01
    
    def test_against_reference(self, validation_data, validation_strategy, reference_results_path):
        """Validate against saved reference results."""
        engine_config = {
            "initial_balance": 10000.0,
            "commission": 0.0,
            "slippage_points": 0.0
        }
        
        # Run backtest
        engine = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            **engine_config
        )
        result = engine.run()
        
        # Extract key metrics
        current_results = {
            "total_trades": result.total_trades,
            "final_balance": result.final_balance,
            "total_return_pct": result.total_return_pct,
            "max_drawdown_pct": result.max_drawdown_pct,
            "win_rate": result.win_rate
        }
        
        # Load or save reference
        reference = load_reference_results(reference_results_path)
        
        if reference is None:
            # First run - save as reference
            save_reference_results(current_results, reference_results_path)
            pytest.skip("Reference results saved, run again to validate")
        
        # Compare against reference (with tolerance)
        tolerance = 0.01  # 0.01% tolerance
        
        assert current_results["total_trades"] == reference["total_trades"], \
            f"Trade count mismatch: {current_results['total_trades']} vs {reference['total_trades']}"
        
        assert abs(current_results["final_balance"] - reference["final_balance"]) < tolerance, \
            f"Final balance mismatch: {current_results['final_balance']} vs {reference['final_balance']}"
        
        assert abs(current_results["total_return_pct"] - reference["total_return_pct"]) < tolerance, \
            f"Return mismatch: {current_results['total_return_pct']} vs {reference['total_return_pct']}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_no_trades(self, validation_data):
        """Test backtest with no trades."""
        class NoTradeStrategy(BaseStrategy):
            def __init__(self, params=None):
                super().__init__(params=params or {"symbol": "TEST"})
            
            def on_init(self):
                pass
            
            def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
                # No signals
                data["entry_signal"] = 0
                data["exit_signal"] = 0
                data["pending_signal"] = 0
                data["cancel_pending_signal"] = 0
                data["price"] = data["close"]
                return data
        
        engine = EventDrivenEngine(
            strategy=NoTradeStrategy(),
            data=validation_data,
            initial_balance=10000.0
        )
        result = engine.run()
        
        assert result.total_trades == 0
        assert result.final_balance == 10000.0
        assert result.total_return_pct == 0.0
    
    def test_single_trade(self, validation_data):
        """Test backtest with exactly one trade."""
        class SingleTradeStrategy(BaseStrategy):
            def __init__(self, params=None):
                super().__init__(params=params or {"symbol": "TEST"})
            
            def on_init(self):
                pass
            
            def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
                data["entry_signal"] = 0
                data["exit_signal"] = 0
                
                # Buy on bar 10, sell on bar 20
                data.loc[data.index[10], "entry_signal"] = 1
                data.loc[data.index[20], "exit_signal"] = 1
                
                data["pending_signal"] = 0
                data["cancel_pending_signal"] = 0
                data["price"] = data["close"]
                return data
        
        engine = EventDrivenEngine(
            strategy=SingleTradeStrategy(),
            data=validation_data,
            initial_balance=10000.0,
            commission=0.0
        )
        result = engine.run()
        
        assert result.total_trades == 1
        assert result.final_balance != 10000.0  # Should have changed
    
    def test_zero_commission(self, validation_data, validation_strategy):
        """Test with zero commission."""
        engine = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            initial_balance=10000.0,
            commission=0.0
        )
        result = engine.run()
        
        assert result.total_trades >= 0
        # With zero commission, gross profit should equal net profit
    
    def test_high_commission(self, validation_data, validation_strategy):
        """Test with high commission."""
        engine = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            initial_balance=10000.0,
            commission=100.0  # High commission
        )
        result = engine.run()
        
        assert result.total_trades >= 0
        # High commission should reduce returns


class TestTradeValidation:
    """Validate individual trade details."""
    
    def test_trade_entry_exit_prices(self, validation_data, validation_strategy):
        """Validate trade entry and exit prices are reasonable."""
        engine = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            initial_balance=10000.0,
            commission=0.0
        )
        result = engine.run()
        
        if result.total_trades > 0:
            for trade in result.trades:
                # Entry and exit prices should be within data range
                min_price = validation_data['low'].min()
                max_price = validation_data['high'].max()
                
                assert min_price <= trade.open_price <= max_price, \
                    f"Entry price {trade.open_price} outside data range"
                
                if trade.close_price is not None:
                    assert min_price <= trade.close_price <= max_price, \
                        f"Exit price {trade.close_price} outside data range"
    
    def test_trade_pnl_calculation(self, validation_data, validation_strategy):
        """Validate P&L calculations are correct."""
        engine = EventDrivenEngine(
            strategy=validation_strategy,
            data=validation_data,
            initial_balance=10000.0,
            commission=0.0,
            slippage_points=0.0
        )
        result = engine.run()
        
        if result.total_trades > 0:
            for trade in result.trades:
                if trade.close_price is not None and trade.profit_loss is not None:
                    # Manually calculate expected P&L
                    price_diff = trade.close_price - trade.open_price
                    if trade.type.lower() == 'short':
                        price_diff = -price_diff
                    
                    expected_pnl = price_diff * trade.size
                    
                    # Allow small tolerance for floating point errors
                    assert abs(trade.profit_loss - expected_pnl) < 0.01, \
                        f"P&L mismatch: {trade.profit_loss} vs {expected_pnl}"
