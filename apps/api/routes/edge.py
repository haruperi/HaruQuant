"""Edge Lab API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.auth_utils import get_user_id_from_token
from apps.edge.classifier import classify_symbol
from apps.edge.config import (
    BootstrapConfig,
    DataConfig,
    EdgeLabConfig,
    PermutationConfig,
)
from apps.edge.core_metrics import build_core_metric_profile
from apps.edge.data import (
    CanonicalOHLCVSSchema,
    CleaningConfig,
    CleaningAction,
    DataQualityReportModel,
    DatasetIssue,
    EnrichmentConfig,
    PreparedDataset,
)
from apps.edge.datasets import (
    DataSource,
    load_ohlc,
    normalize_columns,
    prepare_ohlcvs_dataset,
)
from apps.edge.eds_mean_reversion import run_eds_mean_reversion
from apps.edge.eds_null_models import run_eds_null_baseline
from apps.edge.eds_session import run_eds_session
from apps.edge.eds_trend_persistence import run_eds_trend_persistence
from apps.edge.results_schema import EdgeResult, EdgeStats
from apps.edge.seasonality import SeasonalityFilters, run_seasonality
from apps.utils.logger import logger
from apps.mt5.client import MT5Client
from apps.sqlite.database_operations import DatabaseManager
from apps.utils.data_getters import load_dukascopy

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
    prepared = prepare_ohlcvs_dataset(
        source=source,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_pos=0,
        end_pos=number_of_bars or 5000,
        cleaning=CleaningConfig(timeframe=request.timeframe),
        enrichment=EnrichmentConfig(symbol=request.symbol),
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
        resolved_pip_size = float(df.get("pip_size", pd.Series([request.point_size])).iloc[0])
        resolved_point_size = float(df.get("point_size", pd.Series([request.point_size])).iloc[0])

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

