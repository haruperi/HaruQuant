from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import pandas as pd
from apps.optimization.result import OptimizationResult, OptimizationSummary

class TestOptimizationResult:
    def test_result_init(self):
        params = {"a": 1, "b": 2}
        result_mock = MagicMock()
        metrics = {"sharpe_ratio": 2.5}
        
        opt_res = OptimizationResult(
            parameters=params,
            result=result_mock,
            metrics=metrics,
            score=2.5,
            rank=1
        )
        
        assert opt_res.parameters == params
        assert opt_res.score == 2.5
        assert repr(opt_res) == "OptimizationResult(score=2.5000, rank=1, params={'a': 1, 'b': 2})"

class TestOptimizationSummary:
    @pytest.fixture
    def summary(self):
        results = [
            OptimizationResult({"p": 1}, MagicMock(), {"m": 1}, score=1.0, rank=3),
            OptimizationResult({"p": 2}, MagicMock(), {"m": 2}, score=2.0, rank=1),
            OptimizationResult({"p": 3}, MagicMock(), {"m": 3}, score=1.5, rank=2),
        ]
        return OptimizationSummary(
            best_params={"p": 2},
            best_score=2.0,
            best_result=results[1].result,
            all_results=results,
            total_combinations=3,
            completed=3
        )

    def test_get_top_n(self, summary):
        top = summary.get_top_n(2)
        assert len(top) == 2
        assert top[0].score == 2.0
        assert top[1].score == 1.5

    def test_to_dataframe(self, summary):
        df = summary.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "score" in df.columns
        assert "rank" in df.columns
        assert "p" in df.columns
        # Check sort order not guaranteed by to_dataframe, but content match
        assert df.loc[df["score"] == 2.0, "rank"].values[0] == 1
