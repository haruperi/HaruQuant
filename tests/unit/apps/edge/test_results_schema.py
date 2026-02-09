"""Unit tests for apps.edge.results_schema module."""

import pytest
from datetime import datetime
from apps.edge.results_schema import TradeSample, EdgeStats, EdgeResult


# ==================== TradeSample Tests ====================

def test_trade_sample_creation():
    """Test TradeSample creation with all fields."""
    trade = TradeSample(
        entry_time="2024-01-01 10:00:00",
        exit_time="2024-01-01 12:00:00",
        side="BUY",
        entry_price=1.1000,
        exit_price=1.1050,
        r_multiple=1.5,
        mae_r=-0.3,
        mfe_r=2.0,
        hold_bars=8,
        meta={"session": "london"},
    )
    
    assert trade.side == "BUY"
    assert trade.entry_price == 1.1000
    assert trade.exit_price == 1.1050
    assert trade.r_multiple == 1.5
    assert trade.mae_r == -0.3
    assert trade.mfe_r == 2.0
    assert trade.hold_bars == 8
    assert trade.meta == {"session": "london"}


def test_trade_sample_no_meta():
    """Test TradeSample without meta field."""
    trade = TradeSample(
        entry_time="2024-01-01",
        exit_time="2024-01-02",
        side="SELL",
        entry_price=1.2000,
        exit_price=1.1950,
        r_multiple=0.8,
        mae_r=-0.5,
        mfe_r=1.2,
        hold_bars=16,
    )
    
    assert trade.meta is None


def test_trade_sample_to_dict():
    """Test TradeSample to_dict serialization."""
    trade = TradeSample(
        entry_time="2024-01-01",
        exit_time="2024-01-02",
        side="BUY",
        entry_price=1.1000,
        exit_price=1.1050,
        r_multiple=1.5,
        mae_r=-0.3,
        mfe_r=2.0,
        hold_bars=8,
        meta={"test": "value"},
    )
    
    d = trade.to_dict()
    
    assert d["entry_time"] == "2024-01-01"
    assert d["exit_time"] == "2024-01-02"
    assert d["side"] == "BUY"
    assert d["entry_price"] == 1.1000
    assert d["exit_price"] == 1.1050
    assert d["r_multiple"] == 1.5
    assert d["mae_r"] == -0.3
    assert d["mfe_r"] == 2.0
    assert d["hold_bars"] == 8
    assert d["meta"] == {"test": "value"}


# ==================== EdgeStats Tests ====================

def test_edge_stats_creation():
    """Test EdgeStats creation with all fields."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.15,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.08,
        ci_high=0.22,
        p_value_perm=0.02,
        extras={"sqn": 2.5},
    )
    
    assert stats.n_trades == 100
    assert stats.expectancy_r == 0.15
    assert stats.win_rate == 0.55
    assert stats.profit_factor == 1.8
    assert stats.median_mae_r == -0.4
    assert stats.median_mfe_r == 1.2
    assert stats.avg_hold_bars == 12.5
    assert stats.ci_low == 0.08
    assert stats.ci_high == 0.22
    assert stats.p_value_perm == 0.02
    assert stats.extras == {"sqn": 2.5}


def test_edge_stats_no_extras():
    """Test EdgeStats without extras field."""
    stats = EdgeStats(
        n_trades=50,
        expectancy_r=0.10,
        win_rate=0.50,
        profit_factor=1.5,
        median_mae_r=-0.3,
        median_mfe_r=1.0,
        avg_hold_bars=10.0,
        ci_low=0.05,
        ci_high=0.15,
        p_value_perm=0.03,
    )
    
    assert stats.extras is None


def test_edge_stats_to_dict():
    """Test EdgeStats to_dict serialization."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.15,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.08,
        ci_high=0.22,
        p_value_perm=0.02,
        extras={"test": "value"},
    )
    
    d = stats.to_dict()
    
    assert d["n_trades"] == 100
    assert d["expectancy_r"] == 0.15
    assert d["win_rate"] == 0.55
    assert d["profit_factor"] == 1.8
    assert d["median_mae_r"] == -0.4
    assert d["median_mfe_r"] == 1.2
    assert d["avg_hold_bars"] == 12.5
    assert d["ci_low"] == 0.08
    assert d["ci_high"] == 0.22
    assert d["p_value_perm"] == 0.02
    assert d["extras"] == {"test": "value"}


