"""Backtest management module."""

import contextlib
import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from haruquant.utils import logger


def _json_ready(value: Any) -> Any:
    """Convert nested backtest payload values into JSON-safe Python types."""
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if pd.isna(value) or not pd.notna(value):
            return None
        if value in (float("inf"), float("-inf")):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return json.loads(value.to_json(orient="records", date_format="iso"))
    if isinstance(value, pd.Series):
        return _json_ready(value.tolist())
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "to_dict"):
        with contextlib.suppress(Exception):
            return _json_ready(value.to_dict())
    return value


def _json_text(value: Any) -> str:
    return json.dumps(_json_ready(value), ensure_ascii=False, default=str)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    with contextlib.suppress(Exception):
        return json.loads(value)
    return default


class BacktestManager:
    """Backtest management operations."""

    db_path: str

    def create_backtest_run(
        self,
        strategy_name: str,
        strategy_version: str,
        start_date: datetime,
        end_date: datetime,
        engine_type: str,
        data_resolution: str,
        config_hash: str,
        strategy_version_id: Optional[int] = None,
        user_id: Optional[int] = None,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        initial_balance: float = 10000.0,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        commission_model: Optional[str] = None,
        slippage_model: Optional[str] = None,
        spread_model: Optional[str] = None,
        execution_model: Optional[str] = None,
        fill_model: Optional[str] = None,
        risk_model: Optional[str] = None,
        position_sizing_model: Optional[str] = None,
    ) -> int:
        """Create a canonical JSON-backed backtest row."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metadata = {
                "status": "pending",
                "strategy_name": strategy_name,
                "strategy_version": strategy_version,
                "strategy_version_id": strategy_version_id,
                "user_id": user_id,
                "alias": alias,
                "description": description,
                "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
                "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
                "symbols": symbols or [],
                "timeframes": timeframes or [],
                "initial_balance": float(initial_balance),
                "commission_model": commission_model,
                "slippage_model": slippage_model,
                "spread_model": spread_model,
                "execution_model": execution_model,
                "fill_model": fill_model,
                "risk_model": risk_model,
                "position_sizing_model": position_sizing_model,
                "engine_type": engine_type,
                "data_resolution": data_resolution,
                "config_hash": config_hash,
                "snapshot_version": 1,
            }

            cursor.execute(
                """
                INSERT INTO backtests (metadata, result, analytics)
                VALUES (?, ?, ?)
                """,
                (_json_text(metadata), "{}", "{}"),
            )

            backtest_id = int(cursor.lastrowid or 0)
            if backtest_id <= 0:
                raise ValueError("Failed to retrieve backtest ID after insertion.")

            metadata["backtest_id"] = backtest_id
            metadata["created_at"] = datetime.utcnow().isoformat()
            cursor.execute(
                "UPDATE backtests SET metadata = ? WHERE id = ?",
                (_json_text(metadata), backtest_id),
            )

            conn.commit()
            logger.info(f"Backtest snapshot {backtest_id} created successfully.")
            return backtest_id

        except Exception as e:
            logger.error(f"Error creating backtest run: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_backtest_snapshot(
        self,
        backtest_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        analytics: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        final_balance: Optional[float] = None,
    ) -> bool:
        """Persist the full JSON snapshot for a backtest."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            row = cursor.execute(
                "SELECT metadata, result, analytics FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()

            current_metadata = _json_loads(row[0], {}) if row else {}
            current_result = _json_loads(row[1], {}) if row else {}
            current_analytics = _json_loads(row[2], {}) if row else {}

            merged_metadata = dict(current_metadata)
            if metadata:
                merged_metadata.update(_json_ready(metadata))
            if status is not None:
                merged_metadata["status"] = status
                if status == "completed":
                    merged_metadata["completed_at"] = datetime.utcnow().isoformat()
            if final_balance is not None:
                merged_metadata["final_balance"] = float(final_balance)
            merged_metadata["backtest_id"] = backtest_id
            merged_metadata.setdefault("snapshot_version", 1)
            merged_metadata["updated_at"] = datetime.utcnow().isoformat()

            merged_result = dict(current_result)
            if result:
                merged_result.update(_json_ready(result))

            merged_analytics = dict(current_analytics)
            if analytics:
                merged_analytics.update(_json_ready(analytics))

            if row:
                cursor.execute(
                    """
                    UPDATE backtests
                    SET metadata = ?, result = ?, analytics = ?
                    WHERE id = ?
                    """,
                    (
                        _json_text(merged_metadata),
                        _json_text(merged_result),
                        _json_text(merged_analytics),
                        backtest_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO backtests (id, metadata, result, analytics)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        backtest_id,
                        _json_text(merged_metadata),
                        _json_text(merged_result),
                        _json_text(merged_analytics),
                    ),
                )

            conn.commit()
            return True
        except Exception as exc:
            logger.error(f"Error saving backtest snapshot: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_backtest_snapshot(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """Return the canonical JSON snapshot for a backtest."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT id, metadata, result, analytics FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()
            if row:
                metadata = _json_loads(row["metadata"], {}) or {}
                result = _json_loads(row["result"], {}) or {}
                analytics = _json_loads(row["analytics"], {}) or {}
                return {
                    "backtest_id": int(row["id"]),
                    "metadata": metadata,
                    "result": result,
                    "analytics": analytics,
                }
        except Exception as exc:
            logger.error(f"Error getting backtest snapshot: {exc}")
            raise
        finally:
            if conn:
                conn.close()

    def get_backtest_overview_snapshot(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """Return the precomputed overview payload for a backtest, if available."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT analytics FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()
            if not row:
                return None
            analytics = _json_loads(row["analytics"], {}) or {}
            overview = analytics.get("overview")
            if overview:
                return overview
            summary = analytics.get("summary")
            if summary:
                return {
                    "summary": summary,
                    "metrics": summary,
                    "equity_curves": analytics.get("equity_curves", {"all": [], "long": [], "short": []}),
                    "charts": analytics.get("charts", {"equity_curve": [], "drawdown_curve": []}),
                }
            return None
        except Exception as exc:
            logger.error(f"Error getting backtest overview snapshot: {exc}")
            raise
        finally:
            if conn:
                conn.close()

    def save_backtest_result(
        self,
        backtest_result,
        backtest_id: Optional[int] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> int:
        """Save a legacy BacktestResult as a canonical backtest snapshot."""
        from haruquant.analytics import build_overview_payload, get_analytics_overview

        if backtest_id is None:
            start_date = getattr(backtest_result, "start_date", datetime.utcnow())
            end_date = getattr(backtest_result, "end_date", datetime.utcnow())
            backtest_id = self.create_backtest_run(
                strategy_name=getattr(backtest_result, "strategy_name", "unknown"),
                strategy_version=str(getattr(backtest_result, "strategy_version", "1.0.0")),
                start_date=pd.Timestamp(start_date).to_pydatetime(),
                end_date=pd.Timestamp(end_date).to_pydatetime(),
                engine_type=str(getattr(backtest_result, "backtest_mode", "vectorized")),
                data_resolution=str(getattr(backtest_result, "data_step_mode", "unknown")),
                config_hash=str(hash((getattr(backtest_result, "strategy_name", ""), getattr(backtest_result, "symbol", "")))),
                symbols=[str(getattr(backtest_result, "symbol", "UNKNOWN"))],
                timeframes=[str(getattr(backtest_result, "timeframe", "H1"))],
                initial_balance=float(getattr(backtest_result, "initial_balance", 0.0) or 0.0),
                alias=alias or getattr(getattr(backtest_result, "metadata", {}), "get", lambda *_: None)("alias"),
                description=description or getattr(getattr(backtest_result, "metadata", {}), "get", lambda *_: None)("description"),
                user_id=user_id,
            )

        result_payload = {
            "trades": _json_ready(getattr(backtest_result, "trades", []) or []),
            "equity_curve": _json_ready(getattr(backtest_result, "equity_curve", []) or []),
        }
        metadata_payload = {
            "alias": alias,
            "description": description,
            "status": "completed",
            "strategy_name": getattr(backtest_result, "strategy_name", None),
            "symbol": getattr(backtest_result, "symbol", None),
            "timeframe": getattr(backtest_result, "timeframe", None),
            "start_date": getattr(backtest_result, "start_date", None),
            "end_date": getattr(backtest_result, "end_date", None),
            "initial_balance": getattr(backtest_result, "initial_balance", None),
            "final_balance": getattr(backtest_result, "final_balance", None),
            "final_equity": getattr(backtest_result, "final_equity", None),
        }
        trades_payload = _json_ready(getattr(backtest_result, "trades", []) or [])
        equity_payload = _json_ready(getattr(backtest_result, "equity_curve", []) or [])
        analytics_payload = get_analytics_overview(
            trades=trades_payload,
            initial_balance=float(getattr(backtest_result, "initial_balance", 0.0) or 0.0),
            start_time=getattr(backtest_result, "start_date", None),
            end_time=getattr(backtest_result, "end_date", None),
        )
        analytics_payload["overview"] = build_overview_payload(
            trades_payload,
            initial_balance=float(getattr(backtest_result, "initial_balance", 0.0) or 0.0),
            start_time=getattr(backtest_result, "start_date", None),
            end_time=getattr(backtest_result, "end_date", None),
            equity_curve_records=equity_payload,
            summary_overrides=analytics_payload.get("summary", {}),
        )
        self.save_backtest_snapshot(
            backtest_id=backtest_id,
            metadata=metadata_payload,
            result=result_payload,
            analytics=analytics_payload,
            status="completed",
            final_balance=float(getattr(backtest_result, "final_balance", 0.0) or 0.0),
        )
        logger.info(f"BacktestResult saved successfully to canonical snapshot table (ID: {backtest_id})")
        return int(backtest_id)

    def _ensure_backtest_result_type(self, backtest_result: Any) -> None:
        """Ensure the object is a BacktestResult instance."""
        try:
            from apps.backtest.result import BacktestResult

            if not isinstance(backtest_result, BacktestResult):
                raise ValueError("backtest_result must be a BacktestResult instance")
        except ImportError:
            logger.warning("Could not import BacktestResult for type checking.")

    def _create_backtest_from_result(
        self,
        backtest_result: Any,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> int:
        """Create a new backtest run from a result object."""
        start_date = backtest_result.start_date
        if hasattr(start_date, "to_pydatetime"):
            start_date = start_date.to_pydatetime()

        end_date = backtest_result.end_date
        if hasattr(end_date, "to_pydatetime"):
            end_date = end_date.to_pydatetime()

        return self.create_backtest_run(
            strategy_name=backtest_result.strategy_name,
            strategy_version="1.0.0",
            start_date=start_date,
            end_date=end_date,
            engine_type=backtest_result.backtest_mode,
            data_resolution=backtest_result.data_step_mode,
            config_hash=str(
                hash((backtest_result.strategy_name, backtest_result.symbol))
            ),
            symbols=[backtest_result.symbol],
            timeframes=[backtest_result.timeframe],
            initial_balance=backtest_result.initial_balance,
            alias=alias or backtest_result.metadata.get("alias"),
            description=description or backtest_result.metadata.get("description"),
            user_id=user_id,
        )

    def _save_trades(
        self, cursor: sqlite3.Cursor, backtest_id: int, trades: List[Any]
    ) -> None:
        """Prepare and save trade data."""
        trade_data = []
        for trade in trades:
            open_time = trade.open_time
            if hasattr(open_time, "to_pydatetime"):
                open_time = open_time.to_pydatetime()

            close_time = trade.close_time
            if hasattr(close_time, "to_pydatetime"):
                close_time = close_time.to_pydatetime()

            orig_open_time = getattr(trade, "orig_open_time", None)
            if orig_open_time and hasattr(orig_open_time, "to_pydatetime"):
                orig_open_time = orig_open_time.to_pydatetime()

            trade_data.append(
                (
                    backtest_id,
                    trade.ticket,
                    trade.symbol,
                    trade.type,
                    getattr(trade, "magic_number", 0),
                    trade.strategy_name,
                    getattr(trade, "setup_id", None),
                    getattr(trade, "sample_type", None),
                    getattr(trade, "comment", None),
                    getattr(trade, "signal_timeframe", None),
                    getattr(trade, "execution_timeframe", None),
                    getattr(trade, "session", None),
                    getattr(trade, "day_of_week", None),
                    getattr(trade, "hour_of_day", None),
                    open_time,
                    close_time,
                    trade.time_in_trade,
                    trade.bars_in_trade,
                    trade.open_price,
                    getattr(trade, "orig_open_price", None),
                    orig_open_time,
                    getattr(trade, "requested_entry_price", None),
                    getattr(trade, "spread_at_entry", None),
                    getattr(trade, "atr_at_entry", None),
                    trade.size,
                    trade.close_price,
                    getattr(trade, "requested_exit_price", None),
                    getattr(trade, "close_type", None),
                    getattr(trade, "exit_reason", None),
                    getattr(trade, "stop_loss_price", None),
                    getattr(trade, "profit_target_price", None),
                    trade.initial_risk_pips,
                    trade.initial_risk_usd,
                    getattr(trade, "balance_at_entry", None),
                    getattr(trade, "equity_at_entry", None),
                    getattr(trade, "margin_used", None),
                    getattr(trade, "free_margin", None),
                    getattr(trade, "max_position_size", None),
                    getattr(trade, "partial_close_count", 0),
                    getattr(trade, "trailing_stop_used", False),
                    getattr(trade, "breakeven_triggered", False),
                    getattr(trade, "slippage_usd", None),
                    getattr(trade, "fill_price_deviation", None),
                    getattr(trade, "execution_latency_ms", None),
                    trade.profit_loss,
                    trade.profit_loss_pips,
                    getattr(trade, "commission", 0.0),
                    getattr(trade, "swap", 0.0),
                    trade.r_multiple,
                    getattr(trade, "buy_hold", 0.0),
                    getattr(trade, "buy_hold_pips", 0.0),
                    trade.mae_usd,
                    trade.mae_pips,
                    trade.mfe_usd,
                    trade.mfe_pips,
                    getattr(trade, "drawdown", None),
                    getattr(trade, "market_regime", None),
                    getattr(trade, "volatility_bucket", None),
                    getattr(trade, "correlation_cluster", None),
                    getattr(trade, "rule_violation", False),
                    getattr(trade, "manual_intervention", False),
                )
            )

        if trade_data:
            cursor.executemany(
                """
                INSERT INTO backtest_trades (
                    backtest_id, ticket, symbol, side, magic_number, strategy_name,
                    setup_id, sample_type, comment,
                    signal_timeframe, execution_timeframe, session, day_of_week, hour_of_day,
                    open_time, close_time, time_in_trade_seconds, bars_in_trade,
                    open_price, orig_open_price, orig_open_time, requested_entry_price,
                    spread_at_entry, atr_at_entry, position_size,
                    close_price, requested_exit_price, close_type, exit_reason,
                    stop_loss_price, profit_target_price, initial_risk_pips, initial_risk_usd,
                    balance_at_entry, equity_at_entry, margin_used, free_margin,
                    max_position_size, partial_close_count, trailing_stop_used, breakeven_triggered,
                    slippage_usd, fill_price_deviation, execution_latency_ms,
                    pnl, pnl_pips, commission, swap, r_multiple, buy_hold, buy_hold_pips,
                    mae_usd, mae_pips, mfe_usd, mfe_pips, drawdown,
                    market_regime, volatility_bucket, correlation_cluster,
                    rule_violation, manual_intervention
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                trade_data,
            )

    def _save_equity_curve(
        self, cursor: sqlite3.Cursor, backtest_id: int, equity_curve: List[Any]
    ) -> None:
        """Prepare and save equity curve data."""
        equity_data = []
        for point in equity_curve:
            timestamp = point.timestamp
            if hasattr(timestamp, "to_pydatetime"):
                timestamp = timestamp.to_pydatetime()

            equity_data.append(
                (
                    backtest_id,
                    timestamp,
                    point.equity,
                    point.balance,
                    point.drawdown,
                    getattr(point, "exposure", 0),
                )
            )

        if equity_data:
            cursor.executemany(
                """
                INSERT INTO backtest_equity_curve (backtest_id, timestamp, equity, balance, drawdown, exposure)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                equity_data,
            )

    def _save_finance_metrics(
        self, cursor: sqlite3.Cursor, backtest_id: int, backtest_result: Any
    ) -> None:
        """Compatibility hook that now stores analytics in the JSON snapshot."""
        from haruquant.analytics import get_analytics_overview

        snapshot = self.get_backtest_snapshot(backtest_id) or {"metadata": {}, "result": {}, "analytics": {}}
        metadata = snapshot.get("metadata") or {}
        result_payload = snapshot.get("result") or {}
        trades = _json_ready(getattr(backtest_result, "trades", None) or result_payload.get("trades", []) or [])

        account = metadata.get("account", {}) if isinstance(metadata, dict) else {}
        data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
        initial_balance = float(
            getattr(
                backtest_result,
                "initial_balance",
                account.get("initial_balance", metadata.get("initial_balance", 0.0)),
            )
            or 0.0
        )

        analytics = get_analytics_overview(
            trades=trades,
            initial_balance=initial_balance,
            start_time=getattr(backtest_result, "start_date", data.get("start") or metadata.get("start_date")),
            end_time=getattr(backtest_result, "end_date", data.get("end") or metadata.get("end_date")),
        )

        self.save_backtest_snapshot(backtest_id=backtest_id, analytics=analytics)

    def get_backtest_run(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a backtest snapshot in run-shaped form."""
        snapshot = self.get_backtest_snapshot(backtest_id)
        if not snapshot:
            return None

        metadata = snapshot.get("metadata", {}) or {}
        analytics = snapshot.get("analytics", {}) or {}
        summary_all = (analytics.get("summary", {}) or {}).get("all", {})
        result_payload = snapshot.get("result", {}) or {}
        account = metadata.get("account", {}) if isinstance(metadata, dict) else {}
        data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
        reporting = metadata.get("reporting", {}) if isinstance(metadata, dict) else {}
        strategy = metadata.get("strategy", {}) if isinstance(metadata, dict) else {}
        trades = result_payload.get("trades", []) or []

        symbol = data.get("symbol") or metadata.get("symbol")
        if not symbol:
            symbols = data.get("symbols", []) or metadata.get("symbols", [])
            symbol = ",".join(symbols) if symbols else None
            
        timeframe = data.get("timeframe") or metadata.get("timeframe")
        if not timeframe:
            timeframes = data.get("timeframes", []) or metadata.get("timeframes", [])
            timeframe = timeframes[0] if timeframes else None

        return {
            "backtest_id": snapshot["backtest_id"],
            "strategy_id": metadata.get("strategy_id"),
            "strategy_version_id": metadata.get("strategy_version_id"),
            "status": metadata.get("status", "completed"),
            "strategy_name": metadata.get("strategy_name") or strategy.get("name"),
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": data.get("start") or metadata.get("start_date"),
            "end_date": data.get("end") or metadata.get("end_date"),
            "initial_balance": account.get("initial_balance", metadata.get("initial_balance")),
            "final_balance": metadata.get("final_balance", summary_all.get("equity_final")),
            "total_trades": len(trades),
            "win_rate": summary_all.get("win_rate_pct"),
            "profit_factor": summary_all.get("profit_factor"),
            "sharpe_ratio": summary_all.get("sharpe_ratio"),
            "max_drawdown": summary_all.get("max_drawdown_pct"),
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
            "alias": reporting.get("alias", metadata.get("alias")),
            "description": reporting.get("description", metadata.get("description")),
            "engine_type": metadata.get("engine_type"),
            "data_resolution": metadata.get("data_resolution"),
            "metadata": metadata,
            "result": result_payload,
            "analytics": analytics,
        }

    def get_backtest_trades(self, backtest_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all trades for a backtest.

        Args:
            backtest_id (int): Backtest ID

        Returns:
            list: List of trade dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            snapshot_row = cursor.execute(
                "SELECT result FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()
            if snapshot_row:
                result_payload = _json_loads(snapshot_row["result"], {}) or {}
                trades = result_payload.get("trades", []) or []
                if isinstance(trades, list):
                    return trades
            return []

        except Exception as e:
            logger.error(f"Error getting backtest trades: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_backtest_equity_curve(self, backtest_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve equity curve for a backtest.

        Args:
            backtest_id (int): Backtest ID

        Returns:
            list: List of equity point dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            snapshot_row = cursor.execute(
                "SELECT result FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()
            if snapshot_row:
                result_payload = _json_loads(snapshot_row["result"], {}) or {}
                equity_curve = result_payload.get("equity_curve", []) or []
                if isinstance(equity_curve, list):
                    return equity_curve
            return []

        except Exception as e:
            logger.error(f"Error getting backtest equity curve: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_backtest_finance_metrics(self, backtest_id: int) -> Dict[str, Any]:
        """
        Retrieve all finance metrics for a backtest (Layer 3: Derived).

        Args:
            backtest_id (int): Backtest ID

        Returns:
            dict: All finance metrics combined
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)  # Add timeout
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            snapshot_row = cursor.execute(
                "SELECT analytics FROM backtests WHERE id = ?",
                (backtest_id,),
            ).fetchone()
            if snapshot_row:
                analytics = _json_loads(snapshot_row["analytics"], {}) or {}
                if isinstance(analytics, dict):
                    return {
                        "trade_metrics": analytics.get("metrics", {}),
                        "return_metrics": analytics.get("returns", {}),
                        "drawdown_metrics": analytics.get("drawdowns", {}),
                        "ratio_metrics": analytics.get("ratios", {}),
                        "risk_metrics": analytics.get("risks", {}),
                        "efficiency_metrics": analytics.get("efficiency", {}),
                        "benchmark_metrics": analytics.get("benchmark", {}),
                        "summary": analytics.get("summary", {}),
                    }
            return {}

        except Exception as e:
            logger.error(f"Error getting backtest finance metrics: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_all_backtests(
        self,
        user_id: Optional[int] = None,
        strategy_version_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all backtest runs with optional filters.

        Args:
            user_id (int, optional): Filter by user ID
            strategy_version_id (int, optional): Filter by strategy version
            status (str, optional): Filter by status
            limit (int): Maximum number of results

        Returns:
            list: List of backtest run dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            snapshot_rows = cursor.execute(
                "SELECT id, metadata, result, analytics FROM backtests ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            if snapshot_rows:
                results = []
                for row in snapshot_rows:
                    metadata = _json_loads(row["metadata"], {}) or {}
                    result_payload = _json_loads(row["result"], {}) or {}
                    analytics = _json_loads(row["analytics"], {}) or {}
                    account = metadata.get("account", {}) if isinstance(metadata, dict) else {}
                    data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
                    reporting = metadata.get("reporting", {}) if isinstance(metadata, dict) else {}
                    strategy = metadata.get("strategy", {}) if isinstance(metadata, dict) else {}
                    record = {
                        "backtest_id": int(row["id"]),
                        "strategy_id": metadata.get("strategy_id"),
                        "strategy_version_id": metadata.get("strategy_version_id"),
                        "status": metadata.get("status", "completed"),
                        "alias": reporting.get("alias", metadata.get("alias")),
                        "description": reporting.get("description", metadata.get("description")),
                        "strategy_name": metadata.get("strategy_name") or strategy.get("name"),
                        "start_date": data.get("start") or metadata.get("start_date"),
                        "end_date": data.get("end") or metadata.get("end_date"),
                        "symbols": data.get("symbols", []) or metadata.get("symbols", []),
                        "timeframes": [data.get("timeframe")] if data.get("timeframe") else metadata.get("timeframes", []),
                        "initial_balance": account.get("initial_balance", metadata.get("initial_balance")),
                        "final_balance": metadata.get("final_balance"),
                        "engine_type": metadata.get("engine_type"),
                        "data_resolution": metadata.get("data_resolution"),
                        "config_hash": metadata.get("config_hash"),
                        "created_at": metadata.get("created_at"),
                        "completed_at": metadata.get("completed_at"),
                        "total_trades": len((result_payload.get("trades") or [])),
                    }

                    if user_id is not None and metadata.get("user_id") != user_id:
                        continue
                    if strategy_version_id is not None and metadata.get("strategy_version_id") != strategy_version_id:
                        continue
                    if status is not None and metadata.get("status") != status:
                        continue
                    results.append(record)

                return results

            return []

        except Exception as e:
            logger.error(f"Error getting all backtests: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_backtest_status(
        self, backtest_id: int, status: str, final_balance: Optional[float] = None
    ) -> bool:
        """Update status in the canonical snapshot metadata."""
        from haruquant.analytics import get_analytics_overview

        snapshot = self.get_backtest_snapshot(backtest_id) or {"metadata": {}, "result": {}, "analytics": {}}
        metadata = dict(snapshot.get("metadata") or {})
        metadata["status"] = status
        metadata["updated_at"] = datetime.utcnow().isoformat()
        if final_balance is not None:
            metadata["final_balance"] = float(final_balance)
            metadata["completed_at"] = datetime.utcnow().isoformat()

        analytics = dict(snapshot.get("analytics") or {})
        if status == "completed" and not analytics:
            result = snapshot.get("result") or {}
            trades = result.get("trades", []) or []
            account = metadata.get("account", {}) if isinstance(metadata, dict) else {}
            data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
            initial_balance = float(account.get("initial_balance", metadata.get("initial_balance", 0.0)) or 0.0)
            analytics = get_analytics_overview(
                trades=trades,
                initial_balance=initial_balance,
                start_time=data.get("start") or metadata.get("start_date"),
                end_time=data.get("end") or metadata.get("end_date"),
            )

        return self.save_backtest_snapshot(
            backtest_id=backtest_id,
            metadata=metadata,
            result=snapshot.get("result") or {},
            analytics=analytics,
            status=status,
            final_balance=final_balance,
        )

    def save_backtest_trades(self, backtest_id: int, trades: List[Any]) -> bool:
        """Save trades into the canonical snapshot payload."""
        if not trades:
            return True
        snapshot = self.get_backtest_snapshot(backtest_id) or {
            "metadata": {"backtest_id": backtest_id},
            "result": {},
            "analytics": {},
        }
        result = dict(snapshot.get("result") or {})
        result["trades"] = _json_ready(trades)
        return self.save_backtest_snapshot(
            backtest_id=backtest_id,
            metadata=snapshot.get("metadata") or {},
            result=result,
            analytics=snapshot.get("analytics") or {},
            status=(snapshot.get("metadata") or {}).get("status"),
        )

    def save_backtest_equity_curve(self, backtest_id: int, equity_curve: List[Any]) -> bool:
        """Save equity curve points into the canonical snapshot payload."""
        if not equity_curve:
            return True
        snapshot = self.get_backtest_snapshot(backtest_id) or {
            "metadata": {"backtest_id": backtest_id},
            "result": {},
            "analytics": {},
        }
        result = dict(snapshot.get("result") or {})
        result["equity_curve"] = _json_ready(equity_curve)
        return self.save_backtest_snapshot(
            backtest_id=backtest_id,
            metadata=snapshot.get("metadata") or {},
            result=result,
            analytics=snapshot.get("analytics") or {},
            status=(snapshot.get("metadata") or {}).get("status"),
        )

    def update_backtest_metadata(
        self,
        backtest_id: int,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        if alias is None and description is None:
            return True
        snapshot = self.get_backtest_snapshot(backtest_id) or {"metadata": {}, "result": {}, "analytics": {}}
        metadata = dict(snapshot.get("metadata") or {})
        if alias is not None:
            metadata["alias"] = alias
            metadata.setdefault("reporting", {})["alias"] = alias
        if description is not None:
            metadata["description"] = description
            metadata.setdefault("reporting", {})["description"] = description
        metadata["updated_at"] = datetime.utcnow().isoformat()
        return self.save_backtest_snapshot(
            backtest_id=backtest_id,
            metadata=metadata,
            result=snapshot.get("result") or {},
            analytics=snapshot.get("analytics") or {},
        )

    def load_backtest_result(self, backtest_id: int) -> Optional[Any]:
        """
        Load a BacktestResult from database.

        Args:
            backtest_id: Backtest ID

        Returns:
            BacktestResult instance or None if not found
        """
        try:
            from apps.backtest.result import BacktestResult, EquityPoint, TradeRecord
        except ImportError:
            logger.error("Could not import apps.backtest.result")
            return None

        # Get run metadata
        run = self.get_backtest_run(backtest_id)
        if not run:
            logger.warning(f"Backtest {backtest_id} not found")
            return None

        # Get trades
        trades_data = self.get_backtest_trades(backtest_id)
        trades = []
        for trade_dict in trades_data:
            trade = TradeRecord(
                ticket=trade_dict["ticket"],
                symbol=trade_dict["symbol"],
                type=trade_dict["side"],
                open_time=pd.to_datetime(trade_dict["open_time"]),
                close_time=pd.to_datetime(trade_dict["close_time"]),
                open_price=trade_dict["open_price"],
                close_price=trade_dict["close_price"],
                size=trade_dict["position_size"],
                profit_loss=trade_dict["pnl"],
                profit_loss_pips=trade_dict["pnl_pips"],
                commission=trade_dict["commission"],
                swap=trade_dict["swap"] or 0.0,
                mae_usd=trade_dict["mae_usd"],
                mae_pips=trade_dict["mae_pips"],
                mfe_usd=trade_dict["mfe_usd"],
                mfe_pips=trade_dict["mfe_pips"],
                r_multiple=trade_dict["r_multiple"],
                initial_risk_pips=trade_dict["initial_risk_pips"],
                initial_risk_usd=trade_dict["initial_risk_usd"],
                time_in_trade=trade_dict["time_in_trade_seconds"],
                bars_in_trade=trade_dict["bars_in_trade"],
                strategy_name=trade_dict["strategy_name"],
            )
            trades.append(trade)

        # Get equity curve
        equity_data = self.get_backtest_equity_curve(backtest_id)
        equity_curve = []
        for point_dict in equity_data:
            point = EquityPoint(
                timestamp=pd.to_datetime(point_dict["timestamp"]),
                balance=point_dict["balance"],
                equity=point_dict["equity"],
                drawdown=point_dict["drawdown"],
                drawdown_percent=0.0,  # Can be calculated if needed
            )
            equity_curve.append(point)

        # Extract symbol and timeframe
        symbols_data = run.get("symbols")
        if isinstance(symbols_data, str):
            symbols = json.loads(symbols_data) if symbols_data else ["UNKNOWN"]
        elif isinstance(symbols_data, list):
            symbols = symbols_data
        else:
            symbols = ["UNKNOWN"]

        timeframes_data = run.get("timeframes")
        if isinstance(timeframes_data, str):
            timeframes = json.loads(timeframes_data) if timeframes_data else ["H1"]
        elif isinstance(timeframes_data, list):
            timeframes = timeframes_data
        else:
            timeframes = ["H1"]

        symbol = symbols[0] if symbols else "UNKNOWN"
        timeframe = timeframes[0] if timeframes else "H1"

        # Calculate final equity
        final_equity = equity_curve[-1].equity if equity_curve else run["final_balance"]

        # Create BacktestResult
        result = BacktestResult(
            strategy_name=run["strategy_name"],
            symbol=symbol,
            timeframe=timeframe,
            start_date=pd.to_datetime(run["start_date"]),
            end_date=pd.to_datetime(run["end_date"]),
            initial_balance=run["initial_balance"],
            backtest_mode=run.get("engine_type", "vectorized"),
            data_step_mode=run.get("data_resolution", "trading_timeframe"),
            final_balance=run["final_balance"],
            final_equity=final_equity,
            trades=trades,
            equity_curve=equity_curve,
            metadata={
                "backtest_id": backtest_id,
                "alias": run.get("alias"),
                "description": run.get("description"),
                "strategy_version": run.get("strategy_version"),
                "config_hash": run.get("config_hash"),
            },
        )

        logger.info(f"Loaded BacktestResult (ID: {backtest_id})")
        return result

    def query_backtests(
        self,
        strategy_name: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_profit_factor: Optional[float] = None,
        min_trades: Optional[int] = None,
        start_date_after: Optional[datetime] = None,
        start_date_before: Optional[datetime] = None,
        limit: int = 100,
        order_by: str = "sharpe",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Query backtests with filters."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, metadata, result, analytics FROM backtests ORDER BY id DESC"
            )
            rows = cursor.fetchall()

            order_column_map = {
                "sharpe": "rm.sharpe",
                "sortino": "rm.sortino",
                "profit_factor": "tm.profit_factor",
                "total_return": "retm.total_return",
                "cagr": "retm.cagr",
                "win_rate": "tm.win_rate",
                "total_trades": "tm.total_trades",
                "max_drawdown": "dm.max_drawdown_pct",
            }
            results = []
            for row in rows:
                metadata = _json_loads(row[1], {}) or {}
                result_payload = _json_loads(row[2], {}) or {}
                analytics = _json_loads(row[3], {}) or {}
                summary_all = (
                    (analytics.get("summary", {}) or {}).get("all", {})
                    if isinstance(analytics, dict)
                    else {}
                )
                account = metadata.get("account", {}) if isinstance(metadata, dict) else {}
                data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
                reporting = metadata.get("reporting", {}) if isinstance(metadata, dict) else {}
                strategy = metadata.get("strategy", {}) if isinstance(metadata, dict) else {}

                record = {
                    "backtest_id": int(row[0]),
                    "strategy_id": metadata.get("strategy_id"),
                    "strategy_version_id": metadata.get("strategy_version_id"),
                    "status": metadata.get("status", "completed"),
                    "alias": reporting.get("alias", metadata.get("alias")),
                    "description": reporting.get("description", metadata.get("description")),
                    "strategy_name": metadata.get("strategy_name") or strategy.get("name"),
                    "start_date": data.get("start") or metadata.get("start_date"),
                    "end_date": data.get("end") or metadata.get("end_date"),
                    "symbols": data.get("symbols", []) or metadata.get("symbols", []),
                    "timeframes": [data.get("timeframe")] if data.get("timeframe") else metadata.get("timeframes", []),
                    "initial_balance": account.get("initial_balance", metadata.get("initial_balance")),
                    "final_balance": metadata.get("final_balance"),
                    "engine_type": metadata.get("engine_type"),
                    "data_resolution": metadata.get("data_resolution"),
                    "config_hash": metadata.get("config_hash"),
                    "created_at": metadata.get("created_at"),
                    "completed_at": metadata.get("completed_at"),
                    "total_trades": len((result_payload.get("trades") or [])),
                    "win_rate": summary_all.get("win_rate_pct", summary_all.get("win_rate")),
                    "profit_factor": summary_all.get("profit_factor"),
                    "sharpe": summary_all.get("sharpe_ratio"),
                    "sortino": summary_all.get("sortino_ratio"),
                    "calmar": summary_all.get("calmar_ratio"),
                    "max_drawdown_pct": summary_all.get("max_drawdown_pct"),
                    "total_return": summary_all.get("return_pct", summary_all.get("total_return")),
                    "cagr": summary_all.get("cagr_pct", summary_all.get("cagr")),
                }

                if strategy_name is not None and record.get("strategy_name") != strategy_name:
                    continue
                if user_id is not None and metadata.get("user_id") != user_id:
                    continue
                if status is not None and record.get("status") != status:
                    continue
                if min_sharpe is not None and (record.get("sharpe") is None or record.get("sharpe") < min_sharpe):
                    continue
                if max_drawdown is not None and (record.get("max_drawdown_pct") is None or record.get("max_drawdown_pct") > max_drawdown):
                    continue
                if min_profit_factor is not None and (record.get("profit_factor") is None or record.get("profit_factor") < min_profit_factor):
                    continue
                if min_trades is not None and (record.get("total_trades") is None or record.get("total_trades") < min_trades):
                    continue
                if start_date_after is not None and record.get("start_date") and str(record.get("start_date")) < str(start_date_after):
                    continue
                if start_date_before is not None and record.get("start_date") and str(record.get("start_date")) > str(start_date_before):
                    continue

                results.append(record)

            sort_key = order_by if order_by in order_column_map else "sharpe"

            def _sort_value(item: Dict[str, Any]) -> Any:
                value = item.get(sort_key)
                if value is None:
                    return float("-inf") if not ascending else float("inf")
                return value

            results.sort(key=_sort_value, reverse=not ascending)
            return results[:limit]

        except Exception as e:
            logger.error(f"Error querying backtests: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _build_backtest_filters(
        self,
        strategy_name: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_profit_factor: Optional[float] = None,
        min_trades: Optional[int] = None,
        start_date_after: Optional[datetime] = None,
        start_date_before: Optional[datetime] = None,
    ) -> tuple[str, List[Any]]:
        """Build SQL filter clause and parameters."""
        conditions = []
        params: List[Any] = []

        # List of (value, sql_condition) pairs
        filters = [
            (strategy_name, "br.strategy_name = ?"),
            (user_id, "br.user_id = ?"),
            (status, "br.status = ?"),
            (min_sharpe, "rm.sharpe >= ?"),
            (max_drawdown, "dm.max_drawdown_pct <= ?"),
            (min_profit_factor, "tm.profit_factor >= ?"),
            (min_trades, "tm.total_trades >= ?"),
            (start_date_after, "br.start_date >= ?"),
            (start_date_before, "br.start_date <= ?"),
        ]

        for value, condition in filters:
            if value is not None:
                conditions.append(condition)
                params.append(value)

        clause = ""
        if conditions:
            clause = " AND " + " AND ".join(conditions)

        return clause, params

    def compare_backtests(
        self, backtest_ids: List[int], metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Compare multiple backtests side-by-side."""
        if metrics is None:
            metrics = [
                "total_trades",
                "win_rate",
                "profit_factor",
                "sharpe",
                "sortino",
                "max_drawdown_pct",
                "total_return",
                "cagr",
            ]

        rows = self.query_backtests(limit=1000)

        # Filter to requested IDs
        rows = [r for r in rows if r["backtest_id"] in backtest_ids]

        comparison_data = []
        for row in rows:
            data = {
                "backtest_id": row["backtest_id"],
                "alias": row.get("alias", "N/A"),
                "strategy_name": row["strategy_name"],
            }

            for metric in metrics:
                data[metric] = row.get(metric)

            comparison_data.append(data)

        df = pd.DataFrame(comparison_data)
        return df

    def export_backtest_to_json(
        self,
        backtest_id: int,
        output_path: Optional[str] = None,
        include_trades: bool = True,
        include_equity: bool = False,
    ) -> Optional[str]:
        """Export backtest to JSON file."""
        snapshot = self.get_backtest_snapshot(backtest_id)
        if not snapshot:
            logger.warning(f"Backtest {backtest_id} not found")
            return None

        export_data: Dict[str, Any] = {
            "backtest_run": snapshot.get("metadata", {}),
            "result": snapshot.get("result", {}),
            "analytics": snapshot.get("analytics", {}),
        }

        if include_trades:
            export_data["trades"] = snapshot.get("result", {}).get("trades", [])

        if include_equity:
            export_data["equity_curve"] = snapshot.get("result", {}).get("equity_curve", [])

        if output_path is None:
            alias = (snapshot.get("metadata", {}) or {}).get("alias", "backtest")
            output_path = f"{alias}_{backtest_id}.json"

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported backtest {backtest_id} to {output_path}")
        return output_path

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM backtests")
            json_backtests = int(cursor.fetchone()[0] or 0)
            if json_backtests > 0:
                stats["total_backtests"] = json_backtests

                cursor.execute("SELECT result FROM backtests")
                stats["total_trades"] = 0
                for (result_text,) in cursor.fetchall():
                    result_payload = _json_loads(result_text, {}) or {}
                    stats["total_trades"] += len(result_payload.get("trades", []) or [])

                cursor.execute("SELECT COUNT(*) FROM optimization_runs")
                stats["total_optimizations"] = cursor.fetchone()[0]

                cursor.execute("SELECT metadata FROM backtests")
                unique_strategies = set()
                for (metadata_text,) in cursor.fetchall():
                    metadata = _json_loads(metadata_text, {}) or {}
                    strategy = metadata.get("strategy", {}) if isinstance(metadata, dict) else {}
                    unique_strategies.add(strategy.get("name") or metadata.get("strategy_name"))
                stats["unique_strategies"] = len([name for name in unique_strategies if name])

                cursor.execute("SELECT metadata FROM backtests")
                timestamps = []
                for (metadata_text,) in cursor.fetchall():
                    metadata = _json_loads(metadata_text, {}) or {}
                    timestamps.extend(
                        [
                            metadata.get("created_at"),
                            metadata.get("completed_at"),
                            metadata.get("updated_at"),
                        ]
                    )
                timestamps = [ts for ts in timestamps if ts]
                stats["first_backtest"] = min(timestamps) if timestamps else None
                stats["latest_backtest"] = max(timestamps) if timestamps else None
                return stats
            return stats
        except Exception:
            return {}
        finally:
            if conn:
                conn.close()

    def delete_backtest(self, backtest_id: int) -> bool:
        """
        Delete a backtest run and all associated data (cascades to all layers).

        Args:
            backtest_id (int): Backtest ID

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM backtests WHERE id = ?", (backtest_id,))

            if cursor.rowcount == 0:
                logger.warning(f"Backtest {backtest_id} not found.")
                return False

            conn.commit()
            logger.info(f"Backtest {backtest_id} deleted successfully.")
            return True

        except Exception as e:
            logger.error(f"Error deleting backtest: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

