"""Data API routes for market instruments and dataset preparation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from backend.api.auth_utils import get_user_id_from_token
from backend.common.datasets import (
    DataSource,
    load_ohlc,
    normalize_columns,
    prepare_ohlcvs_dataset,
)
from backend.services.research.data import (
    CanonicalOHLCVSSchema,
    CleaningConfig,
    DataQualityReportModel,
    DatasetIssue,
    CleaningAction,
    EnrichmentConfig,
    PreparedDataset,
)
from backend.common.logger import logger
from backend.mcp.mt5_mcp.client import MT5Client
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.market_data.data_getters import load_dukascopy

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)

# --- Models ---

class DatasetPrepareRequest(BaseModel):
    """Request model for preparing a reusable dataset."""
    symbol: str
    timeframe: str = "M15"
    data_source: str = "mt5"
    range_by: str = "dates"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    session_basis: str = "dataset_index"

# --- Data Sources ---

class MT5DataSource:
    """MT5 data source wrapper."""
    def __init__(
        self,
        user_id: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        count: Optional[int],
    ):
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
        self.start_date = start_date
        self.end_date = end_date
        self.count = count

    def fetch_data(
        self, symbol: str, timeframe: str, start_pos: int, end_pos: int
    ) -> Optional[pd.DataFrame]:
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

# --- Shared Logic ---

def json_safe_value(value: Any) -> Any:
    """Safely convert common data types to JSON-serializable values."""
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

def report_to_dict(report: DataQualityReportModel) -> Dict[str, Any]:
    """Serialize a DataQualityReportModel to a dictionary."""
    return {
        "checks_performed": list(report.checks_performed),
        "warnings": [
            {
                "code": item.code,
                "severity": item.severity,
                "message": item.message,
                "count": item.count,
                "details": {k: json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.warnings
        ],
        "fatal_errors": [
            {
                "code": item.code,
                "severity": item.severity,
                "message": item.message,
                "count": item.count,
                "details": {k: json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.fatal_errors
        ],
        "cleaning_actions": [
            {
                "action": item.action,
                "count": item.count,
                "details": {k: json_safe_value(v) for k, v in item.details.items()},
            }
            for item in report.cleaning_actions
        ],
        "metadata": {k: json_safe_value(v) for k, v in report.metadata.items()},
        "is_valid": report.is_valid,
    }

def serialize_prepared_dataset(prepared: PreparedDataset) -> Dict[str, Any]:
    """Serialize a PreparedDataset to a dictionary."""
    frame = prepared.data.copy()
    frame = frame.reset_index().rename(columns={frame.index.name or "index": "timestamp"})
    if "timestamp" not in frame.columns:
        frame = frame.rename(columns={"index": "timestamp"})
    rows: List[Dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        rows.append({key: json_safe_value(value) for key, value in row.items()})
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
        "report": report_to_dict(prepared.report),
        "rows": rows,
        "preview_rows": preview,
    }

def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

def hash_jsonable(payload: Dict[str, Any]) -> str:
    """Stable hash of a JSON-serializable dictionary."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def dataset_fingerprint(prepared: PreparedDataset) -> str:
    """Generate a content-based fingerprint for a prepared dataset."""
    row_hashes = pd.util.hash_pandas_object(prepared.data, index=True)
    digest = hashlib.sha256()
    digest.update(row_hashes.to_numpy().tobytes())
    digest.update("|".join(str(column) for column in prepared.data.columns).encode("utf-8"))
    return digest.hexdigest()

def deserialize_prepared_dataset(payload: Dict[str, Any]) -> PreparedDataset:
    """Reconstruct a PreparedDataset from its serialized dictionary form."""
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

def resolve_prepared_dataset_from_payload(
    payload: Optional[Dict[str, Any]],
) -> Optional[PreparedDataset]:
    """Helper to safely resolve a dataset from a request payload."""
    if not payload:
        return None
    return deserialize_prepared_dataset(payload)

def validate_range_params(
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

    start_date = parse_date(start_date_str) if range_by == "dates" else None
    end_date = parse_date(end_date_str) if range_by == "dates" else None
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

def create_data_source(
    data_source: str,
    user_id: int,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    number_of_bars: Optional[int],
    string_dates: Tuple[Optional[str], Optional[str]] = (None, None),
) -> DataSource:
    """Create a data source object based on source type."""
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

def default_session_hours() -> Dict[str, List[int]]:
    """Return default trading session hour buckets."""
    return {
        "sydney": list(range(0, 7)),
        "tokyo": list(range(2, 9)),
        "london": list(range(10, 17)),
        "ny": list(range(15, 22)),
    }

# --- Routes ---

@router.get("/symbols", response_model=List[Dict[str, Any]])
async def get_symbols(
    authorization: str = Header(None),
):
    """Get all available symbols from MT5 terminal."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    creds = db_manager.get_mt5_credentials(user_id)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MT5 credentials not found.",
        )

    client = MT5Client()
    try:
        ok = client.connect(
            path=str(creds.get("path") or ""),
            login=int(creds.get("login") or 0),
            password=str(creds.get("password") or ""),
            server=str(creds.get("server") or ""),
        )

        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to connect to MT5.",
            )

        symbols = client.symbols_get()
        if symbols is None:
            return []

        result = []
        for s in symbols:
            # Map path to category (e.g. "Forex\Major\EURUSD" -> "Forex")
            category = "Other"
            if hasattr(s, "path") and s.path:
                parts = s.path.split("\\")
                if len(parts) > 1:
                    category = parts[0]

            result.append(
                {
                    "symbol": s.name,
                    "name": getattr(s, "description", s.name) or s.name,
                    "category": category,
                }
            )
        return result
    except Exception as e:
        logger.error(f"Error fetching symbols from MT5: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching symbols: {str(e)}",
        )
    finally:
        client.shutdown()

@router.post("/dataset/prepare", response_model=Dict[str, Any])
async def prepare_dataset_endpoint(
    request: DatasetPrepareRequest,
    authorization: str = Header(None),
):
    """Prepare and serialize a reusable dataset."""
    try:
        user_id = get_user_id_from_token(authorization)
    except Exception:
        user_id = 1

    range_by, start_date, end_date, number_of_bars = validate_range_params(
        request.range_by,
        request.start_date,
        request.end_date,
        request.number_of_bars,
    )
    source = create_data_source(
        request.data_source.lower(),
        user_id,
        start_date,
        end_date,
        number_of_bars,
        (request.start_date, request.end_date),
    )
    session_hours = default_session_hours()
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
    payload = serialize_prepared_dataset(prepared)
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
