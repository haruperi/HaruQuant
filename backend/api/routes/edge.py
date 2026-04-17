"""Edge Lab API routes."""

from __future__ import annotations

import os
import hashlib
import json
from time import perf_counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.auth_utils import get_user_id_from_token
from backend.services.research.classifier import classify_symbol
from backend.services.research.config import (
    BootstrapConfig,
    DataConfig,
    EdgeLabConfig,
    MarketStructureConfig,
    PermutationConfig,
)
from backend.services.research.core_metrics import build_core_metric_profile
from backend.services.research.data import (
    CanonicalOHLCVSSchema,
    CleaningConfig,
    CleaningAction,
    DataQualityReportModel,
    DatasetIssue,
    EnrichmentConfig,
    PreparedDataset,
)
from backend.services.research.datasets import (
    DataSource,
    load_ohlc,
    normalize_columns,
    prepare_ohlcvs_dataset,
)
from backend.services.research.eds_mean_reversion import run_eds_mean_reversion
from backend.services.research.eds_null_models import run_eds_null_baseline
from backend.services.research.eds_session import run_eds_session
from backend.services.research.eds_trend_persistence import run_eds_trend_persistence
from backend.services.research.market_structure import build_market_structure_profile
from backend.services.research.market_structure_calibration import evaluate_calibration_candidates
from backend.services.research.market_structure_metric_calibration import evaluate_metric_calibration_candidates
from backend.services.research.market_structure_profile_calibration import evaluate_profile_calibration
from backend.services.research.market_structure_robustness import build_market_structure_robustness_report
from backend.services.research.market_structure_profiles import resolve_market_structure_profile
from backend.services.research.market_structure_stability import build_market_structure_stability_report
from backend.services.research.market_structure_validation import (
    build_validation_summary,
    confidence_bucket,
    label_realized_market_behavior,
)
from backend.services.research.results_schema import EdgeResult, EdgeStats
from backend.services.research.scorecard import SCORECARD_SPEC_VERSION, build_edge_lab_scorecard_report
from backend.services.research.seasonality import SeasonalityFilters, run_seasonality
from backend.services.features import FeaturePipeline, FeatureSpec
from backend.services.modeling import (
    UnsupervisedResearchConfig,
    UnsupervisedResearchService,
)
from backend.common.logger import logger
from backend.mcp.mt5_mcp.client import MT5Client
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.market_data.data_getters import load_dukascopy

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)


class EdgeLabRunRequest(BaseModel):
    """Request model for running Edge Lab analysis."""

    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    eds: str = Field(default="all")
    n_boot: int = 2000
    n_perm: int = 2000
    save_db: bool = False
    save_trades: bool = True
    prepared_dataset: Optional[Dict[str, Any]] = None


class EdgeLabSummary(BaseModel):
    """Summary of Edge Lab run results."""

    symbols: List[str]
    total_results: int
    edges_confirmed: int


class EdgeLabRunResponse(BaseModel):
    """Response model for Edge Lab run, containing results and summary."""

    results: List[Dict[str, Any]]
    summary: EdgeLabSummary


class EdgeLabSeasonalityRequest(BaseModel):
    """Request model for seasonality analysis."""

    symbol: str
    timeframe: str = "H1"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    point_size: float = 1.0
    decades: Optional[List[int]] = None
    years: Optional[List[int]] = None
    months: Optional[List[int]] = None
    dows: Optional[List[int]] = None
    hours: Optional[List[int]] = None
    data_offset: int = 0
    data_limit: int = 20
    prepared_dataset: Optional[Dict[str, Any]] = None


class EdgeCoreMetricRequest(BaseModel):
    """Request model for Core Metric MVP profile generation."""

    symbol: Optional[str] = None
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    prepared_dataset: Optional[Dict[str, Any]] = None
    save_db: bool = True


class EdgeLabDatasetRequest(BaseModel):
    """Request model for preparing a reusable Edge Lab dataset."""

    symbol: str
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    session_basis: str = "dataset_index"


class EdgeMarketStructureRequest(BaseModel):
    """Request model for Market Structure profile generation."""

    symbol: Optional[str] = None
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    prepared_dataset: Optional[Dict[str, Any]] = None
    save_db: bool = True


class EdgeProfileSnapshotRequest(BaseModel):
    """Request model for persisting one versioned Edge Lab profile snapshot."""

    dataset: Dict[str, Any]
    core_metric_profile: Dict[str, Any]
    seasonality_result: Dict[str, Any]
    market_structure_profile: Dict[str, Any]
    unsupervised_result: Optional[Dict[str, Any]] = None
    market_structure_stability: Optional[Dict[str, Any]] = None
    market_structure_robustness: Optional[Dict[str, Any]] = None
    scorecard_report: Dict[str, Any]
    artifacts: Optional[List[Dict[str, Any]]] = None


class EdgeUnsupervisedStructureRequest(BaseModel):
    """Request model for unsupervised PCA/K-Means structure analysis."""

    symbol: Optional[str] = None
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    prepared_dataset: Optional[Dict[str, Any]] = None
    save_db: bool = False
    fast_period: int = 20
    slow_period: int = 50
    n_components: int = 2
    n_clusters: int = 3
    random_state: int = 42
    forward_return_horizon: int = 1
    min_rows: int = 40
    scale_features: bool = True


class EdgeLabAutomationRequest(BaseModel):
    """Request model for automated single-symbol Edge Lab execution."""

    symbol: str
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    metric_families: Optional[List[str]] = None
    save_snapshot: bool = True
    use_cache: bool = True
    force_rerun: bool = False
    trigger_type: str = "manual"
    run_reason: Optional[str] = None


class EdgeLabAutomationBatchRequest(BaseModel):
    """Request model for automated batch Edge Lab execution."""

    symbols: List[str]
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    metric_families: Optional[List[str]] = None
    save_snapshot: bool = True
    use_cache: bool = True
    force_rerun: bool = False
    trigger_type: str = "batch_manual"
    run_reason: Optional[str] = None


class EdgeLabAutomationScheduleRequest(BaseModel):
    """Request model for scheduled Edge Lab refresh workflow."""

    symbols: List[str]
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    metric_families: Optional[List[str]] = None
    save_snapshot: bool = True
    use_cache: bool = True
    force_rerun: bool = False
    trigger_type: str = "scheduled"
    run_reason: Optional[str] = None


