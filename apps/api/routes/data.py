"""Data management routes."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.logger import logger
from apps.sqlite.database_operations import DatabaseManager
from apps.utils.data_getters import get_data_dir, load_dukascopy, load_mt5
from apps.utils.data_validator import DataValidator

router = APIRouter()


class IngestRequest(BaseModel):
    """Request model for ingesting market data."""

    symbol: str
    source: str = "mt5"
    # Although the UI removes inputs, we keep these optional in the model
    # but will enforce defaults in logic as requested
    start_date: Optional[str] = None
    timeframe: Optional[str] = None


def _default_ingest_config() -> tuple[str, str, str]:
    start_date = "2007-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    timeframe = "M1"
    return start_date, end_date, timeframe


def _parse_mt5_login(source: str) -> Optional[int]:
    if ":" not in source:
        return None

    parts = source.split(":")
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        logger.warning(f"Invalid MT5 source format: {source}, using default")
        return None


def _download_data(
    request: IngestRequest,
    start_date: str,
    end_date: str,
    timeframe: str,
    user_id: int,
):
    source = request.source.lower()
    if source.startswith("mt5"):
        mt5_login = _parse_mt5_login(request.source)
        return load_mt5(
            symbol=request.symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            mt5_login=mt5_login,
        )

    if source == "dukascopy":
        return load_dukascopy(
            symbol=request.symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

    raise ValueError(f"Unknown source: {request.source}")


def _validate_data(df) -> dict:
    validator = DataValidator()
    _, _, sanity_issues = validator.validate_price_sanity(df, mark_invalid=True)
    _, gap_info = validator.detect_gaps(df, expected_frequency="1min")

    return {
        "total_records": len(df),
        "sanity_issues_count": len(sanity_issues),
        "gaps_count": len(gap_info),
        "sanity_sample": str(sanity_issues[:5]) if sanity_issues else [],
        "gaps_sample": str(gap_info[:5]) if gap_info else [],
    }


def _save_parquet(df, symbol: str) -> tuple[Path, str]:
    data_dir = get_data_dir()
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{symbol}.parquet"
    file_name = file_name.replace("/", "").replace(":", "")
    file_path = raw_dir / file_name
    df.to_parquet(file_path)
    return file_path, file_name


def _save_metadata(metadata: dict) -> None:
    db = DatabaseManager()
    db.initialize_database()
    db.save_market_data_metadata(metadata)


async def _ingest_stream(request: IngestRequest, user_id: int):
    try:
        yield json.dumps(
            {
                "status": "starting",
                "message": f"Initializing ingestion for {request.symbol}...",
            }
        ) + "\n"

        start_date, end_date, timeframe = _default_ingest_config()
        yield json.dumps(
            {
                "status": "info",
                "message": (
                    "Configuration: "
                    f"Start={start_date}, End={end_date}, TF={timeframe}, UserID={user_id}"
                ),
            }
        ) + "\n"

        yield json.dumps(
            {
                "status": "downloading",
                "progress": 10,
                "message": f"Downloading data from {request.source}...",
            }
        ) + "\n"

        try:
            df = _download_data(request, start_date, end_date, timeframe, user_id)
        except Exception as exc:
            yield json.dumps(
                {"status": "error", "message": f"Download failed: {str(exc)}"}
            ) + "\n"
            return

        if df is None or df.empty:
            yield json.dumps(
                {"status": "error", "message": "No data returned from source."}
            ) + "\n"
            return

        yield json.dumps(
            {
                "status": "downloading",
                "progress": 40,
                "message": f"Downloaded {len(df):,} records.",
            }
        ) + "\n"

        yield json.dumps(
            {
                "status": "validating",
                "progress": 50,
                "message": "Validating data integrity...",
            }
        ) + "\n"

        validation_report = _validate_data(df)
        yield json.dumps(
            {
                "status": "validating",
                "progress": 60,
                "message": (
                    "Price sanity check complete. "
                    f"Issues: {validation_report['sanity_issues_count']}"
                ),
            }
        ) + "\n"
        yield json.dumps(
            {
                "status": "validating",
                "progress": 70,
                "message": (
                    "Gap detection complete. "
                    f"Gaps found: {validation_report['gaps_count']}"
                ),
            }
        ) + "\n"

        yield json.dumps(
            {
                "status": "saving",
                "progress": 80,
                "message": "Saving raw data to parquet...",
            }
        ) + "\n"

        file_path, file_name = _save_parquet(df, request.symbol)
        yield json.dumps(
            {"status": "saving", "progress": 90, "message": f"Saved to {file_name}"}
        ) + "\n"

        yield json.dumps(
            {
                "status": "saving",
                "progress": 95,
                "message": "Saving metadata to database...",
            }
        ) + "\n"

        metadata = {
            "symbol": request.symbol,
            "timeframe": timeframe,
            "source": request.source,
            "start_date": start_date,
            "end_date": end_date,
            "record_count": len(df),
            "validation_report": validation_report,
            "file_path": str(file_path),
        }

        _save_metadata(metadata)

        yield json.dumps(
            {
                "status": "complete",
                "progress": 100,
                "message": "Ingestion pipeline completed successfully.",
            }
        ) + "\n"

    except Exception as exc:
        logger.error(f"Ingestion error: {exc}")
        yield json.dumps(
            {"status": "error", "message": f"Internal error: {str(exc)}"}
        ) + "\n"


@router.post("/ingest")
async def ingest_data(request: IngestRequest, user_id: int = 1):
    """Ingest data and stream progress messages."""
    return StreamingResponse(
        _ingest_stream(request, user_id), media_type="application/x-ndjson"
    )


@router.get("/list")
async def list_datasets():
    """List all available datasets in metadata db."""
    try:
        db = DatabaseManager()
        db.initialize_database()
        datasets = db.get_market_data_list()
        return datasets
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(dataset_id: int):
    """Return a preview (first and last 10 rows) of a dataset."""
    try:
        file_path = _get_dataset_file_path(dataset_id)
        import pandas as pd

        df = pd.read_parquet(file_path)
        return _build_preview(df, pd)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_dataset_file_path(dataset_id: int) -> Path:
    db = DatabaseManager()
    db.initialize_database()
    datasets = db.get_market_data_list()
    dataset = next((d for d in datasets if d["id"] == dataset_id), None)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = Path(dataset["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Data file not found")

    return file_path


def _format_preview_row(row, pd_module):
    item = row.to_dict()
    for key, value in item.items():
        if isinstance(value, (datetime, pd_module.Timestamp)):
            item[key] = value.strftime("%Y-%m-%d %H:%M:%S")

    display_item = {}
    for key, value in item.items():
        lower_key = key.lower()
        if lower_key in ["index", "time", "date", "datetime"]:
            display_item["Datetime"] = value
        elif lower_key in ["open", "high", "low", "close"]:
            display_item[key.capitalize()] = value
        elif lower_key in ["tick_volume", "volume", "real_volume"]:
            display_item["Volume"] = value
        elif lower_key == "spread":
            display_item["Spread"] = value
    return display_item


def _process_preview_chunk(chunk, pd_module):
    if isinstance(chunk.index, pd_module.DatetimeIndex):
        chunk = chunk.reset_index()
    return [_format_preview_row(row, pd_module) for _, row in chunk.iterrows()]


def _build_preview(df, pd_module):
    if len(df) <= 20:
        return _process_preview_chunk(df, pd_module)

    head_rows = _process_preview_chunk(df.head(10), pd_module)
    tail_rows = _process_preview_chunk(df.tail(10), pd_module)
    keys = head_rows[0].keys() if head_rows else []
    separator = dict.fromkeys(keys, "...")
    return head_rows + [separator, separator] + tail_rows
