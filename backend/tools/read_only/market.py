"""Read-only market and symbol metadata chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


class SymbolStatsTool:
    name = "symbol_stats"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        symbol = context.get("symbol")
        if not symbol:
            return {"symbol_found": False}
        records = [
            record
            for record in (self.db.get_market_data_list() or [])
            if str(record.get("symbol", "")).upper() == str(symbol).upper()
        ]
        total_records = sum(int(record.get("record_count") or 0) for record in records)
        return {
            "symbol_found": bool(records),
            "symbol": str(symbol).upper(),
            "dataset_count": len(records),
            "total_record_count": total_records,
            "timeframes": sorted({str(record.get("timeframe") or "") for record in records if record.get("timeframe")}),
            "sources": sorted({str(record.get("source") or "") for record in records if record.get("source")}),
        }