async def _refresh_market_structure_evaluations(
    *,
    limit: int,
    horizon_bars: int,
    authorization: str,
) -> List[Dict[str, Any]]:
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    runs = db_manager.get_market_structure_runs(limit=limit, offset=0)
    rows: List[Dict[str, Any]] = []

    for run in runs:
        report = run.get("report") or {}
        metadata = report.get("metadata") or {}
        end_value = metadata.get("end")
        if not end_value:
            continue
        try:
            end_dt = _parse_date(str(end_value))
        except Exception:
            continue
        if end_dt is None:
            continue

        data_source = str(run.get("data_source") or "mt5").lower()
        symbol = str(run.get("symbol") or "")
        timeframe = str(run.get("timeframe") or "")
        source = _create_data_source(
            data_source,
            user_id,
            end_dt,
            None,
            horizon_bars + 2,
            (end_dt.isoformat(), None),
        )

        try:
            future = load_ohlc(
                source=source,
                symbol=symbol,
                timeframe=timeframe,
                start_pos=0,
                end_pos=horizon_bars + 2,
                exclude_last_bar=False,
            )
        except Exception:
            continue

        future = normalize_columns(future)
        future = future[future.index > end_dt].head(horizon_bars)
        realized = label_realized_market_behavior(
            future,
            symbol=symbol,
            close_col="Close",
            high_col="High",
            low_col="Low",
        )
        predicted_verdict = str((run.get("summary") or {}).get("verdict") or "MIXED")
        decision_confidence = (run.get("summary") or {}).get("decision_confidence_score")
        realized_verdict = str(realized.get("realized_verdict") or "INSUFFICIENT_DATA")
        row = {
            "run_id": run.get("run_id"),
            "symbol": symbol,
            "timeframe": timeframe,
            "run_created_at": run.get("created_at"),
            "predicted_verdict": predicted_verdict,
            "realized_verdict": realized_verdict,
            "matched": predicted_verdict == realized_verdict,
            "decision_confidence_score": decision_confidence,
            "confidence_bucket": confidence_bucket(decision_confidence),
            "forward_end": future.index.max().isoformat() if len(future) else None,
            "calibration_metadata": (run.get("summary") or {}).get("calibration_metadata") or run.get("calibration_metadata") or {},
            **realized,
        }
        db_manager.save_market_structure_evaluation(row)
        rows.append(row)
    return rows


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (np.floating, float)):
        value = float(value)
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def _report_to_dict(report: DataQualityReportModel) -> Dict[str, Any]:
    return {
        "checks_performed": list(report.checks_performed),
        "warnings": [
            {
                "code": item.code,
                "severity": item.severity,
                "message": item.message,
                "count": item.count,
                "details": {k: _json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.warnings
        ],
        "fatal_errors": [
            {
                "code": item.code,
                "severity": item.severity,
                "message": item.message,
                "count": item.count,
                "details": {k: _json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.fatal_errors
        ],
        "cleaning_actions": [
            {
                "action": item.action,
                "count": item.count,
                "details": {k: _json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.cleaning_actions
        ],
        "metadata": {k: _json_safe_value(v) for k, v in report.metadata.items()},
        "is_valid": report.is_valid,
    }


def _serialize_prepared_dataset(prepared: PreparedDataset) -> Dict[str, Any]:
    frame = prepared.data.copy()
    frame = frame.reset_index().rename(columns={frame.index.name or "index": "timestamp"})
    if "timestamp" not in frame.columns:
        frame = frame.rename(columns={"index": "timestamp"})
    rows: List[Dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        rows.append({key: _json_safe_value(value) for key, value in row.items()})
    preview = rows[:200]
    return {
        "meta": {
            "symbol": prepared.report.metadata.get("symbol"),
            "timeframe": prepared.report.metadata.get("timeframe"),
            "n_rows": len(rows),
            "start": prepared.report.metadata.get("start"),
            "end": prepared.report.metadata.get("end"),
            "session_basis": prepared.report.metadata.get("session_basis"),
            "session_hours": prepared.report.metadata.get("session_hours"),
        },
        "schema": {
            "open": prepared.schema.open,
            "high": prepared.schema.high,
            "low": prepared.schema.low,
            "close": prepared.schema.close,
            "volume": prepared.schema.volume,
            "spread": prepared.schema.spread,
        },
        "report": _report_to_dict(prepared.report),
        "rows": rows,
        "preview_rows": preview,
    }


def _hash_jsonable(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _dataset_fingerprint(prepared: PreparedDataset) -> str:
    row_hashes = pd.util.hash_pandas_object(prepared.data, index=True)
    digest = hashlib.sha256()
    digest.update(row_hashes.to_numpy().tobytes())
    digest.update("|".join(str(column) for column in prepared.data.columns).encode("utf-8"))
    return digest.hexdigest()


def _deserialize_prepared_dataset(payload: Dict[str, Any]) -> PreparedDataset:
    rows = payload.get("rows") or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prepared dataset rows are required.",
        )

    frame = pd.DataFrame(rows)
    if "timestamp" not in frame.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prepared dataset timestamp column is missing.",
        )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.set_index("timestamp").sort_index()

    schema_payload = payload.get("schema") or {}
    schema = CanonicalOHLCVSSchema(
        open=str(schema_payload.get("open") or "Open"),
        high=str(schema_payload.get("high") or "High"),
        low=str(schema_payload.get("low") or "Low"),
        close=str(schema_payload.get("close") or "Close"),
        volume=str(schema_payload.get("volume") or "Volume"),
        spread=str(schema_payload.get("spread") or "Spread"),
    )

    report_payload = payload.get("report") or {}
    report = DataQualityReportModel(
        checks_performed=list(report_payload.get("checks_performed") or []),
        metadata=dict(report_payload.get("metadata") or {}),
    )
    for item in report_payload.get("warnings") or []:
        report.add_issue(
            DatasetIssue(
                code=str(item.get("code") or ""),
                severity="warning",
                message=str(item.get("message") or ""),
                count=int(item.get("count") or 0),
                details=dict(item.get("details") or {}),
            )
        )
    for item in report_payload.get("fatal_errors") or []:
        report.add_issue(
            DatasetIssue(
                code=str(item.get("code") or ""),
                severity="fatal",
                message=str(item.get("message") or ""),
                count=int(item.get("count") or 0),
                details=dict(item.get("details") or {}),
            )
        )
    for item in report_payload.get("cleaning_actions") or []:
        report.add_action(
            CleaningAction(
                action=str(item.get("action") or ""),
                count=int(item.get("count") or 0),
                details=dict(item.get("details") or {}),
            )
        )
    return PreparedDataset(data=frame, report=report, schema=schema)


def _resolve_prepared_dataset_from_payload(
    payload: Optional[Dict[str, Any]],
) -> Optional[PreparedDataset]:
    if not payload:
        return None
    return _deserialize_prepared_dataset(payload)


class MT5DataSource:
    """MT5 data source wrapper."""

    def __init__(
        self,
        user_id: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        count: Optional[int],
    ):
        """Initialize MT5DataSource."""
        self.client = self._init_client(user_id)
        self.connected = self.client is not None and self.client.is_connected()
        self.start_date = start_date
        self.end_date = end_date
        self.count = count

    def _init_client(self, user_id: int) -> Optional[MT5Client]:
        creds = db_manager.get_mt5_credentials(user_id)
        try:
            client = MT5Client()
            if not creds:
                return None
            ok = client.connect(
                path=str(creds.get("path") or ""),
                login=int(creds.get("login") or 0),
                password=str(creds.get("password") or ""),
                server=str(creds.get("server") or ""),
            )
            if not ok:
                return None
            return client if client.is_connected() else None
        except Exception as exc:
            logger.error(f"Failed to initialize MT5 client: {exc}")
            return None

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> Optional[pd.DataFrame]:
        """Fetch data from MT5."""
        if not self.connected or self.client is None:
            logger.error("MT5 not connected")
            return None

        if self.start_date:
            df = self.client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                date_from=self.start_date,
                date_to=self.end_date,
            )
        else:
            count = self.count or max(1, end_pos - start_pos)
            df = self.client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                start_pos=start_pos,
            )
        if df is None or df.empty:
            return None
        return normalize_columns(df)


class DukascopyDataSource:
    """Dukascopy data source wrapper."""

    def __init__(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        count: Optional[int],
    ):
        """Initialize DukascopyDataSource."""
        self.start_date = start_date
        self.end_date = end_date
        self.count = count

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> Optional[pd.DataFrame]:
        """Fetch data from Dukascopy."""
        df = load_dukascopy(
            symbol=symbol,
            timeframe=timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            count=self.count,
        )
        if df is None or df.empty:
            return None
        return normalize_columns(df)


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _run_single_eds(
    eds_func,
    df,
    symbol: str,
    timeframe: str,
    config: Any,
    bootstrap: BootstrapConfig,
    perm: PermutationConfig,
    error_code: str,
    **kwargs,
) -> Optional[EdgeResult]:
    """Execute a single EDS function safely."""
    try:
        return cast(
            Optional[EdgeResult],
            eds_func(df, symbol, timeframe, config, bootstrap, perm, **kwargs),
        )
    except Exception as exc:
        logger.error(f"{error_code} failed for {symbol} {timeframe}: {exc}")
        return None


def _run_eds(
    df,
    symbol: str,
    timeframe: str,
    eds_type: str,
    cfg: EdgeLabConfig,
) -> List[EdgeResult]:
    """Run selected Edge Discovery components."""
    results: List[EdgeResult] = []

    if eds_type in ("all", "null"):
        res = _run_single_eds(
            run_eds_null_baseline,
            df,
            symbol,
            timeframe,
            cfg.null,
            cfg.bootstrap,
            cfg.perm,
            "EDS-0",
        )
        if res:
            results.append(res)

    if eds_type in ("all", "mr"):
        res = _run_single_eds(
            run_eds_mean_reversion,
            df,
            symbol,
            timeframe,
            cfg.mr,
            cfg.bootstrap,
            cfg.perm,
            "EDS-1",
        )
        if res:
            results.append(res)

    if eds_type in ("all", "tp"):
        res = _run_single_eds(
            run_eds_trend_persistence,
            df,
            symbol,
            timeframe,
            cfg.tp,
            cfg.bootstrap,
            cfg.perm,
            "EDS-2",
        )
        if res:
            results.append(res)

    if eds_type in ("all", "session"):
        # Session has slightly different sig, so handle separately or wrap
        try:
            results.append(
                run_eds_session(
                    df,
                    symbol,
                    timeframe,
                    cfg.session_edge,
                    cfg.sessions,
                    cfg.bootstrap,
                    cfg.perm,
                )
            )
        except Exception as exc:
            logger.error(f"EDS-3 failed for {symbol} {timeframe}: {exc}")

    return results


def _validate_range_params(
    range_by: str,
    start_date_str: Optional[str],
    end_date_str: Optional[str],
    number_of_bars: Optional[int],
) -> Tuple[str, Optional[datetime], Optional[datetime], Optional[int]]:
    """Validate and parse common range parameters."""
    range_by = range_by.lower()
    if range_by not in ("dates", "bars"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range_by value.",
        )

    start_date = _parse_date(start_date_str) if range_by == "dates" else None
    end_date = _parse_date(end_date_str) if range_by == "dates" else None
    number_of_bars_val = number_of_bars if range_by == "bars" else None

    if range_by == "dates" and not start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date is required when range_by=dates.",
        )
    if range_by == "bars" and not number_of_bars_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="number_of_bars is required when range_by=bars.",
        )
    return range_by, start_date, end_date, number_of_bars_val


def _validate_run_request(
    request: EdgeLabRunRequest,
) -> Tuple[List[str], str, str, Optional[datetime], Optional[datetime], Optional[int]]:
    """Validate common run request parameters."""
    symbols = []
    if request.symbols:
        symbols = [s for s in request.symbols if s]
    if request.symbol:
        symbols.append(request.symbol)
    symbols = [s.strip() for s in symbols if s.strip()]

    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide symbol or symbols.",
        )

    eds_type = request.eds.lower()
    if eds_type not in ("all", "null", "mr", "tp", "session"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid EDS type.",
        )

    range_by, start_date, end_date, number_of_bars = _validate_range_params(
        request.range_by,
        request.start_date,
        request.end_date,
        request.number_of_bars,
    )

    return symbols, eds_type, range_by, start_date, end_date, number_of_bars


def _create_data_source(
    data_source: str,
    user_id: int,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    number_of_bars: Optional[int],
    string_dates: Tuple[Optional[str], Optional[str]] = (None, None),
) -> DataSource:
    """Create data source based on type."""
    if data_source == "mt5":
        mt5_source = MT5DataSource(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            count=number_of_bars,
        )
        if not mt5_source.connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MT5 not connected.",
            )
        return mt5_source
    elif data_source == "dukascopy":
        return DukascopyDataSource(
            start_date=string_dates[0],
            end_date=string_dates[1],
            count=number_of_bars,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid data_source value.",
    )


