"""Seasonality analytics for Edge Lab (Phase A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

DEFAULT_ADR_PERIOD = 10
SESSION_ORDER = (
    "sydney",
    "tokyo",
    "sydney_tokyo",
    "london",
    "london_ny",
    "ny",
    "gap",
)


@dataclass(frozen=True)
class SeasonalityFilters:
    """Filters for seasonality analysis."""

    decades: Optional[List[int]] = None
    years: Optional[List[int]] = None
    months: Optional[List[int]] = None
    dows: Optional[List[int]] = None
    hours: Optional[List[int]] = None


def _clean_value(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_list(values: Iterable[Any]) -> List[Optional[float]]:
    return [_clean_value(value) for value in values]


def _table_to_dict(frame: pd.DataFrame) -> Dict[str, Any]:
    return {
        "index": [int(v) for v in frame.index],
        "columns": [int(v) for v in frame.columns],
        "values": [list(_to_list(row)) for row in frame.to_numpy().tolist()],
    }


def _series_to_dict(series: pd.Series) -> Dict[str, Any]:
    return {
        "index": [int(v) for v in series.index],
        "values": _to_list(series.values),
    }


def _apply_filters(df: pd.DataFrame, filters: SeasonalityFilters) -> pd.DataFrame:
    out = df
    if filters.decades:
        out = out[out["decade"].isin(filters.decades)]
    if filters.years:
        out = out[out["year"].isin(filters.years)]
    if filters.months:
        out = out[out["month"].isin(filters.months)]
    if filters.dows:
        out = out[out["dow"].isin(filters.dows)]
    if filters.hours:
        out = out[out["hour"].isin(filters.hours)]
    return out


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Spread" not in out.columns:
        out["Spread"] = 0.0
    if "Volume" not in out.columns:
        out["Volume"] = np.nan
    return out


def _compute_adr(df: pd.DataFrame) -> pd.Series:
    daily = df.resample("D").agg({"High": "max", "Low": "min"}).dropna()
    daily_range = daily["High"] - daily["Low"]
    return daily_range.rolling(DEFAULT_ADR_PERIOD).mean().shift(1)


def _calendar_agg(df: pd.DataFrame, key: str) -> Dict[str, Any]:
    grouped = df.groupby(key).agg(
        count=("range_points", "count"),
        avg_range_points=("range_points", "mean"),
        avg_co_points=("co_points", "mean"),
        avg_spread_points=("spread_points", "mean"),
        avg_co_pct=("co_pct", "mean"),
    )
    return {
        "index": [int(v) for v in grouped.index],
        "count": [int(v) for v in grouped["count"].tolist()],
        "avg_range_points": _to_list(grouped["avg_range_points"].tolist()),
        "avg_co_points": _to_list(grouped["avg_co_points"].tolist()),
        "avg_spread_points": _to_list(grouped["avg_spread_points"].tolist()),
        "avg_co_pct": _to_list(grouped["avg_co_pct"].tolist()),
    }


def _prepare_working_data(
    df: pd.DataFrame, point_size: float, pip_size: float
) -> pd.DataFrame:
    df = _ensure_columns(df)
    working = df.copy()

    working["range_points"] = (working["High"] - working["Low"]) / point_size
    working["co_points"] = (working["Close"] - working["Open"]) / point_size
    working["co_pct"] = (working["Close"] - working["Open"]) / working["Close"]
    working["win_flag"] = (working["co_points"] > 0).astype(int)
    working["spread_points"] = working["Spread"]

    adr = _compute_adr(working)
    working["date"] = working.index.normalize()
    working = working.merge(
        adr.rename("adr_d1"), left_on="date", right_index=True, how="left"
    )
    working = working.drop(columns=["date"])
    working["adr_points"] = working["adr_d1"] / point_size
    working["spread_to_range"] = working["spread_points"] / working[
        "range_points"
    ].replace(0, np.nan)
    working["spread_to_adr"] = working["spread_points"] / working["adr_points"].replace(
        0, np.nan
    )

    working["year"] = working.index.year
    working["month"] = working.index.month
    working["day_of_month"] = working.index.day
    working["dow"] = working.index.dayofweek
    working["hour"] = working.index.hour
    working["decade"] = (working["year"] // 10) * 10
    if "session" not in working.columns:
        working["session"] = np.select(
            [
                working["hour"].isin(range(0, 2)),
                working["hour"].isin(range(2, 7)),
                working["hour"].isin(range(7, 9)),
                working["hour"].isin(range(10, 15)),
                working["hour"].isin(range(15, 17)),
                working["hour"].isin(range(17, 22)),
            ],
            ["sydney", "sydney_tokyo", "tokyo", "london", "london_ny", "ny"],
            default="gap",
        )
    if "session_basis" not in working.columns:
        working["session_basis"] = "dataset_index"
    return working


def _label_opportunity(score: float) -> str:
    if score >= 65:
        return "opportunity"
    if score <= 35:
        return "dead"
    return "mixed"


def _score_window(
    avg_range_pips: float,
    avg_spread_pips: float,
    avg_abs_co_pips: float,
    win_rate: float,
) -> float:
    range_score = max(0.0, min(100.0, (avg_range_pips / 25.0) * 100.0))
    spread_efficiency = avg_spread_pips / max(avg_range_pips, 1e-9)
    spread_score = max(0.0, min(100.0, 100.0 - ((spread_efficiency - 0.05) / 0.25) * 100.0))
    movement_score = max(0.0, min(100.0, (avg_abs_co_pips / 10.0) * 100.0))
    directional_score = max(0.0, min(100.0, abs((win_rate - 0.5) * 2.0) * 100.0))
    return float(
        (range_score * 0.40)
        + (spread_score * 0.30)
        + (movement_score * 0.20)
        + (directional_score * 0.10)
    )


def _calculate_intraday_bias(
    filtered: pd.DataFrame,
    point_size: float,
    pip_size: float,
    hour_index: pd.Index,
    dow_index: pd.Index,
) -> Dict[int, List[float]]:
    co_pips_series = filtered["co_points"] * (point_size / pip_size)
    intraday_bias = {}
    for dow in dow_index:
        hourly = (
            filtered.assign(co_pips=co_pips_series)[filtered["dow"] == dow]
            .groupby("hour")["co_pips"]
            .mean()
            .reindex(hour_index)
            .fillna(0.0)
        )
        intraday_bias[int(dow)] = hourly.cumsum().tolist()
    return intraday_bias


def _calculate_heatmaps(
    filtered: pd.DataFrame,
    point_size: float,
    pip_size: float,
    hour_index: pd.Index,
    dow_index: pd.Index,
) -> Dict[str, Any]:
    range_pips_series = filtered["range_points"] * (point_size / pip_size)
    spread_pips_series = filtered["spread_points"] * (point_size / pip_size)

    return {
        "avg_volume": _table_to_dict(
            filtered.pivot_table(
                index="hour", columns="dow", values="Volume", aggfunc="mean"
            ).reindex(index=hour_index, columns=dow_index)
        ),
        "avg_range_pips": _table_to_dict(
            filtered.assign(range_pips=range_pips_series)
            .pivot_table(
                index="hour", columns="dow", values="range_pips", aggfunc="mean"
            )
            .reindex(index=hour_index, columns=dow_index)
        ),
        "win_rate": _table_to_dict(
            filtered.pivot_table(
                index="hour", columns="dow", values="win_flag", aggfunc="mean"
            ).reindex(index=hour_index, columns=dow_index)
        ),
        "avg_spread_pips": _table_to_dict(
            filtered.assign(spread_pips=spread_pips_series)
            .pivot_table(
                index="hour", columns="dow", values="spread_pips", aggfunc="mean"
            )
            .reindex(index=hour_index, columns=dow_index)
        ),
        "spread_to_range": _table_to_dict(
            filtered.pivot_table(
                index="hour", columns="dow", values="spread_to_range", aggfunc="mean"
            ).reindex(index=hour_index, columns=dow_index)
        ),
    }


def _calculate_session_high_low_rates(filtered: pd.DataFrame) -> Dict[str, Any]:
    if filtered.empty:
        return {"total_days": 0, "rows": []}

    high_counts = {session: 0 for session in SESSION_ORDER}
    low_counts = {session: 0 for session in SESSION_ORDER}
    evaluable_days = 0

    for _, frame in filtered.groupby(filtered.index.normalize()):
        if frame.empty:
            continue
        evaluable_days += 1
        high_session = str(frame.loc[frame["High"].idxmax(), "session"])
        low_session = str(frame.loc[frame["Low"].idxmin(), "session"])
        high_counts[high_session] = high_counts.get(high_session, 0) + 1
        low_counts[low_session] = low_counts.get(low_session, 0) + 1

    rows = []
    for session in SESSION_ORDER:
        rows.append(
            {
                "session": session,
                "high_count": int(high_counts.get(session, 0)),
                "low_count": int(low_counts.get(session, 0)),
                "high_rate": float(high_counts.get(session, 0) / evaluable_days) if evaluable_days else 0.0,
                "low_rate": float(low_counts.get(session, 0) / evaluable_days) if evaluable_days else 0.0,
            }
        )
    return {"total_days": evaluable_days, "rows": rows}


def _calculate_session_summary(
    filtered: pd.DataFrame,
    point_size: float,
    pip_size: float,
    high_low_rates: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rate_map = {str(row["session"]): row for row in high_low_rates.get("rows", [])}
    rows: List[Dict[str, Any]] = []
    for session in SESSION_ORDER:
        frame = filtered[filtered["session"] == session]
        if frame.empty:
            rows.append(
                {
                    "session": session,
                    "bars": 0,
                    "avg_range_pips": None,
                    "avg_spread_pips": None,
                    "avg_abs_co_pips": None,
                    "avg_volume": None,
                    "win_rate": None,
                    "opportunity_score": 0.0,
                    "label": "dead",
                    "high_rate": float(rate_map.get(session, {}).get("high_rate", 0.0)),
                    "low_rate": float(rate_map.get(session, {}).get("low_rate", 0.0)),
                }
            )
            continue
        avg_range_pips = float((((frame["High"] - frame["Low"]) / pip_size)).mean())
        avg_spread_pips = float(((frame["Spread"] * point_size) / pip_size).mean())
        avg_abs_co_pips = float((((frame["Close"] - frame["Open"]).abs()) / pip_size).mean())
        avg_volume = _clean_value(frame["Volume"].mean())
        win_rate = float((frame["co_points"] > 0).mean())
        score = _score_window(avg_range_pips, avg_spread_pips, avg_abs_co_pips, win_rate)
        rows.append(
            {
                "session": session,
                "bars": int(len(frame)),
                "avg_range_pips": avg_range_pips,
                "avg_spread_pips": avg_spread_pips,
                "avg_abs_co_pips": avg_abs_co_pips,
                "avg_volume": avg_volume,
                "win_rate": win_rate,
                "opportunity_score": score,
                "label": _label_opportunity(score),
                "high_rate": float(rate_map.get(session, {}).get("high_rate", 0.0)),
                "low_rate": float(rate_map.get(session, {}).get("low_rate", 0.0)),
            }
        )
    return rows


def _calculate_hourly_window_summary(
    filtered: pd.DataFrame,
    point_size: float,
    pip_size: float,
) -> Dict[str, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for hour in range(24):
        frame = filtered[filtered["hour"] == hour]
        if frame.empty:
            score = 0.0
            rows.append(
                {
                    "hour": hour,
                    "bars": 0,
                    "avg_range_pips": None,
                    "avg_spread_pips": None,
                    "avg_abs_co_pips": None,
                    "win_rate": None,
                    "opportunity_score": score,
                    "label": "dead",
                }
            )
            continue
        avg_range_pips = float((((frame["High"] - frame["Low"]) / pip_size)).mean())
        avg_spread_pips = float(((frame["Spread"] * point_size) / pip_size).mean())
        avg_abs_co_pips = float((((frame["Close"] - frame["Open"]).abs()) / pip_size).mean())
        win_rate = float((frame["co_points"] > 0).mean())
        score = _score_window(avg_range_pips, avg_spread_pips, avg_abs_co_pips, win_rate)
        rows.append(
            {
                "hour": hour,
                "bars": int(len(frame)),
                "avg_range_pips": avg_range_pips,
                "avg_spread_pips": avg_spread_pips,
                "avg_abs_co_pips": avg_abs_co_pips,
                "win_rate": win_rate,
                "opportunity_score": score,
                "label": _label_opportunity(score),
            }
        )
    ranked = sorted(rows, key=lambda row: float(row["opportunity_score"]), reverse=True)
    return {
        "all": rows,
        "best_hours": ranked[:5],
        "dead_hours": list(reversed(ranked[-5:])),
    }


def _generate_data_rows(
    filtered: pd.DataFrame,
    data_offset: int,
    data_limit: int,
    point_size: float,
    pip_size: float,
) -> List[Dict[str, Any]]:
    data_rows = []
    if data_offset < 0:
        data_offset = 0
    if data_limit <= 0:
        data_limit = 20
    data_slice = filtered.iloc[data_offset : data_offset + data_limit]
    for idx, (ts, row) in enumerate(data_slice.iterrows(), start=1):
        day_label = ts.strftime("%d")
        month_label = ts.strftime("%B")
        dow_label = ts.strftime("%A")
        data_rows.append(
            {
                "date": ts.strftime("%Y-%m-%d"),
                "time": ts.strftime("%H:%M"),
                "open": _clean_value(row.get("Open")),
                "high": _clean_value(row.get("High")),
                "low": _clean_value(row.get("Low")),
                "close": _clean_value(row.get("Close")),
                "volume": _clean_value(row.get("Volume")),
                "spread_pips": _clean_value(
                    (row.get("Spread") * point_size) / pip_size
                ),
                "decade": f"{int(row.get('decade'))}-{int(row.get('decade')) + 9}",
                "day": day_label,
                "month": month_label,
                "year": int(row.get("year")),
                "dow": dow_label,
                "count": data_offset + idx,
                "range_hl": _clean_value((row.get("High") - row.get("Low")) / pip_size),
                "co_points": _clean_value(
                    (row.get("Close") - row.get("Open")) / pip_size
                ),
                "co_win_loss": (
                    1
                    if row.get("co_points") > 0
                    else -1 if row.get("co_points") < 0 else 0
                ),
                "co_pct": _clean_value(
                    row.get("co_pct") * 100 if row.get("co_pct") is not None else None
                ),
                "time_rnd": ts.strftime("%H:%M"),
            }
        )
    return data_rows


def _extreme(series: pd.Series, mode: str, *, nonzero: bool = False) -> Dict[str, Any]:
    if series.empty:
        return {"value": None, "hour": None}
    series = series.dropna()
    if series.empty:
        return {"value": None, "hour": None}
    if nonzero:
        series = series[series != 0]
        if series.empty:
            return {"value": None, "timestamp": None}
    pos = int(series.to_numpy().argmin() if mode == "min" else series.to_numpy().argmax())
    value = series.iloc[pos]
    idx = series.index[pos]
    return {"value": float(value), "timestamp": idx.strftime("%Y-%m-%d %H:%M")}


def _extreme_abs(series: pd.Series, mode: str) -> Dict[str, Any]:
    if series.empty:
        return {"value": None, "timestamp": None}
    series = series.dropna()
    series = series[series != 0]
    if series.empty:
        return {"value": None, "timestamp": None}
    abs_series = series.abs()
    pos = int(abs_series.to_numpy().argmin() if mode == "min" else abs_series.to_numpy().argmax())
    idx = abs_series.index[pos]
    value = series.iloc[pos]
    return {"value": float(value), "timestamp": idx.strftime("%Y-%m-%d %H:%M")}


def _calc_stats(
    series: pd.Series, abs_percentiles: bool = False
) -> Dict[str, Optional[float]]:
    clean = series.dropna()
    if clean.empty:
        return {"avg": None, "p95": None, "p99": None}

    values = clean.values
    avg_val = float(np.mean(values))

    if abs_percentiles:
        values = np.abs(values)

    p95 = float(np.percentile(values, 95))
    p99 = float(np.percentile(values, 99))

    return {"avg": avg_val, "p95": p95, "p99": p99}


def _calculate_extremes(
    filtered: pd.DataFrame, point_size: float, pip_size: float
) -> Dict[str, Any]:
    range_pips_series = filtered["range_points"] * (point_size / pip_size)
    co_pips_series = filtered["co_points"] * (point_size / pip_size)
    spread_pips_series = filtered["spread_points"] * (point_size / pip_size)

    return {
        "range_pips": {
            "min": _extreme(range_pips_series, "min", nonzero=True),
            "max": _extreme(range_pips_series, "max"),
            **_calc_stats(range_pips_series),
        },
        "co_pips": {
            "min": _extreme_abs(co_pips_series, "min"),
            "max": _extreme_abs(co_pips_series, "max"),
            **_calc_stats(co_pips_series, abs_percentiles=True),
        },
        "volume": {
            "min": _extreme(filtered["Volume"], "min", nonzero=True),
            "max": _extreme(filtered["Volume"], "max"),
            **_calc_stats(filtered["Volume"]),
        },
        "spread_pips": {
            "min": _extreme(spread_pips_series, "min", nonzero=True),
            "max": _extreme(spread_pips_series, "max"),
            **_calc_stats(spread_pips_series),
        },
    }


def run_seasonality(
    df: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    point_size: float = 1.0,
    pip_size: Optional[float] = None,
    filters: Optional[SeasonalityFilters] = None,
    data_offset: int = 0,
    data_limit: int = 20,
) -> Dict[str, Any]:
    """
    Run seasonality analysis on the provided dataframe.

    Args:
        df: Pandas DataFrame with OHLCV data
        symbol: Symbol name
        timeframe: Timeframe name
        point_size: Point size for the symbol (default 1.0)
        pip_size: Pip size for the symbol (default None, uses point_size)
        filters: Filters to apply to the analysis
        data_offset: Offset for data rows pagination
        data_limit: Limit for data rows pagination

    Returns:
        Dictionary with analysis results
    """
    if point_size <= 0:
        raise ValueError("point_size must be > 0")

    if pip_size is None:
        pip_size = point_size
    if pip_size <= 0:
        raise ValueError("pip_size must be > 0")

    working = _prepare_working_data(df, point_size, pip_size)

    total_rows = len(working)
    if filters is None:
        filters = SeasonalityFilters()
    filtered = _apply_filters(working, filters)

    hour_index = pd.Index(range(24), name="hour")
    dow_index = pd.Index(range(7), name="dow")

    intraday_bias = _calculate_intraday_bias(
        filtered, point_size, pip_size, hour_index, dow_index
    )
    heatmaps = _calculate_heatmaps(
        filtered, point_size, pip_size, hour_index, dow_index
    )
    calendar = {
        "year": _calendar_agg(filtered, "year"),
        "month": _calendar_agg(filtered, "month"),
        "day_of_month": _calendar_agg(filtered, "day_of_month"),
        "dow": _calendar_agg(filtered, "dow"),
    }
    session_high_low = _calculate_session_high_low_rates(filtered)
    session_summary = _calculate_session_summary(
        filtered, point_size, pip_size, session_high_low
    )
    hourly_windows = _calculate_hourly_window_summary(filtered, point_size, pip_size)
    ranked_sessions = sorted(
        session_summary, key=lambda row: float(row["opportunity_score"]), reverse=True
    )
    data_rows = _generate_data_rows(
        filtered, data_offset, data_limit, point_size, pip_size
    )
    extremes = _calculate_extremes(filtered, point_size, pip_size)

    spread_series = (
        filtered["Spread"] if "Spread" in filtered.columns else pd.Series([])
    )
    spread_nonzero = int((spread_series > 0).sum()) if not spread_series.empty else 0
    spread_zero = int((spread_series == 0).sum()) if not spread_series.empty else 0

    return {
        "meta": {
            "symbol": symbol,
            "timeframe": timeframe,
            "point_size": point_size,
            "total_rows": total_rows,
            "filtered_rows": len(filtered),
            "spread_nonzero": spread_nonzero,
            "spread_zero": spread_zero,
            "filters": {
                "decades": filters.decades or [],
                "years": filters.years or [],
                "months": filters.months or [],
                "dows": filters.dows or [],
                "hours": filters.hours or [],
            },
        },
        "intraday_bias": {
            "hours": hour_index.tolist(),
            "by_dow": intraday_bias,
        },
        "heatmaps": heatmaps,
        "calendar": calendar,
        "session_summary": session_summary,
        "session_high_low": session_high_low,
        "opportunity_windows": {
            "best_sessions": ranked_sessions[:4],
            "dead_sessions": list(reversed(ranked_sessions[-4:])),
            "best_hours": hourly_windows["best_hours"],
            "dead_hours": hourly_windows["dead_hours"],
            "hourly_rows": hourly_windows["all"],
        },
        "data_rows": data_rows,
        "data_rows_count": len(filtered),
        "data_rows_offset": data_offset,
        "data_rows_limit": data_limit,
        "extremes": extremes,
    }
