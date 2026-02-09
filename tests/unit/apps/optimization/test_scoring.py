from types import SimpleNamespace
import pytest
from apps.optimization.scoring import (
    sharpe_score,
    sortino_score,
    calmar_score,
    profit_factor_score,
    custom_score
)

@pytest.fixture
def mock_result():
    return SimpleNamespace(
        sharpe_ratio=2.0,
        sortino_ratio=3.0,
        calmar_ratio=1.5,
        profit_factor=1.8,
        total_return_pct=10.0,
        max_drawdown_pct=-5.0
    )

def test_sharpe_score(mock_result):
    assert sharpe_score(mock_result) == 2.0

def test_sortino_score(mock_result):
    assert sortino_score(mock_result) == 3.0

def test_calmar_score(mock_result):
    assert calmar_score(mock_result) == 1.5

def test_profit_factor_score(mock_result):
    assert profit_factor_score(mock_result) == 1.8
    
    mock_result.profit_factor = float("inf")
    assert profit_factor_score(mock_result) == 0.0

def test_custom_score(mock_result):
    # Score = (10.0/100)*0.3 + 2.0*0.4 - (5.0/100)*0.3
    #       = 0.03 + 0.8 - 0.015
    #       = 0.815
    score = custom_score(mock_result)
    assert abs(score - 0.815) < 1e-6