def _resolve_seasonality_symbol_info(
    source: DataSource, symbol: str, point_size: float
) -> Tuple[Optional[int], float, Optional[float]]:
    """Resolve symbol digits and point/pip sizes."""
    symbol_digits: Optional[int] = None
    resolved_point_size = point_size
    resolved_pip_size: Optional[float] = None

    if isinstance(source, MT5DataSource) and source.client:
        symbol_info = source.client.symbol_info(symbol)
        if symbol_info:
            symbol_digits = getattr(symbol_info, "digits", None)
            point_value = getattr(symbol_info, "point", None)
            if point_value:
                resolved_point_size = float(point_value or 0.0)
        if symbol_digits is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MT5 symbol digits unavailable.",
            )
        resolved_pip_size = resolved_point_size * 10

    return symbol_digits, resolved_point_size, resolved_pip_size


def _infer_digits_from_point_size(point_size: float) -> Optional[int]:
    """Infer quote display digits from point size when broker metadata is absent."""
    if point_size <= 0:
        return None
    point_text = f"{point_size:.10f}".rstrip("0")
    if "." not in point_text:
        return 0
    return len(point_text.split(".", 1)[1])


def _default_session_hours() -> Dict[str, List[int]]:
    return {
        "sydney": list(range(0, 7)),
        "tokyo": list(range(2, 9)),
        "london": list(range(10, 17)),
        "ny": list(range(15, 22)),
    }


EDGE_AUTOMATION_FAMILIES = (
    "core_metric",
    "seasonality",
    "market_structure",
    "unsupervised_structure",
    "scorecard",
)


def _expand_metric_families(metric_families: Optional[List[str]]) -> List[str]:
    requested = [str(item).strip().lower() for item in (metric_families or []) if str(item).strip()]
    if not requested:
        return list(EDGE_AUTOMATION_FAMILIES)

    expanded: List[str] = []
    if "scorecard" in requested:
        requested.extend(["market_structure", "unsupervised_structure", "seasonality", "core_metric"])
    if "market_structure" in requested:
        requested.extend(["seasonality", "core_metric"])
    if "unsupervised_structure" in requested:
        requested.extend(["core_metric"])
    if "seasonality" in requested:
        requested.extend(["core_metric"])

    for family in EDGE_AUTOMATION_FAMILIES:
        if family in requested and family not in expanded:
            expanded.append(family)
    return expanded


def _build_unsupervised_edge_payload(
    prepared: PreparedDataset,
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str],
    end_date: Optional[str],
    number_of_bars: Optional[int],
    config: Optional[UnsupervisedResearchConfig] = None,
) -> Dict[str, Any]:
    service = UnsupervisedResearchService()
    schema = prepared.schema
    frame = prepared.data.copy()
    normalized = pd.DataFrame(index=frame.index)
    for canonical_name, source_column in {
        "open": schema.open,
        "high": schema.high,
        "low": schema.low,
        "close": schema.close,
        "volume": schema.volume,
        "spread": schema.spread,
    }.items():
        if source_column in frame.columns:
            normalized[canonical_name] = pd.to_numeric(frame[source_column], errors="coerce")

    active_config = config or UnsupervisedResearchConfig()
    feature_pipeline = FeaturePipeline(
        [
            FeatureSpec(name="ema", params={"span": active_config.fast_period, "price_col": "close"}),
            FeatureSpec(name="ema", params={"span": active_config.slow_period, "price_col": "close"}),
        ],
        pipeline_version="edge_unsupervised_structure_v1",
    )
    enriched = feature_pipeline.compute_batch(normalized)
    result = service.analyze_frame(enriched, config=active_config)

    payload = result.to_metadata()
    payload.update(
        {
            "family": "unsupervised_structure",
            "symbol": symbol,
            "timeframe": timeframe,
            "data_source": data_source,
            "range_by": range_by,
            "start_date": start_date,
            "end_date": end_date,
            "number_of_bars": number_of_bars,
        }
    )

    report = dict(payload.get("report") or {})
    risk_context = dict(payload.get("risk_context") or {})
    summary = {
        "status": result.status,
        "model_version": "unsupervised_structure_v1",
        "feature_columns": list(result.feature_columns),
        "feature_set": str(payload.get("feature_metadata", {}).get("name") or active_config.feature_set),
        "cluster_count": int((report.get("clusters") or {}).get("n_clusters") or active_config.n_clusters),
        "pca_explained_variance_ratio": list((report.get("pca") or {}).get("explained_variance_ratio") or []),
        "top_risk_factors": list(report.get("risk_factors") or [])[:5],
        "top_outperforming_cluster": risk_context.get("top_outperforming_cluster"),
        "weakest_cluster": risk_context.get("weakest_cluster"),
        "guardrails": list(result.guardrails),
        "reason": result.reason,
    }
    payload["summary"] = json.loads(json.dumps(summary, default=str))
    return json.loads(json.dumps(payload, default=str))


def _dataset_request_meta(
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str],
    end_date: Optional[str],
    number_of_bars: Optional[int],
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data_source": data_source,
        "range_by": range_by,
        "start_date": start_date,
        "end_date": end_date,
        "number_of_bars": number_of_bars,
        "session_basis": "dataset_index",
        "session_hours": _default_session_hours(),
    }


def _extract_point_and_pip_size(prepared: PreparedDataset, symbol: str) -> Tuple[float, float]:
    point_size = 1.0
    pip_size = 1.0
    if len(prepared.data) > 0:
        first = prepared.data.iloc[0]
        point_size = float(first.get("point_size", point_size) or point_size)
        pip_size = float(first.get("pip_size", pip_size) or pip_size)
    if point_size <= 0:
        point_size = 1.0
    if pip_size <= 0:
        pip_size = point_size * (10 if symbol.upper().endswith("JPY") else 1)
    return point_size, pip_size


