from unittest.mock import MagicMock, patch
import pytest
from apps.optimization.methods.random_search import random_search, _run_single_random_backtest
from apps.optimization.result import OptimizationResult

class TestRandomSearch:
    def test_random_search_sequential(self):
        strategy_class = MagicMock()
        data = MagicMock()
        data.name = "EURUSD"
        param_distributions = {"p": (1, 10)}
        
        with patch("apps.optimization.methods.random_search.TradeSimulator") as mock_sim_class, \
             patch("apps.simulation.utils.calculate_metrics_from_simulator") as mock_calc:
            
            mock_sim = mock_sim_class.return_value
            mock_result = MagicMock()
            mock_result.summary.return_value = {"sharpe": 1.0}
            mock_calc.return_value = mock_result
            
            summary = random_search(
                strategy_class=strategy_class,
                data=data,
                param_distributions=param_distributions,
                n_iter=5,
                initial_balance=10000,
                scoring_func=lambda x: 1.0,
                verbose=False
            )
            
            assert summary.total_combinations == 5
            assert summary.completed == 5
            assert len(summary.all_results) == 5
