import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from apps.optimization.parallel import (
    ProgressTracker,
    _run_backtest_worker,
    parallel_grid_search,
    parallel_random_search,
    parallel_walk_forward,
    analyze_parallel_results,
    analyze_walk_forward_results
)

class TestProgressTracker:
    def test_update(self):
        tracker = ProgressTracker(total=10)
        tracker.update(2)
        assert tracker.completed == 2
        tracker.update(1)
        assert tracker.completed == 3

class TestWorker:
    def test_run_backtest_worker_success(self):
        mock_result = MagicMock()
        mock_result.total_return_pct = 10.0
        mock_result.sharpe_ratio = 1.5
        mock_result.max_drawdown_pct = -5.0
        mock_result.total_trades = 20
        
        args = (lambda p: mock_result, {"p": 1}, 1)
        result = _run_backtest_worker(args)
        
        assert result["success"] is True
        assert result["total_return"] == 10.0
        assert result["params"] == {"p": 1}

    def test_run_backtest_worker_failure(self):
        def fail_factory(p):
            raise ValueError("Error")
            
        args = (fail_factory, {"p": 1}, 1)
        result = _run_backtest_worker(args)
        
        assert result["success"] is False
        assert result["error"] == "Error"

class TestParallelSearch:
    @patch("apps.optimization.parallel.ProcessPoolExecutor")
    def test_parallel_grid_search(self, mock_executor):
        # Mock executor to return immediately
        mock_future = MagicMock()
        mock_future.result.return_value = {
            "task_id": 0, "success": True, "total_return": 10.0, "params": {"p": 1}, "result": MagicMock()
        }
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        # We need to mock as_completed too
        with patch("apps.optimization.parallel.as_completed", return_value=[mock_future]):
            results = parallel_grid_search(
                lambda p: None,
                {"p": [1]},
                n_jobs=1,
                show_progress=False
            )
            
        assert len(results) == 1
        assert results[0]["total_return"] == 10.0

    @patch("apps.optimization.parallel.ProcessPoolExecutor")
    def test_parallel_random_search(self, mock_executor):
        mock_future = MagicMock()
        mock_future.result.return_value = {
            "task_id": 0, "success": True, "total_return": 5.0, "params": {"p": 1}, "result": MagicMock()
        }
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        with patch("apps.optimization.parallel.as_completed", return_value=[mock_future]):
            results = parallel_random_search(
                lambda p: None,
                {"p": lambda: 1},
                n_iter=1,
                n_jobs=1,
                show_progress=False
            )
            
        assert len(results) == 1

class TestAnalysis:
    def test_analyze_parallel_results(self):
        results = [
            {"task_id": 1, "success": True, "duration": 1.0, 
             "total_return": 10.0, "sharpe_ratio": 1.0, "max_drawdown": -5.0, 
             "total_trades": 10, "params": {"p": 1}},
            {"task_id": 2, "success": True, "duration": 1.0, 
             "total_return": 20.0, "sharpe_ratio": 2.0, "max_drawdown": -2.0, 
             "total_trades": 10, "params": {"p": 2}}
        ]
        df = analyze_parallel_results(results)
        assert len(df) == 2
        # Should be sorted by total_return desc for top entry
        assert df.iloc[0]["total_return"] == 20.0
        assert df.iloc[0]["param_p"] == 2

    def test_analyze_walk_forward_results(self):
        results = [
            {"train_return": 10.0, "test_return": 5.0},
            {"train_return": 20.0, "test_return": 10.0}
        ]
        analysis = analyze_walk_forward_results(results)
        assert analysis["num_windows"] == 2
        assert analysis["avg_train_return"] == 15.0
        assert analysis["avg_test_return"] == 7.5
        assert analysis["overfitting_assessment"] == "Moderate overfitting"
