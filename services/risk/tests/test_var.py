import pytest
from services.risk.calculations.var import historical_var, incremental_var


def test_historical_var():
    assert historical_var([0.01, -0.02, 0.003, -0.01]) > 0


def test_incremental_var():
    assert isinstance(incremental_var([0.01, -0.02], [0.001, -0.001]), float)


def test_missing_returns_rejection():
    with pytest.raises(ValueError):
        historical_var([])

