"""Unit tests for apps.edge.config module."""

import pytest
from apps.edge.config import (
    DataConfig,
    SessionConfig,
    BootstrapConfig,
    PermutationConfig,
    NullModelsConfig,
    MeanReversionConfig,
    TrendPersistenceConfig,
    SessionEdgeConfig,
    EdgeLabConfig,
    create_config,
)


# ==================== DataConfig Tests ====================

def test_data_config_defaults():
    """Test DataConfig with default values."""
    cfg = DataConfig(symbol="EURUSD")
    assert cfg.symbol == "EURUSD"
    assert cfg.timeframe == "M15"
    assert cfg.start_pos == 0
    assert cfg.end_pos == 5000
    assert cfg.exclude_last_bar is True
    assert cfg.tz == "UTC"


def test_data_config_custom():
    """Test DataConfig with custom values."""
    cfg = DataConfig(
        symbol="GBPUSD",
        timeframe="H1",
        start_pos=100,
        end_pos=2000,
        exclude_last_bar=False,
        tz="America/New_York",
    )
    assert cfg.symbol == "GBPUSD"
    assert cfg.timeframe == "H1"
    assert cfg.start_pos == 100
    assert cfg.end_pos == 2000
    assert cfg.exclude_last_bar is False
    assert cfg.tz == "America/New_York"


def test_data_config_frozen():
    """Test that DataConfig is frozen (immutable)."""
    cfg = DataConfig(symbol="EURUSD")
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        cfg.symbol = "GBPUSD"


# ==================== SessionConfig Tests ====================

def test_session_config_defaults():
    """Test SessionConfig with default session hours."""
    cfg = SessionConfig()
    assert cfg.asia_hours == tuple(range(0, 7))
    assert cfg.london_hours == tuple(range(7, 13))
    assert cfg.ny_hours == tuple(range(13, 21))
    assert cfg.off_hours == tuple(range(21, 24))


def test_session_config_custom():
    """Test SessionConfig with custom session hours."""
    cfg = SessionConfig(
        asia_hours=tuple(range(0, 8)),
        london_hours=tuple(range(8, 14)),
        ny_hours=tuple(range(14, 22)),
        off_hours=tuple(range(22, 24)),
    )
    assert cfg.asia_hours == tuple(range(0, 8))
    assert cfg.london_hours == tuple(range(8, 14))


def test_session_config_frozen():
    """Test that SessionConfig is frozen."""
    cfg = SessionConfig()
    with pytest.raises(Exception):
        cfg.asia_hours = tuple(range(0, 5))


# ==================== BootstrapConfig Tests ====================

def test_bootstrap_config_defaults():
    """Test BootstrapConfig with default values."""
    cfg = BootstrapConfig()
    assert cfg.n_boot == 2000
    assert cfg.block_size == 20
    assert cfg.ci_level == 0.95
    assert cfg.seed == 7


def test_bootstrap_config_custom():
    """Test BootstrapConfig with custom values."""
    cfg = BootstrapConfig(n_boot=5000, block_size=30, ci_level=0.99, seed=42)
    assert cfg.n_boot == 5000
    assert cfg.block_size == 30
    assert cfg.ci_level == 0.99
    assert cfg.seed == 42


def test_bootstrap_config_no_seed():
    """Test BootstrapConfig with no seed."""
    cfg = BootstrapConfig(seed=None)
    assert cfg.seed is None


# ==================== PermutationConfig Tests ====================

def test_permutation_config_defaults():
    """Test PermutationConfig with default values."""
    cfg = PermutationConfig()
    assert cfg.n_perm == 2000
    assert cfg.seed == 11


def test_permutation_config_custom():
    """Test PermutationConfig with custom values."""
    cfg = PermutationConfig(n_perm=10000, seed=99)
    assert cfg.n_perm == 10000
    assert cfg.seed == 99


# ==================== NullModelsConfig Tests ====================

