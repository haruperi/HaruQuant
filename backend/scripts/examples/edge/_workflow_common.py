from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.edge import CleaningConfig, EnrichmentConfig, build_core_metric_profile, build_market_structure_profile, prepare_ohlcvs_dataset
from apps.edge.scorecard import build_edge_lab_scorecard_report
from apps.edge.seasonality import SeasonalityFilters, run_seasonality
from apps.mt5 import MT5Utils
from apps.sqlite import SQLiteDatabase


DEFAULT_OUTPUT_DIR = ROOT_DIR / "edge_lab_outputs" / "examples"


def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _obj_to_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    if hasattr(value, "dict"):
        return _json_safe(value.dict())
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return {"value": _json_safe(value)}


class MT5BarsSource:
    def __init__(self) -> None:
        self.client = MT5Utils.get_connected_client()

    def fetch_data(self, symbol: str, timeframe: str, start_pos: int, end_pos: int):
        count = max(1, end_pos - start_pos)
        df = self.client.get_bars(symbol=symbol, timeframe=timeframe, count=count, start_pos=start_pos)
        if df is None or df.empty:
            raise RuntimeError(f"No MT5 bars returned for {symbol} {timeframe}")
        return df

    def shutdown(self) -> None:
        self.client.shutdown()


def prepare_mt5_dataset(symbol: str, timeframe: str, bars: int):
    source = MT5BarsSource()
    try:
        prepared = prepare_ohlcvs_dataset(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_pos=0,
            end_pos=bars,
            cleaning=CleaningConfig(timeframe=timeframe),
            enrichment=EnrichmentConfig(symbol=symbol, session_basis="dataset_index"),
        )
        return prepared
    finally:
        source.shutdown()


def extract_point_and_pip(prepared, symbol: str) -> Tuple[float, float]:
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


def serialize_prepared_dataset(prepared) -> Dict[str, Any]:
    frame = prepared.data.copy()
    frame = frame.reset_index().rename(columns={frame.index.name or "index": "timestamp"})
    if "timestamp" not in frame.columns:
        frame = frame.rename(columns={"index": "timestamp"})
    rows = [{key: _json_safe(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]
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
        "report": {
            "warnings": [_obj_to_dict(item) for item in prepared.report.warnings],
            "fatal_errors": [_obj_to_dict(item) for item in prepared.report.fatal_errors],
            "cleaning_actions": [_obj_to_dict(item) for item in prepared.report.cleaning_actions],
            "metadata": _json_safe(prepared.report.metadata),
            "is_valid": prepared.report.is_valid,
        },
        "rows": rows,
        "preview_rows": rows[:200],
    }


def build_progressive_outputs(symbol: str, timeframe: str, bars: int) -> Dict[str, Any]:
    prepared = prepare_mt5_dataset(symbol, timeframe, bars)
    core_metric = build_core_metric_profile(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source="mt5",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=bars,
    ).to_dict()
    point_size, pip_size = extract_point_and_pip(prepared, symbol)
    seasonality = run_seasonality(
        prepared.data,
        symbol=symbol,
        timeframe=timeframe,
        point_size=point_size,
        pip_size=pip_size,
        filters=SeasonalityFilters(),
        data_offset=0,
        data_limit=20,
    )
    market_structure = build_market_structure_profile(
        prepared,
        symbol=symbol,
        timeframe=timeframe,
        data_source="mt5",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=bars,
    ).to_dict()
    dataset_payload = serialize_prepared_dataset(prepared)
    dataset_payload["request"] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "data_source": "mt5",
        "range_by": "bars",
        "start_date": None,
        "end_date": None,
        "number_of_bars": bars,
    }
    scorecard = build_edge_lab_scorecard_report(
        dataset=dataset_payload,
        core_metric_profile=core_metric,
        seasonality_result=seasonality,
        market_structure_profile=market_structure,
        stability=None,
        robustness=None,
    )
    return {
        "prepared": prepared,
        "dataset": dataset_payload,
        "core_metric": core_metric,
        "seasonality": seasonality,
        "market_structure": market_structure,
        "scorecard": scorecard,
    }


def get_db() -> SQLiteDatabase:
    db = SQLiteDatabase()
    db.initialize_database()
    return db


def save_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
    return path
