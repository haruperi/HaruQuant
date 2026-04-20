"""Read-only portfolio and risk chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


def _load_positions(db: DatabaseManager, *, user_id: int, session_id: Any = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sessions = db.get_user_live_sessions(user_id) or []
    positions: list[dict[str, Any]] = []
    if session_id is not None:
        positions = db.get_session_positions(int(session_id)) or []
        return sessions, positions
    for session in sessions:
        positions.extend(db.get_session_positions(int(session["session_id"])) or [])
    return sessions, positions


class PortfolioSummaryTool:
    name = "portfolio_summary"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        sessions, open_positions = _load_positions(self.db, user_id=user_id)
        total_profit = float(sum(float(position.get("current_profit") or 0.0) for position in open_positions))
        symbols = sorted({str(position.get("symbol") or "") for position in open_positions if position.get("symbol")})
        profitable_positions = sum(1 for position in open_positions if float(position.get("current_profit") or 0.0) > 0.0)
        losing_positions = sum(1 for position in open_positions if float(position.get("current_profit") or 0.0) < 0.0)
        headline_metrics = {
            "session_count": len(sessions),
            "open_position_count": len(open_positions),
            "aggregate_open_profit": total_profit,
            "profitable_positions": profitable_positions,
            "losing_positions": losing_positions,
        }
        return {
            **headline_metrics,
            "headline_metrics": headline_metrics,
            "symbols": symbols[:12],
        }


class OpenPositionsTool:
    name = "open_positions"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        _sessions, positions = _load_positions(self.db, user_id=user_id, session_id=context.get("session_id"))
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
        best_position = max(
            (float(position.get("current_profit") or 0.0) for position in positions),
            default=0.0,
        )
        worst_position = min(
            (float(position.get("current_profit") or 0.0) for position in positions),
            default=0.0,
        )
        return {
            "count": len(positions),
            "headline_metrics": {
                "count": len(positions),
                "best_position_profit": best_position,
                "worst_position_profit": worst_position,
            },
            "positions": trimmed,
        }


class RiskSnapshotTool:
    name = "risk_snapshot"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        sessions, open_positions = _load_positions(self.db, user_id=user_id)
        exposure_by_symbol: dict[str, float] = {}
        floating_pnl = 0.0
        total_abs_exposure = 0.0
        for position in open_positions:
            symbol = str(position.get("symbol") or "UNKNOWN")
            size = float(position.get("size") or 0.0)
            exposure_by_symbol[symbol] = exposure_by_symbol.get(symbol, 0.0) + size
            floating_pnl += float(position.get("current_profit") or 0.0)
            total_abs_exposure += abs(size)
        top_exposures = sorted(
            (
                {"symbol": symbol, "size": size}
                for symbol, size in exposure_by_symbol.items()
            ),
            key=lambda item: abs(item["size"]),
            reverse=True,
        )
        largest_exposure = abs(top_exposures[0]["size"]) if top_exposures else 0.0
        concentration_ratio = (largest_exposure / total_abs_exposure) if total_abs_exposure > 0 else 0.0
        headline_metrics = {
            "running_session_count": sum(1 for session in sessions if str(session.get("status", "")).lower() == "running"),
            "open_position_count": len(open_positions),
            "floating_pnl": floating_pnl,
            "largest_exposure": largest_exposure,
            "concentration_ratio": concentration_ratio,
        }
        return {
            **headline_metrics,
            "headline_metrics": headline_metrics,
            "top_symbol_exposures": top_exposures[:5],
        }