def test_null_models_config_defaults():
    """Test NullModelsConfig with default values."""
    cfg = NullModelsConfig()
    assert cfg.n_random_entries == 1000
    assert cfg.hold_bars_options == (8, 16, 32, 48)
    assert cfg.percentile_threshold == 0.95
    assert cfg.include_shuffle_test is True
    assert cfg.include_time_randomization is True


def test_null_models_config_custom():
    """Test NullModelsConfig with custom values."""
    cfg = NullModelsConfig(
        n_random_entries=500,
        hold_bars_options=(10, 20, 30),
        percentile_threshold=0.90,
        include_shuffle_test=False,
        include_time_randomization=False,
    )
    assert cfg.n_random_entries == 500
    assert cfg.hold_bars_options == (10, 20, 30)
    assert cfg.percentile_threshold == 0.90
    assert cfg.include_shuffle_test is False
    assert cfg.include_time_randomization is False


# ==================== MeanReversionConfig Tests ====================

def test_mean_reversion_config_defaults():
    """Test MeanReversionConfig with default values."""
    cfg = MeanReversionConfig()
    assert cfg.sma_n == 20
    assert cfg.z_entry == 2.0
    assert cfg.bbw_n == 20
    assert cfg.bbw_k == 2.0
    assert cfg.compression_window == 252
    assert cfg.compression_q == 0.25
    assert cfg.atr_n == 14
    assert cfg.max_hold_bars == 32
    assert cfg.k_stop_atr == 1.2


def test_mean_reversion_config_custom():
    """Test MeanReversionConfig with custom values."""
    cfg = MeanReversionConfig(
        sma_n=50,
        z_entry=2.5,
        bbw_n=30,
        bbw_k=3.0,
        compression_window=500,
        compression_q=0.20,
        atr_n=20,
        max_hold_bars=48,
        k_stop_atr=1.5,
    )
    assert cfg.sma_n == 50
    assert cfg.z_entry == 2.5
    assert cfg.bbw_n == 30
    assert cfg.bbw_k == 3.0


# ==================== TrendPersistenceConfig Tests ====================

def test_trend_persistence_config_defaults():
    """Test TrendPersistenceConfig with default values."""
    cfg = TrendPersistenceConfig()
    assert cfg.breakout_n == 20
    assert cfg.atr_n == 14
    assert cfg.atr_regime_window == 252
    assert cfg.atr_q_high == 0.70
    assert cfg.max_hold_bars == 48
    assert cfg.k_stop_atr == 1.5
    assert cfg.k_target_atr == 1.0


def test_trend_persistence_config_custom():
    """Test TrendPersistenceConfig with custom values."""
    cfg = TrendPersistenceConfig(
        breakout_n=30,
        atr_n=20,
        atr_regime_window=500,
        atr_q_high=0.80,
        max_hold_bars=64,
        k_stop_atr=2.0,
        k_target_atr=1.5,
    )
    assert cfg.breakout_n == 30
    assert cfg.atr_n == 20
    assert cfg.atr_regime_window == 500


# ==================== SessionEdgeConfig Tests ====================

def test_session_edge_config_defaults():
    """Test SessionEdgeConfig with default values."""
    cfg = SessionEdgeConfig()
    assert cfg.sessions == ("asia", "london", "ny")
    assert cfg.analyze_opening_range is True
    assert cfg.opening_range_bars == 4
    assert cfg.analyze_reversals is True
    assert cfg.analyze_breakouts is True
    assert cfg.min_trades_per_session == 30
    assert cfg.hold_bars == 16
    assert cfg.atr_n == 14
    assert cfg.k_stop_atr == 1.0


def test_session_edge_config_custom():
    """Test SessionEdgeConfig with custom values."""
    cfg = SessionEdgeConfig(
        sessions=("london", "ny"),
        analyze_opening_range=False,
        opening_range_bars=8,
        analyze_reversals=False,
        analyze_breakouts=True,
        min_trades_per_session=50,
        hold_bars=24,
        atr_n=20,
        k_stop_atr=1.5,
    )
    assert cfg.sessions == ("london", "ny")
    assert cfg.analyze_opening_range is False
    assert cfg.opening_range_bars == 8


