
import pytest
import apps.indicator
import apps.indicator.custom
import apps.indicator.momentum
import apps.indicator.trend
import apps.indicator.volatility
import apps.indicator.volume

def test_indicator_exports():
    expected = [
        "rsi",
        "sma",
        "ema",
        "wma",
        "atr",
        "bbands",
        "accumulation_distribution",
        "logger",
    ]
    assert sorted(apps.indicator.__all__) == sorted(expected)

def test_custom_exports():
    expected = [
        "calculate_pair_strength",
        "calculate_currency_strength",
        "get_top_pairs",
        "currency_strength_indicator",
        "CURRENCY_PAIRS",
        "MAJOR_CURRENCIES",
    ]
    assert sorted(apps.indicator.custom.__all__) == sorted(expected)

def test_momentum_exports():
    expected = ["rsi", "logger"]
    assert sorted(apps.indicator.momentum.__all__) == sorted(expected)

def test_trend_exports():
    expected = ["sma", "ema", "wma", "logger"]
    assert sorted(apps.indicator.trend.__all__) == sorted(expected)

def test_volatility_exports():
    expected = ["atr", "bbands", "logger"]
    assert sorted(apps.indicator.volatility.__all__) == sorted(expected)

def test_volume_exports():
    expected = ["accumulation_distribution", "logger"]
    assert sorted(apps.indicator.volume.__all__) == sorted(expected)
