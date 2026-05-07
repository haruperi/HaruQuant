import pytest
from services.risk.calculations.cvar import historical_cvar, incremental_cvar


def test_cvar_calculation():
    assert historical_cvar([0.01, -0.02, 0.003, -0.01]) > 0


def test_incremental_cvar():
    assert isinstance(incremental_cvar([0.01, -0.02], [0.001, -0.001]), float)


def test_missing_returns_rejection():
    with pytest.raises(ValueError):
        historical_cvar([])