def _build_automation_metadata(
    *,
    trigger_type: str,
    run_reason: Optional[str],
    requested_families: List[str],
    recomputed_families: List[str],
    reused_families: List[str],
    cache_hit: bool,
    cache_policy: str,
    dependency_policy: str,
    partial_snapshot: bool,
    stage_timings: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    return {
        "trigger_type": trigger_type,
        "run_reason": run_reason,
        "requested_families": requested_families,
        "recomputed_families": recomputed_families,
        "reused_families": reused_families,
        "cache_hit": cache_hit,
        "cache_policy": cache_policy,
        "dependency_policy": dependency_policy,
        "partial_snapshot": partial_snapshot,
        "stage_timings": stage_timings or {},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


def _run_edge_lab_symbol_profile_sync(
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str],
    end_date: Optional[str],
    number_of_bars: Optional[int],
    metric_families: Optional[List[str]],
    save_snapshot: bool,
    use_cache: bool,
    force_rerun: bool,
    trigger_type: str,
    run_reason: Optional[str],
    user_id: int,
) -> Dict[str, Any]:
    run_started = perf_counter()
    range_by, parsed_start, parsed_end, validated_bars = _validate_range_params(
        range_by,
        start_date,
        end_date,
        number_of_bars,
    )
    expanded_families = _expand_metric_families(metric_families)
    cache_policy = "reuse_latest_matching_snapshot"
    dependency_policy = "scorecard->market_structure+unsupervised_structure->seasonality->core_metric"
    stage_timings: Dict[str, float] = {}

    dataset_started = perf_counter()
    source = _create_data_source(
        data_source.lower(),
        user_id,
        parsed_start,
        parsed_end,
        validated_bars,
        (start_date, end_date),
    )
    prepared = prepare_ohlcvs_dataset(
        source=source,
        symbol=symbol,
        timeframe=timeframe,
        start_pos=0,
        end_pos=validated_bars or 5000,
        cleaning=CleaningConfig(timeframe=timeframe),
        enrichment=EnrichmentConfig(symbol=symbol, session_basis="dataset_index"),
    )
    dataset_payload = _serialize_prepared_dataset(prepared)
    dataset_payload["request"] = _dataset_request_meta(
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source.lower(),
        range_by=range_by,
        start_date=start_date,
        end_date=end_date,
        number_of_bars=validated_bars,
    )
    cfg = MarketStructureConfig()
    dataset_payload["meta"]["dataset_fingerprint"] = _dataset_fingerprint(prepared)
    dataset_payload["meta"]["config_fingerprint"] = _hash_jsonable(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "data_source": data_source.lower(),
            "range_by": range_by,
            "start_date": start_date,
            "end_date": end_date,
            "number_of_bars": validated_bars,
            "model_version": cfg.model_version,
            "baseline_id": cfg.baseline_id,
        }
    )
    dataset_payload["meta"]["score_spec_version"] = SCORECARD_SPEC_VERSION
    stage_timings["dataset_prepare_seconds"] = round(perf_counter() - dataset_started, 6)

    cached_snapshot: Optional[Dict[str, Any]] = None
    if use_cache and not force_rerun and expanded_families == list(EDGE_AUTOMATION_FAMILIES):
        cache_started = perf_counter()
        cached_snapshot = db_manager.find_matching_profile_snapshot(
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source.lower(),
            range_by=range_by,
            start=str(dataset_payload.get("meta", {}).get("start") or ""),
            end=str(dataset_payload.get("meta", {}).get("end") or ""),
            row_count=int(dataset_payload.get("meta", {}).get("n_rows") or 0),
            dataset_fingerprint=str(dataset_payload["meta"].get("dataset_fingerprint") or ""),
            config_fingerprint=str(dataset_payload["meta"].get("config_fingerprint") or ""),
            model_version=cfg.model_version,
            baseline_id=cfg.baseline_id,
        )
        if cached_snapshot is not None:
            stage_timings["cache_lookup_seconds"] = round(perf_counter() - cache_started, 6)
            stage_timings["total_seconds"] = round(perf_counter() - run_started, 6)
            metadata = _build_automation_metadata(
                trigger_type=trigger_type,
                run_reason=run_reason,
                requested_families=metric_families or list(EDGE_AUTOMATION_FAMILIES),
                recomputed_families=[],
                reused_families=list(EDGE_AUTOMATION_FAMILIES),
                cache_hit=True,
                cache_policy=cache_policy,
                dependency_policy=dependency_policy,
                partial_snapshot=False,
                stage_timings=stage_timings,
            )
            cached_snapshot["automation_metadata"] = metadata
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "cached",
                "snapshot": cached_snapshot,
                "automation_metadata": metadata,
            }

    previous_snapshot = None if force_rerun else db_manager.find_matching_profile_snapshot(
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source.lower(),
        range_by=range_by,
        start=str(dataset_payload.get("meta", {}).get("start") or ""),
        end=str(dataset_payload.get("meta", {}).get("end") or ""),
        row_count=int(dataset_payload.get("meta", {}).get("n_rows") or 0),
        dataset_fingerprint=str(dataset_payload["meta"].get("dataset_fingerprint") or ""),
        config_fingerprint=str(dataset_payload["meta"].get("config_fingerprint") or ""),
        limit=10,
    )

    recomputed: List[str] = []
    reused: List[str] = []

    core_metric_profile: Dict[str, Any]
    if "core_metric" in expanded_families:
        stage_started = perf_counter()
        core_metric_profile = build_core_metric_profile(
            prepared,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source.lower(),
            range_by=range_by,
            start_date=start_date,
            end_date=end_date,
            number_of_bars=validated_bars,
        ).to_dict()
        recomputed.append("core_metric")
        stage_timings["core_metric_seconds"] = round(perf_counter() - stage_started, 6)
    elif previous_snapshot:
        core_metric_profile = {
            "symbol": symbol,
            "timeframe": timeframe,
            "data_source": data_source.lower(),
            "range_by": range_by,
            "summary": previous_snapshot.get("core_metric_summary") or {},
        }
        reused.append("core_metric")
    else:
        raise HTTPException(status_code=400, detail="Partial recompute requested without a reusable prior core metric snapshot.")

    seasonality_result: Dict[str, Any]
    if "seasonality" in expanded_families:
        stage_started = perf_counter()
        point_size, pip_size = _extract_point_and_pip_size(prepared, symbol)
        seasonality_result = run_seasonality(
            prepared.data,
            symbol=symbol,
            timeframe=timeframe,
            point_size=point_size,
            pip_size=pip_size,
            filters=SeasonalityFilters(),
            data_offset=0,
            data_limit=20,
        )
        seasonality_result.setdefault("meta", {})["digits"] = _infer_digits_from_point_size(point_size)
        recomputed.append("seasonality")
        stage_timings["seasonality_seconds"] = round(perf_counter() - stage_started, 6)
    elif previous_snapshot:
        seasonality_result = dict(previous_snapshot.get("seasonality_summary") or {})
        reused.append("seasonality")
    else:
        raise HTTPException(status_code=400, detail="Partial recompute requested without a reusable prior seasonality snapshot.")

    market_structure_profile: Dict[str, Any]
    if "market_structure" in expanded_families:
        stage_started = perf_counter()
        market_structure_profile = build_market_structure_profile(
            prepared,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source.lower(),
            range_by=range_by,
            start_date=start_date,
            end_date=end_date,
            number_of_bars=validated_bars,
        ).to_dict()
        recomputed.append("market_structure")
        stage_timings["market_structure_seconds"] = round(perf_counter() - stage_started, 6)
    elif previous_snapshot:
        market_summary = dict(previous_snapshot.get("market_structure_summary", {}).get("summary") or {})
        market_structure_profile = {
            "symbol": symbol,
            "timeframe": timeframe,
            "data_source": data_source.lower(),
            "range_by": range_by,
            "summary": market_summary,
        }
        reused.append("market_structure")
    else:
        raise HTTPException(status_code=400, detail="Partial recompute requested without a reusable prior market structure snapshot.")

    unsupervised_result: Dict[str, Any]
    if "unsupervised_structure" in expanded_families:
        stage_started = perf_counter()
        unsupervised_result = _build_unsupervised_edge_payload(
            prepared,
            symbol=symbol,
            timeframe=timeframe,
            data_source=data_source.lower(),
            range_by=range_by,
            start_date=start_date,
            end_date=end_date,
            number_of_bars=validated_bars,
            config=UnsupervisedResearchConfig(),
        )
        recomputed.append("unsupervised_structure")
        stage_timings["unsupervised_structure_seconds"] = round(perf_counter() - stage_started, 6)
    elif previous_snapshot:
        unsupervised_result = dict(previous_snapshot.get("unsupervised_summary") or {})
        reused.append("unsupervised_structure")
    else:
        raise HTTPException(status_code=400, detail="Partial recompute requested without a reusable prior unsupervised snapshot.")

    scorecard_report: Optional[Dict[str, Any]] = None
    if "scorecard" in expanded_families:
        stage_started = perf_counter()
        scorecard_report = build_edge_lab_scorecard_report(
            dataset=dataset_payload,
            core_metric_profile=core_metric_profile,
            seasonality_result=seasonality_result,
            market_structure_profile=market_structure_profile,
            stability=None,
            robustness=None,
        )
        recomputed.append("scorecard")
        stage_timings["scorecard_seconds"] = round(perf_counter() - stage_started, 6)
    elif previous_snapshot:
        scorecard_report = dict(previous_snapshot.get("scorecard_summary") or {})
        reused.append("scorecard")

    partial_snapshot = expanded_families != list(EDGE_AUTOMATION_FAMILIES)
    automation_metadata = _build_automation_metadata(
        trigger_type=trigger_type,
        run_reason=run_reason,
        requested_families=metric_families or list(EDGE_AUTOMATION_FAMILIES),
        recomputed_families=recomputed,
        reused_families=reused,
        cache_hit=False,
        cache_policy=cache_policy,
        dependency_policy=dependency_policy,
        partial_snapshot=partial_snapshot,
        stage_timings=stage_timings,
    )

    snapshot = None
    snapshot_saved = False
    if save_snapshot and "scorecard" in recomputed and scorecard_report is not None:
        stage_started = perf_counter()
        snapshot_payload = {
            "dataset": dataset_payload,
            "core_metric_profile": core_metric_profile,
            "seasonality_result": seasonality_result,
            "market_structure_profile": market_structure_profile,
            "unsupervised_result": unsupervised_result,
            "market_structure_stability": None,
            "market_structure_robustness": None,
            "scorecard_report": scorecard_report,
            "automation_metadata": automation_metadata,
            "artifacts": [],
        }
        snapshot_id = db_manager.save_profile_snapshot(snapshot_payload, user_id=user_id)
        if snapshot_id is not None:
            snapshot = db_manager.get_profile_snapshot(snapshot_id)
            snapshot_saved = snapshot is not None
        stage_timings["snapshot_persist_seconds"] = round(perf_counter() - stage_started, 6)

    stage_timings["total_seconds"] = round(perf_counter() - run_started, 6)
    automation_metadata["stage_timings"] = stage_timings

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "completed",
        "dataset_meta": dataset_payload.get("meta") or {},
        "core_metric_summary": core_metric_profile.get("summary") or {},
        "seasonality_meta": seasonality_result.get("meta") or {},
        "market_structure_summary": market_structure_profile.get("summary") or {},
        "unsupervised_summary": dict(unsupervised_result.get("summary") or {}),
        "scorecard_summary": {
            "final_score": scorecard_report.get("finalScore") if scorecard_report else None,
            "final_label": scorecard_report.get("finalLabel") if scorecard_report else None,
            "overall_confidence": scorecard_report.get("overallConfidence") if scorecard_report else None,
            "score_spec_version": scorecard_report.get("scoreSpecVersion") if scorecard_report else None,
            "research_ready": scorecard_report.get("research_ready") if scorecard_report else None,
            "readiness_label": scorecard_report.get("readiness_label") if scorecard_report else None,
            "readiness_reasons": scorecard_report.get("readiness_reasons") if scorecard_report else [],
        },
        "snapshot_saved": snapshot_saved,
        "snapshot": snapshot,
        "automation_metadata": automation_metadata,
    }


