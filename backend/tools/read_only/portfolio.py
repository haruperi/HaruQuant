"""Read-only portfolio and risk chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


class PortfolioSummaryTool:
    name = "portfolio_summary"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        sessions = self.db.get_user_live_sessions(user_id) or []
        open_positions = []
        for session in sessions:
            open_positions.extend(self.db.get_session_positions(int(session["session_id"])) or [])
        total_profit = float(sum(float(position.get("current_profit") or 0.0) for position in open_positions))
        symbols = sorted({str(position.get("symbol") or "") for position in open_positions if position.get("symbol")})
        return {
            "session_count": len(sessions),
            "open_position_count": len(open_positions),
            "aggregate_open_profit": total_profit,
            "symbols": symbols[:12],
        }


class OpenPositionsTool:
    name = "open_positions"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        session_id = context.get("session_id")
        positions: list[dict[str, Any]] = []
        if session_id is not None:
            positions = self.db.get_session_positions(int(session_id)) or []
        else:
            sessions = self.db.get_user_live_sessions(user_id) or []
            for session in sessions[:5]:
                positions.extend(self.db.get_session_positions(int(session["session_id"])) or [])
        trimmed = [
            {
                "symbol": position.get("symbol"),
                "direction": position.get("position_type"),
                "size": position.get("size"),
                "current_profit": position.get("current_profit"),
                "status": position.get("status"),
            }
            for position in positions[:8]
        ]
        return {
            "count": len(positions),
            "positions": trimmed,
        }


class RiskSnapshotTool:
    name = "risk_snapshot"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        sessions = self.db.get_user_live_sessions(user_id) or []
        open_positions = []
        for session in sessions:
            open_positions.extend(self.db.get_session_positions(int(session["session_id"])) or [])
        exposure_by_symbol: dict[str, float] = {}
        floating_pnl = 0.0
        for position in open_positions:
            symbol = str(position.get("symbol") or "UNKNOWN")
            size = float(position.get("size") or 0.0)
            exposure_by_symbol[symbol] = exposure_by_symbol.get(symbol, 0.0) + size
            floating_pnl += float(position.get("current_profit") or 0.0)
        top_exposures = sorted(
            (
                {"symbol": symbol, "size": size}
                for symbol, size in exposure_by_symbol.items()
            ),
            key=lambda item: item["size"],
            reverse=True,
        )
        return {
            "running_session_count": sum(1 for session in sessions if str(session.get("status", "")).lower() == "running"),
            "open_position_count": len(open_positions),
            "floating_pnl": floating_pnl,
            "top_symbol_exposures": top_exposures[:5],
        }
