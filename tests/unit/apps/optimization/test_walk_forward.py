from unittest.mock import MagicMock, patch, ANY
import pytest
import pandas as pd
import numpy as np
from apps.optimization.walk_forward import walk_forward

class TestWalkForward:
    @pytest.fixture
    def mock_data(self):
        # Create a dummy dataframe with enough rows
        dates = pd.date_range(start="2023-01-01", periods=500, freq="D")
        df = pd.DataFrame({
            "open": np.random.rand(500),
            "high": np.random.rand(500),
            "low": np.random.rand(500),
            "close": np.random.rand(500),
            "volume": np.random.rand(500)
        }, index=dates)
        df.name = "EURUSD"
        return df

    @patch("apps.optimization.walk_forward.grid_search")
    @patch("apps.optimization.walk_forward.TradeSimulator")
    @patch("apps.optimization.walk_forward.calculate_metrics_from_simulator")
    def test_walk_forward_optimization(self, mock_calc, mock_sim_class, mock_grid, mock_data):
        # Setup mocks
        mock_train_summary = MagicMock()
        mock_train_summary.best_params = {"p": 1}
        mock_train_summary.best_score = 1.0
        mock_grid.return_value = mock_train_summary
        
        mock_sim = mock_sim_class.return_value
        mock_test_result = MagicMock()
        mock_test_result.total_return_pct = 5.0
        mock_calc.return_value = mock_test_result
        
        strategy_class = MagicMock()
        
        summary = walk_forward(
            strategy_class=strategy_class,
            data=mock_data,
            param_grid={"p": [1, 2]},
            train_period=100,
            test_period=20,
            verbose=False
        )
        
        assert "windows" in summary
        assert len(summary["windows"]) > 0
        assert summary["avg_test_return"] == 5.0
        
        # Verify grid_search was called for optimization
        mock_grid.assert_called()

    @patch("apps.optimization.walk_forward.TradeSimulator")
    @patch("apps.optimization.walk_forward.calculate_metrics_from_simulator")
    def test_walk_forward_no_optimization(self, mock_calc, mock_sim_class, mock_data):
        mock_sim = mock_sim_class.return_value
        
        mock_result = MagicMock()
        mock_result.total_return_pct = 5.0
        mock_calc.return_value = mock_result
        
        strategy_class = MagicMock()
        
        summary = walk_forward(
            strategy_class=strategy_class,
            data=mock_data,
            param_grid={},  # Empty grid = no optimization
            train_period=100,
            test_period=20,
            verbose=False
        )
        
        assert "windows" in summary
        assert len(summary["windows"]) > 0
