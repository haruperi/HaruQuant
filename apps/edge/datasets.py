"""Edge Lab data loading and preprocessing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

import numpy as np
import pandas as pd

from apps.utils.data_validator import DataValidator
from apps.utils.logger import logger

from .data.cleaning import CleaningConfig, clean_dataset
from .data.enrichment import EnrichmentConfig, enrich_dataset
from .data.models import CanonicalOHLCVSSchema, PreparedDataset
from .data.validation import validate_dataset


class DataSource(Protocol):
    """Protocol for data sources (MT5 client, CSV loader, DB, etc.)."""

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for the requested range."""
        ...


@dataclass(frozen=True)
class OHLCVSchema:
    """Expected OHLCV columns (case-insensitive matching)."""

    open: str = "Open"
    high: str = "High"
    low: str = "Low"
    close: str = "Close"
    volume: str = "Volume"


DEFAULT_SCHEMA = OHLCVSchema()
DEFAULT_ASIA_HOURS = tuple(range(0, 7))
DEFAULT_LONDON_HOURS = tuple(range(7, 13))
DEFAULT_NY_HOURS = tuple(range(13, 21))
DEFAULT_OFF_HOURS = tuple(range(21, 24))


def normalize_columns(
    df: pd.DataFrame, schema: OHLCVSchema | None = None
) -> pd.DataFrame:
    """Normalize column names to standard schema (Title Case).

    Handles both lowercase (MT5) and uppercase/mixed case inputs.
    """
    if schema is None:
        schema = DEFAULT_SCHEMA

    col_map: Dict[str, str] = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower == "open":
            col_map[col] = schema.open
        elif col_lower == "high":
            col_map[col] = schema.high
        elif col_lower == "low":
            col_map[col] = schema.low
        elif col_lower == "close":
            col_map[col] = schema.close
        elif col_lower in ("volume", "tick_volume", "tickvolume"):
            col_map[col] = schema.volume
        elif col_lower == "spread":
            col_map[col] = "Spread"

    if col_map:
        df = df.rename(columns=col_map)

    return df


