from unittest.mock import MagicMock, patch
import pytest
from apps.optimization.methods.genetic import genetic_algorithm

class TestGeneticAlgorithm:
    def test_genetic_algorithm(self):
        strategy_class = MagicMock()
        data = MagicMock()
        data.name = "EURUSD"
        param_ranges = {"p": (1, 10)}
        
        with patch("apps.optimization.methods.genetic.TradeSimulator") as mock_sim_class, \
             patch("apps.simulation.utils.calculate_metrics_from_simulator") as mock_calc:
            
            mock_sim = mock_sim_class.return_value
            mock_result = MagicMock()
            mock_result.summary.return_value = {"sharpe": 1.0}
            mock_calc.return_value = mock_result
            
            summary = genetic_algorithm(
                strategy_class=strategy_class,
                data=data,
                param_ranges=param_ranges,
                population_size=4,
                generations=2,
                verbose=False
            )
            
            # 4 * 2 = 8 evaluations roughly (minus elites if optimized)
            assert summary.completed > 0
            assert len(summary.all_results) > 0
