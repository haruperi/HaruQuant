
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from apps.risk import allocator, governor, regime

@pytest.fixture
def mock_governor():
    gov = MagicMock(spec=governor.RiskGovernor)
    # Setup default returns for mocked methods
    gov._get_data.return_value = {}
    gov._build_returns_df.return_value = pd.DataFrame({
        "A": [0.01, -0.01],
        "B": [0.02, -0.02]
    })
    gov.effective_limits.return_value = MagicMock()
    gov._estimate_covariance.return_value = np.array([[0.01, 0.0], [0.0, 0.04]])
    gov._build_weights_from_positions.return_value = np.array([0.5, 0.5])
    gov._portfolio_correlation_map.return_value = {"A": 0.1, "B": 0.8}
    
    # Mock risk contributions for the iterative loop
    # Use itertools.cycle to avoid StopIteration
    from itertools import cycle
    gov._compute_risk_contributions_pct.side_effect = cycle([
        {"A": 0.5, "B": 0.5}  # Converged state
    ])
    return gov

@pytest.fixture
def alloc(mock_governor):
    return allocator.RiskBudgetAllocator(mock_governor)

def test_allocator_init(mock_governor):
    a = allocator.RiskBudgetAllocator(mock_governor)
    assert a.gov == mock_governor

def test_compute_target_lots(alloc):
    base_lots = {"A": 1.0, "B": 2.0}
    symbols = ["A", "B"]
    
    # Should run through optimization and return adjusted lots
    targets = alloc.compute_target_lots(symbols, base_lots)
    
    # Verify gov calls
    alloc.gov._get_data.assert_called()
    alloc.gov._build_returns_df.assert_called()
    assert len(targets) == 2
    assert "A" in targets
    assert "B" in targets

def test_compute_target_lots_empty_returns(alloc):
    alloc.gov._build_returns_df.return_value = pd.DataFrame()
    base_lots = {"A": 1.0}
    
    # Should return base lots immediately
    res = alloc.compute_target_lots(["A"], base_lots)
    assert res == base_lots

def test_lots_to_deltas(alloc):
    current = {"A": 1.0, "B": 1.0}
    target = {"A": 1.5, "B": 0.5}
    expected = {"A": 0.5, "B": -0.5}
    
    deltas = alloc.lots_to_deltas(current, target)
    assert deltas == expected

def test_apply_correlation_penalty(alloc):
    budgets = {"A": 0.5, "B": 0.5}
    # A low corr (0.1), B high corr (0.8)
    corr_map = {"A": 0.1, "B": 0.8}
    
    # Defaults: target_corr=0.5. A is fine. B is penalized.
    adj = alloc._apply_correlation_penalty(budgets, corr_map)
    
    # B should decrease relative to A
    assert adj["B"] < adj["A"]
    # Sum should still be 1.0 (normalized)
    assert pytest.approx(sum(adj.values())) == 1.0