def test_edge_stats_edge_confirmed_true():
    """Test edge_confirmed property when edge is confirmed."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.15,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.08,  # > 0
        ci_high=0.22,
        p_value_perm=0.02,  # < 0.05
    )
    
    assert stats.edge_confirmed is True


def test_edge_stats_edge_confirmed_false_ci():
    """Test edge_confirmed property when CI lower bound <= 0."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.05,
        win_rate=0.52,
        profit_factor=1.3,
        median_mae_r=-0.4,
        median_mfe_r=1.0,
        avg_hold_bars=12.0,
        ci_low=-0.02,  # <= 0
        ci_high=0.12,
        p_value_perm=0.02,
    )
    
    assert stats.edge_confirmed is False


def test_edge_stats_edge_confirmed_false_pvalue():
    """Test edge_confirmed property when p-value >= 0.05."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.10,
        win_rate=0.53,
        profit_factor=1.5,
        median_mae_r=-0.3,
        median_mfe_r=1.1,
        avg_hold_bars=11.0,
        ci_low=0.05,
        ci_high=0.15,
        p_value_perm=0.08,  # >= 0.05
    )
    
    assert stats.edge_confirmed is False


def test_edge_stats_verdict_edge_confirmed():
    """Test verdict property for confirmed edge."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.15,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.08,
        ci_high=0.22,
        p_value_perm=0.02,
    )
    
    assert stats.verdict == "EDGE_CONFIRMED"


def test_edge_stats_verdict_insufficient_data():
    """Test verdict property for insufficient data."""
    stats = EdgeStats(
        n_trades=25,  # < 30
        expectancy_r=0.20,
        win_rate=0.60,
        profit_factor=2.0,
        median_mae_r=-0.3,
        median_mfe_r=1.5,
        avg_hold_bars=10.0,
        ci_low=0.10,
        ci_high=0.30,
        p_value_perm=0.01,
    )
    
    assert stats.verdict == "INSUFFICIENT_DATA"


def test_edge_stats_verdict_potential_edge():
    """Test verdict property for potential edge (CI > 0 but p >= 0.05)."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.10,
        win_rate=0.53,
        profit_factor=1.5,
        median_mae_r=-0.3,
        median_mfe_r=1.1,
        avg_hold_bars=11.0,
        ci_low=0.05,  # > 0
        ci_high=0.15,
        p_value_perm=0.08,  # >= 0.05
    )
    
    assert stats.verdict == "POTENTIAL_EDGE"


def test_edge_stats_verdict_weak_signal():
    """Test verdict property for weak signal (expectancy > 0 but CI <= 0)."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.05,  # > 0
        win_rate=0.52,
        profit_factor=1.3,
        median_mae_r=-0.4,
        median_mfe_r=1.0,
        avg_hold_bars=12.0,
        ci_low=-0.02,  # <= 0
        ci_high=0.12,
        p_value_perm=0.10,
    )
    
    assert stats.verdict == "WEAK_SIGNAL"


def test_edge_stats_verdict_no_edge():
    """Test verdict property for no edge (expectancy <= 0)."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=-0.05,  # <= 0
        win_rate=0.45,
        profit_factor=0.8,
        median_mae_r=-0.5,
        median_mfe_r=0.8,
        avg_hold_bars=12.0,
        ci_low=-0.15,
        ci_high=0.05,
        p_value_perm=0.50,
    )
    
    assert stats.verdict == "NO_EDGE"


# ==================== EdgeResult Tests ====================

def test_edge_result_creation():
    """Test EdgeResult creation with all fields."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.15,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.08,
        ci_high=0.22,
        p_value_perm=0.02,
    )
    
    trade = TradeSample(
        entry_time="2024-01-01",
        exit_time="2024-01-02",
        side="BUY",
        entry_price=1.1000,
        exit_price=1.1050,
        r_multiple=1.5,
        mae_r=-0.3,
        mfe_r=2.0,
        hold_bars=8,
    )
    
    result = EdgeResult(
        symbol="EURUSD",
        timeframe="H1",
        eds_name="EDS-1: Mean Reversion",
        config={"z_entry": 2.0},
        stats=stats,
        trades=[trade],
        timestamp="2024-01-01T00:00:00",
    )
    
    assert result.symbol == "EURUSD"
    assert result.timeframe == "H1"
    assert result.eds_name == "EDS-1: Mean Reversion"
    assert result.config == {"z_entry": 2.0}
    assert result.stats == stats
    assert len(result.trades) == 1
    assert result.timestamp == "2024-01-01T00:00:00"