# ==================== EdgeLabConfig Tests ====================

def test_edge_lab_config_creation():
    """Test EdgeLabConfig creation with all sub-configs."""
    data_cfg = DataConfig(symbol="EURUSD", timeframe="H1")
    cfg = EdgeLabConfig(data=data_cfg)
    
    assert cfg.data.symbol == "EURUSD"
    assert cfg.data.timeframe == "H1"
    assert isinstance(cfg.sessions, SessionConfig)
    assert isinstance(cfg.bootstrap, BootstrapConfig)
    assert isinstance(cfg.perm, PermutationConfig)
    assert isinstance(cfg.null, NullModelsConfig)
    assert isinstance(cfg.mr, MeanReversionConfig)
    assert isinstance(cfg.tp, TrendPersistenceConfig)
    assert isinstance(cfg.session_edge, SessionEdgeConfig)


def test_edge_lab_config_custom_sub_configs():
    """Test EdgeLabConfig with custom sub-configs."""
    data_cfg = DataConfig(symbol="GBPUSD")
    boot_cfg = BootstrapConfig(n_boot=5000)
    mr_cfg = MeanReversionConfig(z_entry=2.5)
    
    cfg = EdgeLabConfig(
        data=data_cfg,
        bootstrap=boot_cfg,
        mr=mr_cfg,
    )
    
    assert cfg.data.symbol == "GBPUSD"
    assert cfg.bootstrap.n_boot == 5000
    assert cfg.mr.z_entry == 2.5


# ==================== create_config Function Tests ====================

def test_create_config_basic():
    """Test create_config with basic parameters."""
    cfg = create_config("EURUSD", "H1", end_pos=2000)
    
    assert cfg.data.symbol == "EURUSD"
    assert cfg.data.timeframe == "H1"
    assert cfg.data.end_pos == 2000
    assert isinstance(cfg.mr, MeanReversionConfig)
    assert isinstance(cfg.tp, TrendPersistenceConfig)


def test_create_config_mr_overrides():
    """Test create_config with MR overrides."""
    cfg = create_config("EURUSD", mr_z_entry=2.5, mr_sma_n=50)
    
    assert cfg.mr.z_entry == 2.5
    assert cfg.mr.sma_n == 50
    # Other MR values should be defaults
    assert cfg.mr.bbw_n == 20


def test_create_config_tp_overrides():
    """Test create_config with TP overrides."""
    cfg = create_config("GBPUSD", tp_breakout_n=30, tp_max_hold_bars=64)
    
    assert cfg.tp.breakout_n == 30
    assert cfg.tp.max_hold_bars == 64
    # Other TP values should be defaults
    assert cfg.tp.atr_n == 14


def test_create_config_boot_overrides():
    """Test create_config with bootstrap overrides."""
    cfg = create_config("EURUSD", boot_n_boot=5000, boot_seed=42)
    
    assert cfg.bootstrap.n_boot == 5000
    assert cfg.bootstrap.seed == 42
    # Other bootstrap values should be defaults
    assert cfg.bootstrap.block_size == 20


def test_create_config_mixed_overrides():
    """Test create_config with multiple override types."""
    cfg = create_config(
        "EURUSD",
        "M15",
        end_pos=3000,
        mr_z_entry=2.5,
        tp_breakout_n=30,
        boot_n_boot=5000,
    )
    
    assert cfg.data.symbol == "EURUSD"
    assert cfg.data.timeframe == "M15"
    assert cfg.data.end_pos == 3000
    assert cfg.mr.z_entry == 2.5
    assert cfg.tp.breakout_n == 30
    assert cfg.bootstrap.n_boot == 5000


def test_create_config_defaults():
    """Test create_config with all defaults."""
    cfg = create_config("EURUSD")
    
    assert cfg.data.symbol == "EURUSD"
    assert cfg.data.timeframe == "M15"
    assert cfg.data.end_pos == 5000
    assert cfg.mr == MeanReversionConfig()
    assert cfg.tp == TrendPersistenceConfig()
    assert cfg.bootstrap == BootstrapConfig()
