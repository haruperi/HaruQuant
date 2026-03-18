"""Edge Lab configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class DataConfig:
    """Configuration for data loading and preprocessing."""

    symbol: str
    timeframe: str = "M15"
    start_pos: int = 0
    end_pos: int = 5000
    exclude_last_bar: bool = True
    tz: str = "UTC"


@dataclass(frozen=True)
class SessionConfig:
    """FX session boundaries in UTC hours.

    Default (common approximation, varies with DST):
    - Asia:   00:00–06:59 UTC
    - London: 07:00–12:59 UTC
    - NewYork:13:00–20:59 UTC
    - Off:    21:00–23:59 UTC
    """

    asia_hours: Sequence[int] = tuple(range(0, 7))
    london_hours: Sequence[int] = tuple(range(7, 13))
    ny_hours: Sequence[int] = tuple(range(13, 21))
    off_hours: Sequence[int] = tuple(range(21, 24))


@dataclass(frozen=True)
class BootstrapConfig:
    """Block bootstrap configuration for autocorrelation-aware inference."""

    n_boot: int = 2000
    block_size: int = 20
    ci_level: float = 0.95
    seed: Optional[int] = 7


@dataclass(frozen=True)
class PermutationConfig:
    """Permutation/randomization test configuration."""

    n_perm: int = 2000
    seed: Optional[int] = 11


@dataclass(frozen=True)
class NullModelsConfig:
    """EDS-0: Null Models / Baseline configuration."""

    n_random_entries: int = 1000
    hold_bars_options: Sequence[int] = (8, 16, 32, 48)
    percentile_threshold: float = 0.95
    include_shuffle_test: bool = True
    include_time_randomization: bool = True


@dataclass(frozen=True)
class MeanReversionConfig:
    """EDS-1: Mean Reversion Detector configuration."""

    sma_n: int = 20
    z_entry: float = 2.0
    bbw_n: int = 20
    bbw_k: float = 2.0
    compression_window: int = 252
    compression_q: float = 0.25
    atr_n: int = 14
    max_hold_bars: int = 32
    k_stop_atr: float = 1.2


@dataclass(frozen=True)
class TrendPersistenceConfig:
    """EDS-2: Trend Persistence Detector configuration."""

    breakout_n: int = 20
    atr_n: int = 14
    atr_regime_window: int = 252
    atr_q_high: float = 0.70
    max_hold_bars: int = 48
    k_stop_atr: float = 1.5
    k_target_atr: float = 1.0


@dataclass(frozen=True)
class MarketStructureConfig:
    """Market Structure engine configuration."""

    model_version: str = "market_structure_baseline_v1"
    baseline_id: str = "ms_baseline_2026_03_17"
    swing_window: int = 3
    min_swing_atr: float = 0.5
    atr_window: int = 14
    range_window: int = 20
    breakout_horizon: int = 5
    min_chain_length: int = 2
    eds_boot_n: int = 50
    eds_perm_n: int = 50
    research_eds_boot_n: int = 500
    research_eds_perm_n: int = 500
    bias_verdict_min_gap: float = 15.0
    trend_confidence_min: float = 35.0
    reversion_confidence_min: float = 35.0
    reversion_score_weight: float = 0.75
    chop_score_weight: float = 0.25
    stability_block_count: int = 3
    stability_min_bars_per_block: int = 80
    stability_score_std_max: float = 20.0
    stability_modes: Sequence[str] = ("early_middle_late", "monthly", "quarterly")
    robustness_swing_windows: Sequence[int] = (2, 3, 4)
    robustness_min_swing_atrs: Sequence[float] = (0.3, 0.5, 0.7)
    robustness_range_windows: Sequence[int] = (15, 20, 25)
    robustness_breakout_horizons: Sequence[int] = (3, 5, 8)
    apply_profile_overrides: bool = True
    apply_quality_adjustments: bool = False
    stability_confidence_weight: float = 0.10
    robustness_confidence_weight: float = 0.10


@dataclass(frozen=True)
class SessionEdgeConfig:
    """EDS-3: Session Edge Detector configuration."""

    sessions: Sequence[str] = ("asia", "london", "ny")
    analyze_opening_range: bool = True
    opening_range_bars: int = 4
    analyze_reversals: bool = True
    analyze_breakouts: bool = True
    min_trades_per_session: int = 30
    hold_bars: int = 16
    atr_n: int = 14
    k_stop_atr: float = 1.0


@dataclass(frozen=True)
class EdgeLabConfig:
    """Top-level configuration for Edge Lab."""

    data: DataConfig
    sessions: SessionConfig = field(default_factory=SessionConfig)
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)
    perm: PermutationConfig = field(default_factory=PermutationConfig)
    null: NullModelsConfig = field(default_factory=NullModelsConfig)
    mr: MeanReversionConfig = field(default_factory=MeanReversionConfig)
    tp: TrendPersistenceConfig = field(default_factory=TrendPersistenceConfig)
    market_structure: MarketStructureConfig = field(default_factory=MarketStructureConfig)
    session_edge: SessionEdgeConfig = field(default_factory=SessionEdgeConfig)


def create_config(
    symbol: str, timeframe: str = "M15", end_pos: int = 5000, **overrides
) -> EdgeLabConfig:
    """Create EdgeLabConfig with common defaults.

    Args:
        symbol: Trading symbol (e.g., "EURUSD")
        timeframe: Timeframe string (e.g., "M15", "H1")
        end_pos: Number of bars to analyze
        **overrides: Override any nested config values

    Returns:
        EdgeLabConfig instance

    Example:
        >>> cfg = create_config("EURUSD", "H1", end_pos=2000)
        >>> cfg = create_config("GBPUSD", mr_z_entry=2.5)
    """
    data_cfg = DataConfig(
        symbol=symbol,
        timeframe=timeframe,
        end_pos=end_pos,
    )

    # Parse overrides for nested configs
    mr_overrides = {
        k.replace("mr_", ""): v for k, v in overrides.items() if k.startswith("mr_")
    }
    tp_overrides = {
        k.replace("tp_", ""): v for k, v in overrides.items() if k.startswith("tp_")
    }
    boot_overrides = {
        k.replace("boot_", ""): v for k, v in overrides.items() if k.startswith("boot_")
    }

    return EdgeLabConfig(
        data=data_cfg,
        mr=(
            MeanReversionConfig(**mr_overrides)
            if mr_overrides
            else MeanReversionConfig()
        ),
        tp=(
            TrendPersistenceConfig(**tp_overrides)
            if tp_overrides
            else TrendPersistenceConfig()
        ),
        bootstrap=(
            BootstrapConfig(**boot_overrides) if boot_overrides else BootstrapConfig()
        ),
    )