def run_scheduled_edge_lab_refresh() -> Dict[str, Any]:
    """Run one scheduled Edge Lab batch refresh from environment configuration."""
    symbols = [item.strip() for item in os.getenv("EDGE_LAB_BATCH_SYMBOLS", "").split(",") if item.strip()]
    if not symbols:
        return {"status": "skipped", "reason": "EDGE_LAB_BATCH_SYMBOLS not configured"}

    request = EdgeLabAutomationBatchRequest(
        symbols=symbols,
        timeframe=os.getenv("EDGE_LAB_BATCH_TIMEFRAME", "M15"),
        data_source=os.getenv("EDGE_LAB_BATCH_SOURCE", "mt5"),
        range_by=os.getenv("EDGE_LAB_BATCH_RANGE_BY", "bars"),
        start_date=os.getenv("EDGE_LAB_BATCH_START") or None,
        end_date=os.getenv("EDGE_LAB_BATCH_END") or None,
        number_of_bars=int(os.getenv("EDGE_LAB_BATCH_BARS", "1500") or 1500),
        metric_families=None,
        save_snapshot=True,
        use_cache=True,
        force_rerun=False,
        trigger_type="scheduled",
        run_reason="scheduler_refresh",
    )
    results = [
        _run_edge_lab_symbol_profile_sync(
            symbol=symbol,
            timeframe=request.timeframe,
            data_source=request.data_source,
            range_by=request.range_by,
            start_date=request.start_date,
            end_date=request.end_date,
            number_of_bars=request.number_of_bars,
            metric_families=request.metric_families,
            save_snapshot=request.save_snapshot,
            use_cache=request.use_cache,
            force_rerun=request.force_rerun,
            trigger_type=request.trigger_type,
            run_reason=request.run_reason,
            user_id=1,
        )
        for symbol in request.symbols
    ]
    return {
        "status": "completed",
        "run_count": len(results),
        "results": results,
    }


