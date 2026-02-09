
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from apps.finance import statistical_tests

class BacktestResult:
    pass

@pytest.fixture
def sample_result():
    # Mock BacktestResult
    result = MagicMock(spec=BacktestResult)
    result.strategy_name = "TestStrategy"
    result.sharpe_ratio = 1.5
    
    # Create sample equity df
    dates = pd.date_range("2023-01-01", periods=100)
    equity = 100 * (1 + 0.01 + np.random.normal(0, 0.02, 100)).cumprod()
    equity_df = pd.DataFrame({"equity": equity}, index=dates)
    
    result.get_equity_df.return_value = equity_df
    return result

@pytest.fixture
def benchmark_result():
    result = MagicMock(spec=BacktestResult)
    result.strategy_name = "Benchmark"
    result.sharpe_ratio = 0.5
    
    dates = pd.date_range("2023-01-01", periods=100)
    # Benchmark with lower return
    equity = 100 * (1 + 0.005 + np.random.normal(0, 0.02, 100)).cumprod()
    equity_df = pd.DataFrame({"equity": equity}, index=dates)
    
    result.get_equity_df.return_value = equity_df
    return result

def test_bootstrap_results_dataclass():
    res = statistical_tests.BootstrapResult(
        metric_name="Test",
        point_estimate=1.0,
        mean=1.0,
        median=1.0,
        std=0.1,
        ci_lower=0.8,
        ci_upper=1.2,
        confidence_level=0.95,
        n_bootstrap=100
    )
    assert "Test" in str(res)

def test_permutation_test(sample_result):
    # Should be significant as returns are positive on average
    res = statistical_tests.permutation_test(
        sample_result, n_permutations=50, seed=42
    )
    assert res.metric_name == "Sharpe Ratio"
    assert res.observed_value > 0
    # Significance might vary with random seed/data but structure checks are key
    assert 0 <= res.p_value <= 1.0

def test_permutation_test_insufficient_data():
    empty_result = MagicMock(spec=BacktestResult)
    empty_result.strategy_name = "Empty"
    empty_result.get_equity_df.return_value = pd.DataFrame()
    
    res = statistical_tests.permutation_test(empty_result)
    assert res.p_value == 1.0
    assert not res.is_significant

def test_whites_reality_check(sample_result, benchmark_result):
    # Test valid case
    res = statistical_tests.whites_reality_check(
        [sample_result], benchmark_result, n_bootstrap=50, seed=42
    )
    assert res.best_strategy_name == "TestStrategy"
    assert res.n_strategies == 1

def test_whites_reality_check_custom_metric(sample_result, benchmark_result):
    # Custom metric function
    def metric(r): return 10.0 # constant
    
    res = statistical_tests.whites_reality_check(
        [sample_result], benchmark_result, metric_func=metric, n_bootstrap=10
    )
    assert res.best_performance == 10.0

def test_bootstrap_confidence_intervals(sample_result):
    cis = statistical_tests.bootstrap_confidence_intervals(
        sample_result, n_bootstrap=50, seed=42
    )
    assert len(cis) > 0
    sharpe_ci = next(ci for ci in cis if ci.metric_name == "Sharpe Ratio")
    assert sharpe_ci.ci_lower < sharpe_ci.ci_upper

def test_deflated_sharpe_ratio():
    # Observed Sharpe 2.0, N=10 trials.
    dsr, p_val = statistical_tests.deflated_sharpe_ratio(
        observed_sharpe=2.0, n_trials=10, n_observations=100
    )
    assert 0 <= p_val <= 1.0
    # Should be less significant than raw Sharpe if n_trials was 1
    
    # Invalid input
    dsr0, p0 = statistical_tests.deflated_sharpe_ratio(2.0, 0, 100)
    assert p0 == 1.0

def test_stability_score():
    wf_results = [
        {"test_sharpe_ratio": 1.0, "train_sharpe_ratio": 1.1},
        {"test_sharpe_ratio": 0.9, "train_sharpe_ratio": 1.0},
        {"test_sharpe_ratio": 1.1, "train_sharpe_ratio": 1.2},
    ]
    score = statistical_tests.stability_score(wf_results, metric_key="sharpe_ratio")
    
    assert score["test_mean"] == pytest.approx(1.0)
    assert score["stability_ratio"] > 0
    assert score["degradation"] > 0 # Performance degraded slightly
    
    # Empty
    empty_score = statistical_tests.stability_score([])
    assert empty_score["test_mean"] == 0.0

def test_print_report(capsys, sample_result):
    # Just run to ensure no errors
    p_res = statistical_tests.permutation_test(sample_result, n_permutations=10)
    statistical_tests.print_statistical_validation_report(permutation_result=p_res)
    captured = capsys.readouterr()
    assert "STATISTICAL VALIDATION REPORT" in captured.out
    assert "PERMUTATION TEST" in captured.out