def load_ohlc(
    source: DataSource,
    symbol: str,
    timeframe: str,
    start_pos: int,
    end_pos: int,
    exclude_last_bar: bool = True,
    schema: OHLCVSchema | None = None,
) -> pd.DataFrame:
    """Load OHLC data from a source and standardize columns.

    Args:
        source: Data source implementing fetch_data method
        symbol: Trading symbol
        timeframe: Timeframe string (e.g., "M15", "H1")
        start_pos: Start bar position
        end_pos: End bar position
        exclude_last_bar: Whether to exclude the last (incomplete) bar
        schema: Column naming schema

    Returns:
        DataFrame with standardized OHLC columns and DatetimeIndex

    Raises:
        ValueError: If required columns are missing or data is empty
    """
    logger.info(
        f"Loading OHLC data for {symbol} {timeframe} (bars {start_pos}-{end_pos})"
    )

    df = source.fetch_data(
        symbol=symbol, timeframe=timeframe, start_pos=start_pos, end_pos=end_pos
    )

    if df is None or df.empty:
        logger.error(f"No data returned for {symbol} {timeframe}")
        raise ValueError(f"No data returned for {symbol} {timeframe}")

    # Normalize column names
    df = normalize_columns(df, schema)

    if schema is None:
        schema = DEFAULT_SCHEMA

    # Validate required columns
    required = [schema.open, schema.high, schema.low, schema.close]
    missing = [r for r in required if r not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
        raise ValueError(f"Missing required column(s) {missing} in data for {symbol}")

    # Exclude last bar if requested
    if exclude_last_bar and len(df) > 2:
        df = df.iloc[:-1]

    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df.index = pd.to_datetime(df["time"])
            df = df.drop(columns=["time"], errors="ignore")
        elif "timestamp" in df.columns:
            df.index = pd.to_datetime(df["timestamp"])
            df = df.drop(columns=["timestamp"], errors="ignore")
        else:
            logger.error("Data must have a DatetimeIndex or 'time'/'timestamp' column")
            raise ValueError(
                "Data must have a DatetimeIndex or a 'time'/'timestamp' column."
            )

    df = df.sort_index()

    logger.info(
        f"Loaded {len(df)} bars for {symbol} {timeframe} ({df.index[0]} to {df.index[-1]})"
    )
    return df


def resample_ohlc(
    df: pd.DataFrame, rule: str, schema: OHLCVSchema | None = None
) -> pd.DataFrame:
    """Resample OHLCV to a different timeframe rule.

    Args:
        df: Source DataFrame with OHLCV data
        rule: Pandas resample rule (e.g., '1H', '4H', 'D')
        schema: Column naming schema

    Returns:
        Resampled DataFrame
    """
    if schema is None:
        schema = DEFAULT_SCHEMA

    o, h, l, c, v = schema.open, schema.high, schema.low, schema.close, schema.volume
    agg = {o: "first", h: "max", l: "min", c: "last"}
    if v in df.columns:
        agg[v] = "sum"

    out = df.resample(rule).agg(agg).dropna()
    logger.debug(f"Resampled {len(df)} bars to {len(out)} bars with rule '{rule}'")
    return out


def tag_sessions(
    df: pd.DataFrame,
    asia_hours: Sequence[int] = DEFAULT_ASIA_HOURS,
    london_hours: Sequence[int] = DEFAULT_LONDON_HOURS,
    ny_hours: Sequence[int] = DEFAULT_NY_HOURS,
    off_hours: Sequence[int] = DEFAULT_OFF_HOURS,
) -> pd.DataFrame:
    """Tag each bar with its trading session.

    Sessions are based on UTC hour:
    - Asia:   00:00–06:59 UTC
    - London: 07:00–12:59 UTC
    - NewYork:13:00–20:59 UTC
    - Off:    21:00–23:59 UTC

    Args:
        df: DataFrame with DatetimeIndex
        asia_hours: Hours considered Asia session
        london_hours: Hours considered London session
        ny_hours: Hours considered New York session
        off_hours: Hours considered off-market

    Returns:
        DataFrame with 'session' column added
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex for session tagging")

    df = df.copy()
    hours = df.index.hour

    conditions = [
        hours.isin(asia_hours),
        hours.isin(london_hours),
        hours.isin(ny_hours),
        hours.isin(off_hours),
    ]
    choices = ["asia", "london", "ny", "off"]

    df["session"] = np.select(conditions, choices, default="unknown")

    session_counts = df["session"].value_counts()
    logger.debug(f"Session distribution: {session_counts.to_dict()}")

    return df


def get_session_ranges(
    df: pd.DataFrame,
    session: str,
) -> pd.DataFrame:
    """Get bars belonging to a specific session.

    Args:
        df: DataFrame with 'session' column
        session: Session name ('asia', 'london', 'ny', 'off')

    Returns:
        Filtered DataFrame for the session
    """
    if "session" not in df.columns:
        df = tag_sessions(df)

    return df[df["session"] == session].copy()


def compute_session_stats(
    df: pd.DataFrame,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> pd.DataFrame:
    """Compute per-session statistics.

    Args:
        df: DataFrame with session tags and OHLC data
        close_col: Close price column name
        high_col: High price column name
        low_col: Low price column name

    Returns:
        DataFrame with per-session statistics
    """
    if "session" not in df.columns:
        df = tag_sessions(df)

    df = df.copy()
    df["returns"] = np.log(df[close_col] / df[close_col].shift(1))
    df["range"] = df[high_col] - df[low_col]

    stats = df.groupby("session").agg(
        {
            "returns": ["mean", "std", "count"],
            "range": ["mean", "std"],
        }
    )

    stats.columns = ["_".join(col).strip() for col in stats.columns.values]
    stats = stats.rename(
        columns={
            "returns_mean": "mean_return",
            "returns_std": "volatility",
            "returns_count": "n_bars",
            "range_mean": "avg_range",
            "range_std": "range_std",
        }
    )

    logger.info(f"Session stats computed: {stats.index.tolist()}")
    return stats


def validate_data_quality(
    df: pd.DataFrame,
    schema: OHLCVSchema | None = None,
) -> Dict[str, Any]:
    """Validate data quality and return diagnostics.

    Args:
        df: DataFrame with OHLC data
        schema: Column naming schema

    Returns:
        Dictionary with quality metrics
    """
    if schema is None:
        schema = DEFAULT_SCHEMA

    n_missing: Dict[str, int] = {}
    n_zeros: Dict[str, int] = {}
    gaps: List[Dict[str, str]] = []
    date_range: Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]] = (
        (df.index.min(), df.index.max()) if len(df) > 0 else (None, None)
    )

    diagnostics: Dict[str, Any] = {
        "n_rows": len(df),
        "n_missing": n_missing,
        "n_zeros": n_zeros,
        "date_range": date_range,
        "gaps": gaps,
        "valid": True,
    }

    for col in [schema.open, schema.high, schema.low, schema.close]:
        if col in df.columns:
            diagnostics["n_missing"][col] = int(df[col].isna().sum())
            diagnostics["n_zeros"][col] = int((df[col] == 0).sum())

    # Check for time gaps (more than 2x median interval)
    if len(df) > 1:
        time_diffs = df.index.to_series().diff().dropna()
        median_diff = time_diffs.median()
        large_gaps = time_diffs[time_diffs > 2 * median_diff]
        if len(large_gaps) > 0:
            diagnostics["gaps"] = [
                {"after": str(idx), "gap": str(gap)}
                for idx, gap in large_gaps.head(10).items()
            ]

    # Check for invalid OHLC relationships
    if all(
        col in df.columns
        for col in [schema.high, schema.low, schema.open, schema.close]
    ):
        invalid_hl = (df[schema.high] < df[schema.low]).sum()
        invalid_ho = (df[schema.high] < df[schema.open]).sum()
        invalid_hc = (df[schema.high] < df[schema.close]).sum()
        invalid_lo = (df[schema.low] > df[schema.open]).sum()
        invalid_lc = (df[schema.low] > df[schema.close]).sum()

        invalid_ohlc: Dict[str, int] = {
            "high_lt_low": int(invalid_hl),
            "high_lt_open": int(invalid_ho),
            "high_lt_close": int(invalid_hc),
            "low_gt_open": int(invalid_lo),
            "low_gt_close": int(invalid_lc),
        }
        diagnostics["invalid_ohlc"] = invalid_ohlc

        if any(v > 0 for v in invalid_ohlc.values()):
            diagnostics["valid"] = False
            logger.warning(f"Invalid OHLC relationships detected: {invalid_ohlc}")

    logger.debug(f"Data quality diagnostics: {diagnostics}")
    return diagnostics


def _synthesize_ohlcvs_columns(
    df: pd.DataFrame,
    schema: CanonicalOHLCVSSchema,
) -> pd.DataFrame:
    """Ensure canonical volume and spread columns exist for analysis."""
    out = df.copy()
    if schema.volume not in out.columns:
        out[schema.volume] = 0.0
    if schema.spread not in out.columns:
        validator = DataValidator()
        prepared = validator.prepare_data(out)
        out[schema.spread] = prepared["spread"].to_numpy()
        if schema.volume in prepared.columns:
            out[schema.volume] = prepared["volume"].to_numpy()
    return out


def prepare_ohlcvs_dataset(
    source: DataSource,
    symbol: str,
    timeframe: str,
    start_pos: int,
    end_pos: int,
    *,
    exclude_last_bar: bool = True,
    schema: OHLCVSchema | None = None,
    cleaning: CleaningConfig | None = None,
    enrichment: EnrichmentConfig | None = None,
) -> PreparedDataset:
    """Load, validate, clean, and enrich an analysis-ready OHLCVS dataset."""
    schema = schema or DEFAULT_SCHEMA
    canonical = CanonicalOHLCVSSchema(
        open=schema.open,
        high=schema.high,
        low=schema.low,
        close=schema.close,
        volume=schema.volume,
        spread="Spread",
    )

    raw = load_ohlc(
        source=source,
        symbol=symbol,
        timeframe=timeframe,
        start_pos=start_pos,
        end_pos=end_pos,
        exclude_last_bar=exclude_last_bar,
        schema=schema,
    )
    raw = _synthesize_ohlcvs_columns(raw, canonical)

    report = validate_dataset(raw, schema=canonical, timeframe=timeframe)
    if report.is_valid:
        cleaned = clean_dataset(
            raw,
            report=report,
            schema=canonical,
            config=cleaning or CleaningConfig(timeframe=timeframe),
        )
        enriched = enrich_dataset(
            cleaned,
            schema=canonical,
            config=enrichment or EnrichmentConfig(symbol=symbol),
        )
    else:
        cleaned = raw
        enriched = raw

    report.metadata.update(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "n_rows": len(enriched),
            "start": str(enriched.index.min()) if len(enriched) else None,
            "end": str(enriched.index.max()) if len(enriched) else None,
        }
    )
    return PreparedDataset(data=enriched, report=report, schema=canonical)