@router.post("/run", response_model=EdgeLabRunResponse, status_code=status.HTTP_200_OK)
async def run_edge_lab(request: EdgeLabRunRequest, authorization: str = AUTH_HEADER):
    """Run Edge Lab analysis."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1
    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)

    if prepared is None:
        symbols, eds_type, range_by, start_date, end_date, number_of_bars = (
            _validate_run_request(request)
        )

        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or request.symbol or "")
        timeframe = str(meta.get("timeframe") or request.timeframe)
        request.symbol = symbol
        request.timeframe = timeframe
        request.symbols = [symbol]
        symbols = [symbol]
        eds_type = request.eds.lower()
        if eds_type not in ("all", "null", "mr", "tp", "session"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid EDS type.",
            )
        range_by = str(
            (request.prepared_dataset or {}).get("request", {}).get("range_by")
            or request.range_by
        )
        number_of_bars = (
            (request.prepared_dataset or {}).get("request", {}).get("number_of_bars")
            or request.number_of_bars
        )
        start_date = None
        end_date = None
        source = None

    all_results: List[EdgeResult] = []

    for symbol in symbols:
        cfg = EdgeLabConfig(
            data=DataConfig(
                symbol=symbol,
                timeframe=request.timeframe,
                end_pos=number_of_bars or 5000,
            ),
            bootstrap=BootstrapConfig(n_boot=request.n_boot),
            perm=PermutationConfig(n_perm=request.n_perm),
        )

        if prepared is None:
            try:
                df = load_ohlc(
                    source=source,
                    symbol=cfg.data.symbol,
                    timeframe=cfg.data.timeframe,
                    start_pos=cfg.data.start_pos,
                    end_pos=cfg.data.end_pos,
                    exclude_last_bar=cfg.data.exclude_last_bar,
                )
            except Exception as exc:
                logger.error(f"Failed to load data for {symbol}: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to load data for {symbol}.",
                )
        else:
            df = prepared.data.copy()

        results = _run_eds(
            df=df,
            symbol=symbol,
            timeframe=request.timeframe,
            eds_type=eds_type,
            cfg=cfg,
        )

        run_meta = {
            "data_source": request.data_source.lower(),
            "range_by": range_by,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "number_of_bars": number_of_bars,
        }
        for res in results:
            res.config = {**(res.config or {}), "run_meta": run_meta}

        all_results.extend(results)

        if request.save_db:
            for res in results:
                db_manager.save_edge_result(
                    result=res.to_dict(),
                    user_id=user_id,
                    save_trades=request.save_trades,
                )

    edges_confirmed = sum(1 for res in all_results if res.stats.edge_confirmed)
    response = EdgeLabRunResponse(
        results=[res.to_dict() for res in all_results],
        summary=EdgeLabSummary(
            symbols=symbols,
            total_results=len(all_results),
            edges_confirmed=edges_confirmed,
        ),
    )
    return response


@router.get("/runs", response_model=List[Dict[str, Any]])
async def list_edge_runs(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    eds_type: Optional[str] = None,
    verdict: Optional[str] = None,
    edge_confirmed_only: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    """List edge analysis runs."""
    return db_manager.get_edge_runs(
        symbol=symbol,
        timeframe=timeframe,
        eds_type=eds_type,
        verdict=verdict,
        edge_confirmed_only=edge_confirmed_only,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/count", response_model=Dict[str, int])
async def count_edge_runs(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    eds_type: Optional[str] = None,
    verdict: Optional[str] = None,
    edge_confirmed_only: bool = False,
):
    """Count edge analysis runs."""
    total = db_manager.get_edge_runs_count(
        symbol=symbol,
        timeframe=timeframe,
        eds_type=eds_type,
        verdict=verdict,
        edge_confirmed_only=edge_confirmed_only,
    )
    return {"total": total}


def _range_label(meta: Dict[str, Any]) -> str:
    if not meta:
        return "-"
    if meta.get("range_by") == "dates" and meta.get("start_date"):
        start_date = meta.get("start_date")
        end_date = meta.get("end_date") or "now"
        if isinstance(start_date, str) and len(start_date) == 10:
            start_date = f"{start_date} 00:00"
        if isinstance(end_date, str) and len(end_date) == 10:
            end_date = f"{end_date} 23:00"
        return f"{start_date} - {end_date}"
    if meta.get("range_by") == "bars" and meta.get("number_of_bars"):
        return f"bars: {meta.get('number_of_bars')}"
    return "-"


def _pack_run(run: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not run:
        return {
            "run_id": None,
            "expectancy_r": None,
            "ci_low": None,
            "p_value_perm": None,
            "n_trades": None,
            "total_r": None,
            "verdict": None,
        }
    extras = run.get("extras") or {}
    return {
        "run_id": run.get("run_id"),
        "expectancy_r": run.get("expectancy_r"),
        "ci_low": run.get("ci_low"),
        "p_value_perm": run.get("p_value_perm"),
        "n_trades": run.get("n_trades"),
        "total_r": extras.get("total_r"),
        "verdict": run.get("verdict"),
    }


def _to_edge_result(run: Optional[Dict[str, Any]]) -> Optional[EdgeResult]:
    if not run:
        return None
    expectancy_r = run.get("expectancy_r")
    ci_low = run.get("ci_low")
    ci_high = run.get("ci_high")
    p_value_perm = run.get("p_value_perm")
    win_rate = run.get("win_rate")
    profit_factor = run.get("profit_factor")
    return EdgeResult(
        symbol=run.get("symbol") or "",
        timeframe=run.get("timeframe") or "",
        eds_name=run.get("eds_name") or "",
        config=run.get("config") or {},
        stats=EdgeStats(
            n_trades=int(run.get("n_trades") or 0),
            expectancy_r=float(expectancy_r) if expectancy_r is not None else 0.0,
            win_rate=float(win_rate) if win_rate is not None else 0.0,
            profit_factor=float(profit_factor) if profit_factor is not None else 0.0,
            median_mae_r=float("nan"),
            median_mfe_r=float("nan"),
            avg_hold_bars=float("nan"),
            ci_low=float(ci_low) if ci_low is not None else 0.0,
            ci_high=float(ci_high) if ci_high is not None else 0.0,
            p_value_perm=float(p_value_perm) if p_value_perm is not None else 1.0,
            extras=run.get("extras") or {},
        ),
        trades=[],
    )


@router.get("/runs/summary", response_model=Dict[str, Any])
async def get_edge_run_summary(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    verdict: Optional[str] = None,
    edge_confirmed_only: bool = False,
    sort_by: str = "latest_created_at",
    sort_dir: str = "desc",
    limit: int = 25,
    offset: int = 0,
):
    """Get summary of edge analysis runs."""
    rows = db_manager.get_edge_summary_rows(symbol=symbol, timeframe=timeframe)

    summary_rows: List[Dict[str, Any]] = []
    for row in rows:
        classification_result = classify_symbol(
            _to_edge_result(row.get("mr")),
            _to_edge_result(row.get("bo")),
        )
        classification = classification_result.edge_class.value

        if verdict and classification != verdict:
            continue
        if edge_confirmed_only and classification == "No Clear Edge":
            continue

        summary_rows.append(
            {
                "symbol": row.get("symbol"),
                "timeframe": row.get("timeframe"),
                "latest_run_id": row.get("latest_run_id"),
                "latest_created_at": row.get("latest_created_at"),
                "verdict": classification,
                "confidence": classification_result.confidence,
                "robustness": classification_result.robustness,
                "score_breakdown": classification_result.breakdown,
                "range": _range_label(row.get("range_meta") or {}),
                "mr": _pack_run(row.get("mr")),
                "bo": _pack_run(row.get("bo")),
            }
        )

    total = len(summary_rows)
    reverse = sort_dir.lower() != "asc"
    if sort_by == "symbol":
        summary_rows.sort(
            key=lambda item: str(item.get("symbol") or ""), reverse=reverse
        )
    elif sort_by == "verdict":
        summary_rows.sort(
            key=lambda item: str(item.get("verdict") or ""), reverse=reverse
        )
    elif sort_by == "mr_expectancy":
        summary_rows.sort(
            key=lambda item: float(
                (item.get("mr") or {}).get("expectancy_r") or -999999.0
            ),
            reverse=reverse,
        )
    elif sort_by == "bo_expectancy":
        summary_rows.sort(
            key=lambda item: float(
                (item.get("bo") or {}).get("expectancy_r") or -999999.0
            ),
            reverse=reverse,
        )
    elif sort_by == "confidence":
        summary_rows.sort(
            key=lambda item: float(item.get("confidence") or 0.0),
            reverse=reverse,
        )
    else:
        summary_rows.sort(
            key=lambda item: str(item.get("latest_created_at") or ""),
            reverse=reverse,
        )
    paged = summary_rows[offset : offset + limit]

    return {"total": total, "rows": paged}


@router.post("/dataset/prepare", response_model=Dict[str, Any])
async def prepare_edge_lab_dataset(
    request: EdgeLabDatasetRequest,
    authorization: str = AUTH_HEADER,
):
    """Prepare and serialize a reusable Edge Lab dataset."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    range_by, start_date, end_date, number_of_bars = _validate_range_params(
        request.range_by,
        request.start_date,
        request.end_date,
        request.number_of_bars,
    )
    source = _create_data_source(
        request.data_source.lower(),
        user_id,
        start_date,
        end_date,
        number_of_bars,
        (request.start_date, request.end_date),
    )
    session_hours = _default_session_hours()
    prepared = prepare_ohlcvs_dataset(
        source=source,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_pos=0,
        end_pos=number_of_bars or 5000,
        cleaning=CleaningConfig(timeframe=request.timeframe),
        enrichment=EnrichmentConfig(
            symbol=request.symbol,
            session_basis=request.session_basis,
        ),
    )
    payload = _serialize_prepared_dataset(prepared)
    payload["request"] = {
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "data_source": request.data_source.lower(),
        "range_by": range_by,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "number_of_bars": number_of_bars,
        "session_basis": request.session_basis,
        "session_hours": session_hours,
    }
    return payload


@router.post("/seasonality", response_model=Dict[str, Any])
async def run_seasonality_lab(
    request: EdgeLabSeasonalityRequest,
    authorization: str = AUTH_HEADER,
):
    """Run seasonality analysis."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol_digits: Optional[int] = None
    resolved_point_size = request.point_size
    resolved_pip_size: Optional[float] = None
    session_basis = "dataset_index"
    session_hours = _default_session_hours()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        symbol_digits, resolved_point_size, resolved_pip_size = (
            _resolve_seasonality_symbol_info(source, request.symbol, request.point_size)
        )
        session_basis = "dataset_index"
        try:
            df = load_ohlc(
                source=source,
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_pos=0,
                end_pos=number_of_bars or 5000,
            )
        except Exception as exc:
            logger.error(f"Failed to load data for {request.symbol}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load data for {request.symbol}.",
            )
        df = normalize_columns(df)
    else:
        df = prepared.data
        meta = prepared.report.metadata
        request.symbol = str(meta.get("symbol") or request.symbol)
        request.timeframe = str(meta.get("timeframe") or request.timeframe)
        range_by = str((request.prepared_dataset or {}).get("request", {}).get("range_by") or request.range_by)
        session_basis = str(meta.get("session_basis") or session_basis)
        session_hours = dict(meta.get("session_hours") or session_hours)
        resolved_pip_size = float(df.get("pip_size", pd.Series([request.point_size])).iloc[0])
        resolved_point_size = float(df.get("point_size", pd.Series([request.point_size])).iloc[0])
        symbol_digits = _infer_digits_from_point_size(resolved_point_size)

    if symbol_digits is None:
        symbol_digits = _infer_digits_from_point_size(resolved_point_size)

    if resolved_point_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="point_size must be > 0.",
        )
    if request.data_offset < 0 or request.data_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_offset must be >= 0 and data_limit must be > 0.",
        )
    filters = SeasonalityFilters(
        decades=request.decades,
        years=request.years,
        months=request.months,
        dows=request.dows,
        hours=request.hours,
    )
    result = run_seasonality(
        df,
        symbol=request.symbol,
        timeframe=request.timeframe,
        point_size=resolved_point_size,
        pip_size=resolved_pip_size,
        filters=filters,
        data_offset=request.data_offset,
        data_limit=request.data_limit,
    )

    result_meta = result.get("meta", {})
    result_meta.update(
        {
            "data_source": request.data_source,
            "range_by": range_by,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "number_of_bars": number_of_bars,
            "timezone": "broker",
            "digits": symbol_digits,
            "session_basis": session_basis,
            "session_hours": session_hours,
        }
    )
    result["meta"] = result_meta
    return result


@router.get("/runs/{run_id}", response_model=Dict[str, Any])
async def get_edge_run(run_id: int):
    """Get specific Edge Lab run."""
    run = db_manager.get_edge_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge run {run_id} not found.",
        )
    return run


@router.get("/runs/{run_id}/stats", response_model=Dict[str, Any])
async def get_edge_run_stats(run_id: int):
    """Get stats for a specific Edge Lab run."""
    stats = db_manager.get_edge_stats(run_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge stats for run {run_id} not found.",
        )
    return stats


@router.get("/runs/{run_id}/trades", response_model=List[Dict[str, Any]])
async def get_edge_run_trades(run_id: int):
    """Get trades for a specific Edge Lab run."""
    return db_manager.get_edge_trades(run_id)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge_run(run_id: int):
    """Delete an Edge Lab run."""
    success = db_manager.delete_edge_run(run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge run {run_id} not found.",
        )
    return None


@router.post("/core-metrics/run", response_model=Dict[str, Any])
async def run_core_metrics(
    request: EdgeCoreMetricRequest,
    authorization: str = AUTH_HEADER,
):
    """Run the Core Metric MVP profile for one symbol."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol = request.symbol or ""
    timeframe = request.timeframe
    data_source = request.data_source.lower()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=number_of_bars or 5000,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or symbol)
        timeframe = str(meta.get("timeframe") or timeframe)
        data_source = str(
            (request.prepared_dataset or {}).get("request", {}).get("data_source")
            or data_source
        )
        range_by = str(
            (request.prepared_dataset or {}).get("request", {}).get("range_by")
            or range_by
        )

    profile = build_core_metric_profile(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=number_of_bars,
    )

    saved_run_id: Optional[int] = None
    if request.save_db:
        saved_run_id = db_manager.save_core_metric_profile(profile, user_id=user_id)

    payload = profile.to_dict()
    payload["run_id"] = saved_run_id
    return payload


