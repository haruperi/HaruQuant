"""Read-only market and symbol metadata chat tools."""

from __future__ import annotations

from datetime import timezone
from typing import Any

import pandas as pd

from backend.api.routes.dashboard.broker import client as global_mt5_client
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.mcp.mt5_mcp import get_mt5_api

mt5 = get_mt5_api()


def _fetch_ohlc_data(symbol: str, timeframe: str, count: int = 500) -> pd.DataFrame | None:
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe, mt5.TIMEFRAME_M1), 0, count)
    if rates is None:
        return None
    data = pd.DataFrame(rates)
    if data.empty:
        return None
    data["time"] = pd.to_datetime(data["time"], unit="s")
    return data


def _ensure_mt5_connection(db: DatabaseManager, user_id: int):
    creds = db.get_mt5_credentials(user_id) or {}
    login = creds.get("login")
    password = creds.get("password")
    server = creds.get("server")
    path = creds.get("path", "")
    if not login or not password or not server:
        return global_mt5_client
    global_mt5_client.account_login = int(login)  # type: ignore[attr-defined]
    global_mt5_client.account_password = password  # type: ignore[attr-defined]
    global_mt5_client.account_server = server  # type: ignore[attr-defined]
    if not global_mt5_client.is_connected():
        global_mt5_client.connect(
            path=path,
            login=int(login),
            password=password,
            server=server,
        )
    return global_mt5_client


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


class LatestCandleTool:
    name = "latest_candle"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        session_id = context.get("session_id")
        symbol = str(context.get("symbol") or "").upper()
        timeframe = str(context.get("timeframe") or "").upper()
        if not isinstance(session_id, int):
            return {
                "candle_available": False,
                "reason": "no live session is selected",
                "symbol": symbol or None,
                "timeframe": timeframe or None,
            }
        if not symbol or not timeframe:
            return {
                "candle_available": False,
                "reason": "symbol or timeframe is missing from the current live chart context",
                "symbol": symbol or None,
                "timeframe": timeframe or None,
                "session_id": session_id,
            }

        session = self.db.get_live_session(session_id)
        if not session or int(session.get("user_id") or 0) != int(user_id):
            return {
                "candle_available": False,
                "reason": "the selected live session is unavailable",
                "symbol": symbol,
                "timeframe": timeframe,
                "session_id": session_id,
            }

        mt5_client = _ensure_mt5_connection(self.db, user_id)

        if not mt5_client or not mt5_client.is_connected():
            return {
                "candle_available": False,
                "reason": "MT5 connection is not available",
                "symbol": symbol,
                "timeframe": timeframe,
                "session_id": session_id,
            }

        data = _fetch_ohlc_data(symbol=symbol, timeframe=timeframe, count=3)
        if data is None or data.empty:
            return {
                "candle_available": False,
                "reason": f"no market data was returned for {symbol} {timeframe}",
                "symbol": symbol,
                "timeframe": timeframe,
                "session_id": session_id,
            }

        data = data.sort_values("time")
        row = data.iloc[-1]
        candle_time = row["time"]
        if hasattr(candle_time, "to_pydatetime"):
            candle_time = candle_time.to_pydatetime()
        if getattr(candle_time, "tzinfo", None) is None:
            candle_time = candle_time.replace(tzinfo=timezone.utc)
        else:
            candle_time = candle_time.astimezone(timezone.utc)

        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])
        direction = "bullish" if close_price > open_price else "bearish" if close_price < open_price else "neutral"
        body_size = round(abs(close_price - open_price), 8)
        range_size = round(high_price - low_price, 8)

        return {
            "candle_available": True,
            "session_id": session_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "last_candle_direction": direction,
            "last_candle_time": candle_time.isoformat(),
            "headline_metrics": {
                "symbol": symbol,
                "timeframe": timeframe,
                "last_candle_direction": direction,
            },
            "last_candle": {
                "time": candle_time.isoformat(),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            },
            "body_size": body_size,
            "range_size": range_size,
        }
