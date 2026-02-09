from unittest.mock import MagicMock, patch
import pytest
from apps.optimization.methods.grid_search import grid_search, _run_single_backtest
from apps.optimization.result import OptimizationResult

class TestGridSearch:
    @patch("apps.optimization.methods.grid_search.TradeSimulator")
    def test_run_single_backtest(self, mock_simulator_class):
        mock_sim = mock_simulator_class.return_value
        mock_sim.summary.return_value = {"sharpe": 1.0}
        
        # Mock calculate metrics
        mock_result = MagicMock()
        mock_result.summary.return_value = {"sharpe": 1.0}
        
        with patch("apps.simulation.utils.calculate_metrics_from_simulator", return_value=mock_result):
            args = (("path", "Class"), None, "EURUSD", {"p": 1}, 10000, "vectorised", lambda x: 1.0)
            
            with patch("apps.optimization.methods.grid_search._load_strategy_from_path") as mock_load:
                mock_load.return_value = MagicMock()
                
                params, result, error = _run_single_backtest(args)
                
                assert params == {"p": 1}
                assert isinstance(result, OptimizationResult)
                assert result.score == 1.0
                assert error is None

    def test_grid_search_sequential(self):
        strategy_class = MagicMock()
        data = MagicMock()
        data.name = "EURUSD"
        param_grid = {"p": [1, 2]}
        
        # Mock TradeSimulator and calculate_metrics
        with patch("apps.optimization.methods.grid_search.TradeSimulator") as mock_sim_class, \
             patch("apps.simulation.utils.calculate_metrics_from_simulator") as mock_calc:
            
            mock_sim = mock_sim_class.return_value
            mock_result = MagicMock()
            mock_result.summary.return_value = {"sharpe": 1.0}
            mock_calc.return_value = mock_result
            
            summary = grid_search(
                strategy_class=strategy_class,
                data=data,
                param_grid=param_grid,
                initial_balance=10000,
                scoring_func=lambda x: 1.0,  # Fixed score
                verbose=False
            )
            
            assert summary.total_combinations == 2
            assert summary.completed == 2
            assert len(summary.all_results) == 2