@router.get("/core-metrics/runs", response_model=List[Dict[str, Any]])
async def list_core_metric_runs(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List stored Core Metric profile runs."""
    return db_manager.get_core_metric_runs(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )


@router.get("/core-metrics/runs/{run_id}", response_model=Dict[str, Any])
async def get_core_metric_run(run_id: int):
    """Get one stored Core Metric profile."""
    run = db_manager.get_core_metric_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Core metric run {run_id} not found.",
        )
    return run


@router.delete("/core-metrics/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_core_metric_run(run_id: int):
    """Delete a stored Core Metric profile."""
    success = db_manager.delete_core_metric_run(run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Core metric run {run_id} not found.",
        )
    return None


@router.post("/market-structure/run", response_model=Dict[str, Any])
async def run_market_structure(
    request: EdgeMarketStructureRequest,
    authorization: str = AUTH_HEADER,
):
    """Run the Market Structure profile for one symbol."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol = request.symbol or ""
    timeframe = request.timeframe
    data_source = request.data_source.lower()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=number_of_bars or 5000,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or symbol)
        timeframe = str(meta.get("timeframe") or timeframe)
        data_source = str(
            (request.prepared_dataset or {}).get("request", {}).get("data_source")
            or data_source
        )
        range_by = str(
            (request.prepared_dataset or {}).get("request", {}).get("range_by")
            or range_by
        )

    profile = build_market_structure_profile(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=number_of_bars,
    )

    saved_run_id: Optional[int] = None
    if request.save_db:
        saved_run_id = db_manager.save_market_structure_profile(profile, user_id=user_id)

    payload = profile.to_dict()
    payload["run_id"] = saved_run_id
    return payload


@router.post("/unsupervised-structure/run", response_model=Dict[str, Any])
async def run_unsupervised_structure(
    request: EdgeUnsupervisedStructureRequest,
    authorization: str = AUTH_HEADER,
):
    """Run PCA/K-Means unsupervised structure analysis for one symbol."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol = request.symbol or ""
    timeframe = request.timeframe
    data_source = request.data_source.lower()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=number_of_bars or 5000,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or symbol)
        timeframe = str(meta.get("timeframe") or timeframe)
        data_source = str((request.prepared_dataset or {}).get("request", {}).get("data_source") or data_source)
        range_by = str((request.prepared_dataset or {}).get("request", {}).get("range_by") or range_by)

    payload = _build_unsupervised_edge_payload(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=number_of_bars,
        config=UnsupervisedResearchConfig(
            fast_period=request.fast_period,
            slow_period=request.slow_period,
            n_components=request.n_components,
            n_clusters=request.n_clusters,
            random_state=request.random_state,
            forward_return_horizon=request.forward_return_horizon,
            min_rows=request.min_rows,
            scale_features=request.scale_features,
        ),
    )
    payload["run_id"] = None
    return payload


@router.get("/market-structure/runs", response_model=List[Dict[str, Any]])
async def list_market_structure_runs(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List stored Market Structure runs."""
    return db_manager.get_market_structure_runs(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )


@router.get("/market-structure/runs/{run_id}", response_model=Dict[str, Any])
async def get_market_structure_run(run_id: int):
    """Get one stored Market Structure profile."""
    run = db_manager.get_market_structure_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend structure run {run_id} not found.",
        )
    return run


