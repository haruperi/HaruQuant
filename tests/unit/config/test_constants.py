"""
Tests for the constants module.
"""

import os
from pathlib import Path
import pytest
from app.config.constants import (
    PROJECT_ROOT,
    DATA_DIR,
    LOGS_DIR,
    HISTORICAL_DATA_DIR,
    BACKTEST_RESULTS_DIR,
    OPTIMIZATION_RESULTS_DIR,
    TIMEFRAME_MAP
)

def test_project_paths():
    """Test that project paths are correctly resolved."""
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.is_dir()
    assert DATA_DIR.parent == PROJECT_ROOT
    assert LOGS_DIR.parent == PROJECT_ROOT
    assert HISTORICAL_DATA_DIR.parent == DATA_DIR
    assert BACKTEST_RESULTS_DIR.parent == DATA_DIR
    assert OPTIMIZATION_RESULTS_DIR.parent == DATA_DIR

def test_timeframe_map():
    """Test that timeframe map contains valid values."""
    assert "M1" in TIMEFRAME_MAP
    assert "M5" in TIMEFRAME_MAP
    assert "H1" in TIMEFRAME_MAP
    assert "D1" in TIMEFRAME_MAP
    assert TIMEFRAME_MAP["M1"] == 1
    assert TIMEFRAME_MAP["H1"] == 60
    assert TIMEFRAME_MAP["D1"] == 1440

def test_trading_parameters():
    """Test that trading parameters have valid ranges."""
    from app.config.constants import (
        MAX_SLIPPAGE_POINTS,
        MAX_SPREAD_POINTS,
        MAX_VOLUME,
        MIN_VOLUME,
        VOLUME_STEP
    )
    assert MAX_SLIPPAGE_POINTS > 0
    assert MAX_SPREAD_POINTS > 0
    assert MAX_VOLUME > MIN_VOLUME
    assert VOLUME_STEP > 0
    assert MIN_VOLUME > 0 