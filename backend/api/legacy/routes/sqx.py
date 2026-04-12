"""SQX import routes."""

import io
import json
from typing import Annotated, Any, Dict, List, Optional, cast

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from backend.common.logger import logger
from backend.db.sqlite.database_operations import DatabaseManager

router = APIRouter()


DEFAULT_SQX_MAPPING = {
    "strategy_name": "Strategy Name",
    "symbol": "Symbol",
    "timeframe": "TimeFrame",
    "net_profit": "Net profit",
    "profit_factor": "Profit factor",
    "trades": "# of trades",
    "drawdown": "Drawdown",
    "max_drawdown_pct": "Max DD %",
    "ret_dd_ratio": "Ret/DD Ratio",
    "annual_return_pct": "Annual % Return",
}

REQUIRED_SQX_COLUMNS = {
    "strategy_name",
    "symbol",
    "timeframe",
    "net_profit",
    "profit_factor",
    "trades",
    "ret_dd_ratio",
    "annual_return_pct",
    "max_drawdown_pct",
}


def _parse_mapping(mapping_json: Optional[str]) -> Dict[str, Any]:
    if not mapping_json:
        return DEFAULT_SQX_MAPPING
    try:
        return cast(Dict[str, Any], json.loads(mapping_json))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in mapping field.")


def _sniff_delimiter(text_sample: str) -> str:
    delimiter = ","
    if ";" in text_sample and text_sample.count(";") > text_sample.count(","):
        delimiter = ";"

    if "\t" in text_sample and text_sample.count("\t") > text_sample.count(delimiter):
        delimiter = "\t"
    return delimiter


def _parse_uploaded_csv(content: bytes) -> pd.DataFrame:
    try:
        text_sample = content[:4096].decode("utf-8", errors="ignore")
        delimiter = _sniff_delimiter(text_sample)
        return pd.read_csv(io.BytesIO(content), sep=delimiter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")


def _validate_columns(df: pd.DataFrame, mapping_dict: Dict[str, str]) -> List[str]:
    missing_required = []
    for canon_key in REQUIRED_SQX_COLUMNS:
        header = mapping_dict.get(canon_key)
        if header and header not in df.columns:
            missing_required.append(header)
    return missing_required


@router.post("/import", summary="Import SQX Strategy Export")
async def import_sqx_strategies(
    stage: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    mapping: Annotated[Optional[str], Form()] = None,
    import_name: Annotated[Optional[str], Form()] = None,
    purge_missing: Annotated[bool, Form()] = False,
):
    """
    Import SQX strategies from CSV.

    - **file**: CSV file exported from SQX Databank.
    - **mapping**: JSON string mapping canonical columns to CSV headers.
    - **stage**: The stage label (e.g., 'CORE', 'SPREAD_P99').
    - **import_name**: Optional label for this import.
    - **purge_missing**: If true, delete strategies for included symbols that are missing in the import.
    """
    try:
        # Parse inputs
        mapping_dict = _parse_mapping(mapping)
        content = await file.read()
        df = _parse_uploaded_csv(content)

        final_import_name = (
            import_name
            if import_name is not None
            else (file.filename or "unknown_import")
        )

        # Report missing columns for required fields
        missing_required = _validate_columns(df, mapping_dict)

        # Process import
        db = DatabaseManager()
        rows_merged = db.merge_sqx_export(
            df=df,
            mapping=mapping_dict,
            stage=stage,
            import_name=final_import_name,
            purge_missing=purge_missing,
        )

        return {
            "status": "success",
            "message": f"Successfully merged {rows_merged} strategies.",
            "rows_merged": rows_merged,
            "missing_columns": missing_required,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-scores", summary="Calculate Strategy Scores")
async def calculate_scores(
    symbol: Annotated[Optional[str], Form()] = None,
):
    """
    Run scorecard calculation for strategies.

    - **symbol**: Optional, run only for specific symbol.
    """
    try:
        db = DatabaseManager()

        # 1. Fetch strategies
        strategies = db.get_sqx_strategies(symbol=symbol)
        if not strategies:
            return {
                "status": "success",
                "message": "No strategies found to score.",
                "updated_count": 0,
            }

        # 2. Convert to DataFrame
        import pandas as pd

        df = pd.DataFrame(strategies)

        # 3. Run Scorecard
        from backend.services.research.scorecard import StrategyScorecard

        scorer = StrategyScorecard()
        scored_df = scorer.process(df)

        # 4. Update DB
        updated_count = db.update_strategy_scores(scored_df)

        return {
            "status": "success",
            "message": f"Successfully calculated scores for {updated_count} strategies.",
            "updated_count": updated_count,
        }

    except Exception as e:
        logger.error(f"Score calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _apply_strategy_sorting(
    df: pd.DataFrame, sort_by: Optional[str], sort_dir: str
) -> pd.DataFrame:
    allowed_sort = {
        "stage",
        "strategy_name",
        "symbol",
        "profit_factor",
        "ret_dd_ratio",
        "annual_return_pct",
        "trades",
        "net_profit",
        "drawdown",
        "max_drawdown_pct",
        "edge_score",
        "robust_score",
        "stability_score",
        "risk_score",
        "simple_score",
        "final_score",
    }

    if not sort_by or sort_by not in allowed_sort:
        if "final_score" in df.columns:
            return df.sort_values(by="final_score", ascending=False, kind="mergesort")
        return df

    # Check if sort column exists in DF
    if sort_by not in df.columns and sort_by not in {
        "profit_factor",
        "ret_dd_ratio",
        "annual_return_pct",
        "trades",
        "net_profit",
        "max_drawdown_pct",
    }:
        # If it's not a computed complex sort and not in columns, just return or sort by final_score
        return df

    ascending = sort_dir.lower() == "asc"

    if sort_by in df.columns:
        return df.sort_values(by=sort_by, ascending=ascending, kind="mergesort")

    # Complex sort logic for stage-specific metrics
    prefix_map = {"A1_OOS2": "a1", "A2_OOS3": "a2", "E1_WFM": "e1"}

    def stage_sort_value(row):
        prefix = prefix_map.get(row.get("stage"))
        if prefix:
            prefixed = f"{prefix}_{sort_by}"
            if prefixed in row and pd.notna(row[prefixed]):
                return row[prefixed]
        return row.get(sort_by)

    df["_stage_sort"] = df.apply(stage_sort_value, axis=1)
    df = df.sort_values(by="_stage_sort", ascending=ascending, kind="mergesort")
    return df.drop(columns=["_stage_sort"])


@router.get("/strategies", summary="List SQX Strategies")
async def list_strategies(
    symbol: Annotated[Optional[str], Query()] = None,
    stage: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort_by: Annotated[Optional[str], Query()] = None,
    sort_dir: Annotated[str, Query()] = "desc",
):
    """
    List SQX strategies with optional filters.

    - **symbol**: Optional symbol filter.
    - **stage**: Optional stage filter.
    - **limit**: Max rows returned.
    """
    try:
        db = DatabaseManager()
        rows = db.get_sqx_strategies(symbol=symbol)
        if not rows:
            return {"status": "success", "rows": []}

        df = pd.DataFrame(rows)
        if stage and "stage" in df.columns:
            df = df[df["stage"] == stage]

        df = _apply_strategy_sorting(df, sort_by, sort_dir)

        total = int(len(df))
        if limit and limit < total:
            df = df.iloc[offset : offset + limit]
        elif offset:
            df = df.iloc[offset:]

        return {
            "status": "success",
            "rows": df.to_dict(orient="records"),
            "total": total,
        }
    except Exception as e:
        logger.error(f"Listing SQX strategies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