@router.delete("/market-structure/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_structure_run(run_id: int):
    """Delete a stored Market Structure profile."""
    success = db_manager.delete_market_structure_run(run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend structure run {run_id} not found.",
        )
    return None


@router.get("/market-structure/validation", response_model=Dict[str, Any])
async def get_market_structure_validation(
    limit: int = 20,
    horizon_bars: int = 48,
    refresh: bool = True,
    authorization: str = AUTH_HEADER,
):
    """Validate saved Market Structure runs against simple forward realized behavior."""
    rows = (
        await _refresh_market_structure_evaluations(
            limit=limit,
            horizon_bars=horizon_bars,
            authorization=authorization,
        )
        if refresh
        else db_manager.get_market_structure_evaluations(limit=limit, offset=0)
    )

    return {
        "summary": build_validation_summary(rows),
        "rows": rows,
    }


@router.get("/market-structure/evaluations", response_model=List[Dict[str, Any]])
async def list_market_structure_evaluations(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List persisted Market Structure forward-evaluation rows."""
    return db_manager.get_market_structure_evaluations(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )


@router.post("/market-structure/evaluations/refresh", response_model=Dict[str, Any])
async def refresh_market_structure_evaluations(
    limit: int = 100,
    horizon_bars: int = 48,
    authorization: str = AUTH_HEADER,
):
    """Refresh persisted Market Structure forward-evaluation rows."""
    rows = await _refresh_market_structure_evaluations(
        limit=limit,
        horizon_bars=horizon_bars,
        authorization=authorization,
    )
    return {
        "summary": build_validation_summary(rows),
        "rows": rows,
    }


@router.get("/market-structure/calibration", response_model=Dict[str, Any])
async def get_market_structure_calibration(
    limit: int = 50,
    horizon_bars: int = 48,
    authorization: str = AUTH_HEADER,
):
    """Evaluate a small grid of top-level verdict thresholds against forward validation rows."""
    persisted = db_manager.get_market_structure_evaluations(limit=limit, offset=0)
    validation_rows = persisted or await _refresh_market_structure_evaluations(
        limit=limit,
        horizon_bars=horizon_bars,
        authorization=authorization,
    )
    runs = db_manager.get_market_structure_runs(limit=limit, offset=0)
    return evaluate_calibration_candidates(runs, validation_rows)


@router.get("/market-structure/profile-calibration", response_model=Dict[str, Any])
async def get_market_structure_profile_calibration(
    limit: int = 100,
    horizon_bars: int = 48,
    authorization: str = AUTH_HEADER,
):
    """Group calibration results by symbol/timeframe profile class."""
    persisted = db_manager.get_market_structure_evaluations(limit=limit, offset=0)
    validation_rows = persisted or await _refresh_market_structure_evaluations(
        limit=limit,
        horizon_bars=horizon_bars,
        authorization=authorization,
    )
    runs = db_manager.get_market_structure_runs(limit=limit, offset=0)
    return evaluate_profile_calibration(runs, validation_rows)


@router.get("/market-structure/metric-calibration", response_model=Dict[str, Any])
async def get_market_structure_metric_calibration(
    limit: int = 50,
    horizon_bars: int = 48,
    authorization: str = AUTH_HEADER,
):
    """Evaluate a small grid of lower-level score normalization bands."""
    persisted = db_manager.get_market_structure_evaluations(limit=limit, offset=0)
    validation_rows = persisted or await _refresh_market_structure_evaluations(
        limit=limit,
        horizon_bars=horizon_bars,
        authorization=authorization,
    )
    runs = db_manager.get_market_structure_runs(limit=limit, offset=0)
    detailed_runs = []
    for run in runs:
        run_id = int(run.get("run_id") or 0)
        detail = db_manager.get_market_structure_run(run_id)
        if detail:
            detailed_runs.append(detail)
    return evaluate_metric_calibration_candidates(detailed_runs, validation_rows)


@router.post("/market-structure/stability", response_model=Dict[str, Any])
async def get_market_structure_stability(
    request: EdgeMarketStructureRequest,
    authorization: str = AUTH_HEADER,
):
    """Evaluate block-by-block Market Structure stability on the current dataset."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol = request.symbol or ""
    timeframe = request.timeframe
    data_source = request.data_source.lower()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=number_of_bars or 5000,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or symbol)
        timeframe = str(meta.get("timeframe") or timeframe)
        data_source = str(
            (request.prepared_dataset or {}).get("request", {}).get("data_source")
            or data_source
        )
        range_by = str(
            (request.prepared_dataset or {}).get("request", {}).get("range_by")
            or range_by
        )

    return build_market_structure_stability_report(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=number_of_bars,
        config=MarketStructureConfig(
            apply_quality_adjustments=False,
            eds_boot_n=MarketStructureConfig().research_eds_boot_n,
            eds_perm_n=MarketStructureConfig().research_eds_perm_n,
        ),
    )


@router.post("/market-structure/robustness", response_model=Dict[str, Any])
async def get_market_structure_robustness(
    request: EdgeMarketStructureRequest,
    authorization: str = AUTH_HEADER,
):
    """Evaluate verdict robustness across nearby parameter variants."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    prepared = _resolve_prepared_dataset_from_payload(request.prepared_dataset)
    range_by = request.range_by.lower()
    number_of_bars = request.number_of_bars
    symbol = request.symbol or ""
    timeframe = request.timeframe
    data_source = request.data_source.lower()

    if prepared is None:
        range_by, start_date, end_date, number_of_bars = _validate_range_params(
            request.range_by,
            request.start_date,
            request.end_date,
            request.number_of_bars,
        )
        source = _create_data_source(
            request.data_source.lower(),
            user_id,
            start_date,
            end_date,
            number_of_bars,
            (request.start_date, request.end_date),
        )
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=number_of_bars or 5000,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol),
        )
    else:
        meta = prepared.report.metadata
        symbol = str(meta.get("symbol") or symbol)
        timeframe = str(meta.get("timeframe") or timeframe)
        data_source = str(
            (request.prepared_dataset or {}).get("request", {}).get("data_source")
            or data_source
        )
        range_by = str(
            (request.prepared_dataset or {}).get("request", {}).get("range_by")
            or range_by
        )

    return build_market_structure_robustness_report(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source=data_source,
        range_by=range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=number_of_bars,
        config=MarketStructureConfig(
            apply_quality_adjustments=False,
            eds_boot_n=MarketStructureConfig().research_eds_boot_n,
            eds_perm_n=MarketStructureConfig().research_eds_perm_n,
        ),
    )


@router.post("/automation/run", response_model=Dict[str, Any])
async def run_edge_lab_automation(
    request: EdgeLabAutomationRequest,
    authorization: str = AUTH_HEADER,
):
    """Run the progressive Edge Lab chain for one symbol with cache/dependency metadata."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    return _run_edge_lab_symbol_profile_sync(
        symbol=request.symbol,
        timeframe=request.timeframe,
        data_source=request.data_source,
        range_by=request.range_by,
        start_date=request.start_date,
        end_date=request.end_date,
        number_of_bars=request.number_of_bars,
        metric_families=request.metric_families,
        save_snapshot=request.save_snapshot,
        use_cache=request.use_cache,
        force_rerun=request.force_rerun,
        trigger_type=request.trigger_type,
        run_reason=request.run_reason,
        user_id=user_id,
    )


@router.post("/automation/batch", response_model=Dict[str, Any])
async def run_edge_lab_automation_batch(
    request: EdgeLabAutomationBatchRequest,
    authorization: str = AUTH_HEADER,
):
    """Run the progressive Edge Lab chain across a batch of symbols."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    results = []
    for symbol in request.symbols:
        results.append(
            _run_edge_lab_symbol_profile_sync(
                symbol=symbol,
                timeframe=request.timeframe,
                data_source=request.data_source,
                range_by=request.range_by,
                start_date=request.start_date,
                end_date=request.end_date,
                number_of_bars=request.number_of_bars,
                metric_families=request.metric_families,
                save_snapshot=request.save_snapshot,
                use_cache=request.use_cache,
                force_rerun=request.force_rerun,
                trigger_type=request.trigger_type,
                run_reason=request.run_reason,
                user_id=user_id,
            )
        )
    return {
        "symbol_count": len(request.symbols),
        "results": results,
    }


@router.post("/automation/refresh", response_model=Dict[str, Any])
async def refresh_edge_lab_automation_schedule(
    request: EdgeLabAutomationScheduleRequest,
    authorization: str = AUTH_HEADER,
):
    """Run one scheduled-style refresh workflow for a symbol batch."""
    batch_request = EdgeLabAutomationBatchRequest(**request.model_dump())
    return await run_edge_lab_automation_batch(batch_request, authorization=authorization)


@router.post("/scorecard/snapshots", response_model=Dict[str, Any])
async def save_scorecard_snapshot(
    request: EdgeProfileSnapshotRequest,
    authorization: str = AUTH_HEADER,
):
    """Persist one versioned Edge Lab profile snapshot from the progressive tab chain."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    snapshot_id = db_manager.save_profile_snapshot(request.model_dump(), user_id=user_id)
    if snapshot_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save profile snapshot.",
        )
    snapshot = db_manager.get_profile_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot saved but could not be reloaded.",
        )
    return snapshot


@router.get("/scorecard/snapshots", response_model=List[Dict[str, Any]])
async def list_scorecard_snapshots(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List stored Edge Lab profile snapshots."""
    return db_manager.get_profile_snapshots(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )


@router.get("/scorecard/snapshots/{snapshot_id}", response_model=Dict[str, Any])
async def get_scorecard_snapshot(snapshot_id: int):
    """Get one stored Edge Lab profile snapshot."""
    snapshot = db_manager.get_profile_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scorecard snapshot {snapshot_id} not found.",
        )
    return snapshot


@router.get("/scorecard/snapshots/compare", response_model=Dict[str, Any])
async def compare_scorecard_snapshots(
    left_snapshot_id: int,
    right_snapshot_id: int,
):
    """Compare two stored Edge Lab profile snapshots."""
    comparison = db_manager.compare_profile_snapshots(
        left_snapshot_id=left_snapshot_id,
        right_snapshot_id=right_snapshot_id,
    )
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both scorecard snapshots were not found.",
        )
    return comparison


@router.post("/scorecard/snapshots/{snapshot_id}/export-parquet", response_model=Dict[str, Any])
async def export_scorecard_snapshot_parquet(snapshot_id: int):
    """Export one profile snapshot's wide metrics to a Parquet artifact."""
    artifact = db_manager.export_profile_snapshot_metrics_parquet(snapshot_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scorecard snapshot {snapshot_id} not found or has no metrics.",
        )
    return artifact


@router.get("/scorecard/snapshots/{snapshot_id}/report", response_model=Dict[str, Any])
async def get_scorecard_snapshot_report(snapshot_id: int):
    """Build a machine-readable complete pair report from one stored snapshot."""
    snapshot = db_manager.get_profile_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scorecard snapshot {snapshot_id} not found.",
        )
    from backend.services.research.profile_reporting import snapshot_report_json

    return snapshot_report_json(snapshot)


@router.post("/scorecard/snapshots/{snapshot_id}/export-report", response_model=Dict[str, Any])
async def export_scorecard_snapshot_report(snapshot_id: int):
    """Export Markdown and JSON reports for one stored snapshot."""
    result = db_manager.export_profile_snapshot_reports(snapshot_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scorecard snapshot {snapshot_id} not found.",
        )
    return result


@router.post("/scorecard/snapshots/compare/export-markdown", response_model=Dict[str, Any])
async def export_scorecard_snapshot_comparison_markdown(
    left_snapshot_id: int,
    right_snapshot_id: int,
):
    """Export a Markdown comparison report for two stored snapshots."""
    result = db_manager.export_profile_snapshot_comparison_markdown(
        left_snapshot_id=left_snapshot_id,
        right_snapshot_id=right_snapshot_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both scorecard snapshots were not found.",
        )
    return result