def test_edge_result_empty_trades():
    """Test EdgeResult with empty trades list."""
    stats = EdgeStats(
        n_trades=0,
        expectancy_r=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        median_mae_r=0.0,
        median_mfe_r=0.0,
        avg_hold_bars=0.0,
        ci_low=0.0,
        ci_high=0.0,
        p_value_perm=1.0,
    )
    
    result = EdgeResult(
        symbol="GBPUSD",
        timeframe="M15",
        eds_name="EDS-0: Null Model",
        config={},
        stats=stats,
    )
    
    assert len(result.trades) == 0


def test_edge_result_to_dict():
    """Test EdgeResult to_dict serialization."""
    stats = EdgeStats(
        n_trades=1,
        expectancy_r=0.15,
        win_rate=1.0,
        profit_factor=1.0,
        median_mae_r=-0.3,
        median_mfe_r=2.0,
        avg_hold_bars=8.0,
        ci_low=0.08,
        ci_high=0.22,
        p_value_perm=0.02,
    )
    
    trade = TradeSample(
        entry_time="2024-01-01",
        exit_time="2024-01-02",
        side="BUY",
        entry_price=1.1000,
        exit_price=1.1050,
        r_multiple=1.5,
        mae_r=-0.3,
        mfe_r=2.0,
        hold_bars=8,
    )
    
    result = EdgeResult(
        symbol="EURUSD",
        timeframe="H1",
        eds_name="Test EDS",
        config={"test": "value"},
        stats=stats,
        trades=[trade],
        timestamp="2024-01-01T00:00:00",
    )
    
    d = result.to_dict()
    
    assert d["symbol"] == "EURUSD"
    assert d["timeframe"] == "H1"
    assert d["eds_name"] == "Test EDS"
    assert d["config"] == {"test": "value"}
    assert isinstance(d["stats"], dict)
    assert d["stats"]["n_trades"] == 1
    assert isinstance(d["trades"], list)
    assert len(d["trades"]) == 1
    assert d["trades"][0]["side"] == "BUY"
    assert d["timestamp"] == "2024-01-01T00:00:00"


def test_edge_result_from_dict():
    """Test EdgeResult from_dict deserialization."""
    data = {
        "symbol": "EURUSD",
        "timeframe": "H1",
        "eds_name": "Test EDS",
        "config": {"test": "value"},
        "stats": {
            "n_trades": 1,
            "expectancy_r": 0.15,
            "win_rate": 1.0,
            "profit_factor": 1.0,
            "median_mae_r": -0.3,
            "median_mfe_r": 2.0,
            "avg_hold_bars": 8.0,
            "ci_low": 0.08,
            "ci_high": 0.22,
            "p_value_perm": 0.02,
            "extras": {"sqn": 2.5},
        },
        "trades": [
            {
                "entry_time": "2024-01-01",
                "exit_time": "2024-01-02",
                "side": "BUY",
                "entry_price": 1.1000,
                "exit_price": 1.1050,
                "r_multiple": 1.5,
                "mae_r": -0.3,
                "mfe_r": 2.0,
                "hold_bars": 8,
                "meta": {"session": "london"},
            }
        ],
        "timestamp": "2024-01-01T00:00:00",
    }
    
    result = EdgeResult.from_dict(data)
    
    assert result.symbol == "EURUSD"
    assert result.timeframe == "H1"
    assert result.eds_name == "Test EDS"
    assert result.config == {"test": "value"}
    assert result.stats.n_trades == 1
    assert result.stats.expectancy_r == 0.15
    assert result.stats.extras == {"sqn": 2.5}
    assert len(result.trades) == 1
    assert result.trades[0].side == "BUY"
    assert result.trades[0].meta == {"session": "london"}
    assert result.timestamp == "2024-01-01T00:00:00"


