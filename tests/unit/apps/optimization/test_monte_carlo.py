import pytest
import numpy as np
from unittest.mock import MagicMock
from apps.optimization.monte_carlo import (
    monte_carlo_analysis,
    shuffle_trades_simulation,
    resample_returns_simulation,
    bootstrap_simulation,
    calculate_probability_of_ruin,
    calculate_confidence_intervals,
    MonteCarloResult,
    ParametricSimulationResult,
    parametric_simulation
)

class TestMonteCarlo:
    @pytest.fixture
    def mock_backtest_result(self):
        result = MagicMock()
        result.initial_balance = 10000.0
        result.total_return_pct = 10.0
        result.sharpe_ratio = 1.5
        result.max_drawdown_pct = -5.0
        
        # Mock trades dataframe
        trades_df = MagicMock()
        trades_df.empty = False
        trades_df.__len__.return_value = 100
        # Create a dataframe-like structure for profit_loss
        trades_df.__getitem__.return_value.values = np.random.normal(100, 50, 100)
        
        result.get_trades_df.return_value = trades_df
        return result

    def test_shuffle_trades_simulation(self, mock_backtest_result):
        mc_result = shuffle_trades_simulation(mock_backtest_result, num_simulations=10)
        assert isinstance(mc_result, MonteCarloResult)
        assert mc_result.simulation_type == "shuffle_trades"
        assert len(mc_result.final_balances) == 10

    def test_resample_returns_simulation(self, mock_backtest_result):
        mc_result = resample_returns_simulation(mock_backtest_result, num_simulations=10)
        assert isinstance(mc_result, MonteCarloResult)
        assert mc_result.simulation_type == "resample_returns"
        assert len(mc_result.final_balances) == 10

    def test_bootstrap_simulation(self, mock_backtest_result):
        mc_result = bootstrap_simulation(mock_backtest_result, num_simulations=10, block_size=5)
        assert isinstance(mc_result, MonteCarloResult)
        assert mc_result.simulation_type == "bootstrap"
        assert len(mc_result.final_balances) == 10

    def test_calculate_statistics(self):
        mc_result = MonteCarloResult(simulation_type="test", num_simulations=10)
        mc_result.total_returns = [10.0, 20.0, 30.0, 40.0, 50.0]
        mc_result.max_drawdowns = [5.0, 10.0, 15.0, 20.0, 25.0]
        
        mc_result.calculate_statistics()
        
        assert mc_result.mean_return == 30.0
        assert mc_result.median_return == 30.0
        assert mc_result.ci_95_lower < mc_result.ci_95_upper

    def test_monte_carlo_analysis_wrapper(self, mock_backtest_result):
        mc_result = monte_carlo_analysis(
            mock_backtest_result, 
            num_simulations=10, 
            simulation_type="shuffle_trades",
            random_seed=42
        )
        assert isinstance(mc_result, MonteCarloResult)
        assert mc_result.num_simulations == 10

    def test_calculate_probability_of_ruin(self, mock_backtest_result):
        prob = calculate_probability_of_ruin(
            mock_backtest_result,
            ruin_threshold_pct=50.0,
            num_simulations=10
        )
        assert 0.0 <= prob <= 100.0

    def test_calculate_confidence_intervals(self, mock_backtest_result):
        ci = calculate_confidence_intervals(
            mock_backtest_result,
            metric="total_return_pct",
            num_simulations=10
        )
        assert 90 in ci
        assert 95 in ci
        assert 99 in ci
        assert len(ci[95]) == 2

    def test_parametric_simulation(self):
        result = parametric_simulation(
            win_rate=0.5,
            reward_risk_ratio=2.0,
            risk_per_trade=0.01,
            num_trades=100,
            num_simulations=10,
            initial_balance=10000.0
        )
        assert isinstance(result, ParametricSimulationResult)
        assert result.num_simulations == 10
        assert len(result.final_balances) == 10
