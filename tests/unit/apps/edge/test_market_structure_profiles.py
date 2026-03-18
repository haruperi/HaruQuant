from __future__ import annotations

from apps.edge.market_structure_profiles import resolve_market_structure_profile


def test_market_structure_profile_resolves_major_fx_intraday_swing():
    profile = resolve_market_structure_profile("EURUSD", "H1")
    assert profile["symbol_class"] == "major_fx"
    assert profile["timeframe_bucket"] == "intraday_swing"
    assert profile["profile_key"] == "major_fx::intraday_swing"


def test_market_structure_profile_resolves_metal_fast_bucket():
    profile = resolve_market_structure_profile("XAUUSD", "M15")
    assert profile["symbol_class"] == "metals"
    assert profile["timeframe_bucket"] == "intraday_fast"