def test_edge_result_from_dict_no_trades():
    """Test EdgeResult from_dict with no trades."""
    data = {
        "symbol": "GBPUSD",
        "timeframe": "M15",
        "eds_name": "Test EDS",
        "config": {},
        "stats": {
            "n_trades": 0,
            "expectancy_r": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "median_mae_r": 0.0,
            "median_mfe_r": 0.0,
            "avg_hold_bars": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "p_value_perm": 1.0,
        },
    }
    
    result = EdgeResult.from_dict(data)
    
    assert len(result.trades) == 0
    assert result.stats.n_trades == 0


def test_edge_result_summary():
    """Test EdgeResult summary string generation."""
    stats = EdgeStats(
        n_trades=100,
        expectancy_r=0.1523,
        win_rate=0.55,
        profit_factor=1.8,
        median_mae_r=-0.4,
        median_mfe_r=1.2,
        avg_hold_bars=12.5,
        ci_low=0.0812,
        ci_high=0.2234,
        p_value_perm=0.0234,
    )
    
    result = EdgeResult(
        symbol="EURUSD",
        timeframe="H1",
        eds_name="EDS-1: Mean Reversion",
        config={},
        stats=stats,
    )
    
    summary = result.summary()
    
    assert "EDS-1: Mean Reversion" in summary
    assert "EURUSD" in summary
    assert "H1" in summary
    assert "Trades: 100" in summary
    assert "0.1523" in summary
    assert "0.0812" in summary
    assert "0.2234" in summary
    assert "0.0234" in summary
    assert "EDGE_CONFIRMED" in summary


def test_edge_result_round_trip():
    """Test EdgeResult serialization and deserialization round trip."""
    stats = EdgeStats(
        n_trades=50,
        expectancy_r=0.12,
        win_rate=0.54,
        profit_factor=1.6,
        median_mae_r=-0.35,
        median_mfe_r=1.1,
        avg_hold_bars=11.0,
        ci_low=0.06,
        ci_high=0.18,
        p_value_perm=0.03,
        extras={"test": "data"},
    )
    
    trade1 = TradeSample(
        entry_time="2024-01-01",
        exit_time="2024-01-02",
        side="BUY",
        entry_price=1.1000,
        exit_price=1.1050,
        r_multiple=1.5,
        mae_r=-0.3,
        mfe_r=2.0,
        hold_bars=8,
        meta={"session": "london"},
    )
    
    trade2 = TradeSample(
        entry_time="2024-01-03",
        exit_time="2024-01-04",
        side="SELL",
        entry_price=1.2000,
        exit_price=1.1950,
        r_multiple=0.8,
        mae_r=-0.4,
        mfe_r=1.2,
        hold_bars=12,
    )
    
    original = EdgeResult(
        symbol="EURUSD",
        timeframe="H1",
        eds_name="Test EDS",
        config={"param": 123},
        stats=stats,
        trades=[trade1, trade2],
        timestamp="2024-01-01T00:00:00",
    )
    
    # Serialize and deserialize
    data = original.to_dict()
    restored = EdgeResult.from_dict(data)
    
    # Verify all fields match
    assert restored.symbol == original.symbol
    assert restored.timeframe == original.timeframe
    assert restored.eds_name == original.eds_name
    assert restored.config == original.config
    assert restored.stats.n_trades == original.stats.n_trades
    assert restored.stats.expectancy_r == original.stats.expectancy_r
    assert restored.stats.extras == original.stats.extras
    assert len(restored.trades) == len(original.trades)
    assert restored.trades[0].side == original.trades[0].side
    assert restored.trades[0].meta == original.trades[0].meta
    assert restored.trades[1].meta is None
    assert restored.timestamp == original.timestamp
