
import pytest
from apps.finance import (
    metrics,
    returns,
    drawdowns,
    ratios,
    risks,
    benchmark,
    distributions,
    efficiency,
    statistical_tests,
)

def test_finance_exports():
    """Verify that all submodules are exported correctly."""
    assert metrics is not None
    assert returns is not None
    assert drawdowns is not None
    assert ratios is not None
    assert risks is not None
    assert benchmark is not None
    assert distributions is not None
    assert efficiency is not None
    assert statistical_tests is not None

def test_all_variable():
    """Verify __all__ contains expected modules."""
    from apps.finance import __all__
    expected = [
        "metrics",
        "returns",
        "drawdowns",
        "ratios",
        "risks",
        "benchmark",
        "distributions",
        "efficiency",
        "statistical_tests",
    ]
    assert sorted(__all__) == sorted(expected)
