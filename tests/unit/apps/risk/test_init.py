
import pytest
from apps.risk import (
    RiskGovernor,
    RiskLimits,
    CorrelationPreference,
    RiskBudgetAllocator,
    RegimeState,
    RiskRegimeDetector,
    PositionSizer
)

def test_risk_exports():
    # Verify all key components are exported
    assert RiskGovernor
    assert RiskLimits
    assert CorrelationPreference
    assert RiskBudgetAllocator
    assert RegimeState
    assert RiskRegimeDetector
    assert PositionSizer
