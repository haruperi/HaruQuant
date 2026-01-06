"""Backtest management module."""

import contextlib
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.logger import logger


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
        """
        Create a new backtest run (Layer 1: Run).

        Returns:
            int: Backtest ID (auto-increment)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert lists to JSON
            symbols_json = json.dumps(symbols) if symbols else None
            timeframes_json = json.dumps(timeframes) if timeframes else None

            query = """
            INSERT INTO backtest_runs (
                strategy_version_id, user_id, status, alias, description,
                strategy_name, strategy_version, start_date, end_date,
                symbols, timeframes, initial_balance,
                commission_model, slippage_model, spread_model,
                execution_model, fill_model, risk_model, position_sizing_model,
                engine_type, data_resolution, config_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    strategy_version_id,
                    user_id,
                    "pending",
                    alias,
                    description,
                    strategy_name,
                    strategy_version,
                    start_date,
                    end_date,
                    symbols_json,
                    timeframes_json,
                    initial_balance,
                    commission_model,
                    slippage_model,
                    spread_model,
                    execution_model,
                    fill_model,
                    risk_model,
                    position_sizing_model,
                    engine_type,
                    data_resolution,
                    config_hash,
                ),
            )

            backtest_id = cursor.lastrowid
            if backtest_id is None:
                raise ValueError("Failed to retrieve backtest ID after insertion.")

            conn.commit()
            logger.info(f"Backtest run {backtest_id} created successfully.")
            return int(backtest_id)

        except Exception as e:
            logger.error(f"Error creating backtest run: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_backtest_result(
        self, backtest_result, backtest_id: Optional[int] = None
    ) -> int:
        """
        Save complete BacktestResult to database using 4-layer architecture.

        Args:
            backtest_result: BacktestResult instance
            backtest_id: Optional existing backtest ID. If None, creates new run.

        Returns:
            int: Backtest ID
        """
        self._ensure_backtest_result_type(backtest_result)

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

            # =====================================================================
            # LAYER 1: Create/Update Run
            # =====================================================================

            if backtest_id is None:
                backtest_id = self._create_backtest_from_result(backtest_result)

            # Update final balance and status
            cursor.execute(
                """
                UPDATE backtest_runs
                SET final_balance = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE backtest_id = ?
                """,
                (backtest_result.final_balance, backtest_id),
            )

            # =====================================================================
            # LAYER 2: Save Facts (Trades & Equity)
            # =====================================================================

            # Save trades
            self._save_trades(cursor, backtest_id, backtest_result.trades)

            # Save equity curve
            self._save_equity_curve(cursor, backtest_id, backtest_result.equity_curve)

            # =====================================================================
            # LAYER 3: Save Derived Finance Metrics
            # =====================================================================

            self._save_finance_metrics(cursor, backtest_id, backtest_result)

            conn.commit()
            logger.info(
                f"BacktestResult saved successfully to database (ID: {backtest_id})"
            )
            logger.info(f"  - {len(backtest_result.trades)} trades")
            logger.info(f"  - {len(backtest_result.equity_curve)} equity points")
            logger.info("  - 6 finance metric tables populated")

            return backtest_id

        except Exception as e:
            logger.error(f"Error saving backtest result: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _ensure_backtest_result_type(self, backtest_result: Any) -> None:
        """Ensure the object is a BacktestResult instance."""
        try:
            from apps.backtest.result import BacktestResult

            if not isinstance(backtest_result, BacktestResult):
                raise ValueError("backtest_result must be a BacktestResult instance")
        except ImportError:
            logger.warning("Could not import BacktestResult for type checking.")

    def _create_backtest_from_result(self, backtest_result: Any) -> int:
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
        """Save derived finance metrics."""
        comp_summary = backtest_result.comprehensive_summary()

        # Save trade metrics
        cursor.execute(
            """
            INSERT INTO finance_trade_metrics (
                backtest_id, total_trades, winning_trades, losing_trades,
                win_rate, loss_rate, avg_win, avg_loss, largest_win, largest_loss,
                expectancy, expectancy_r, profit_factor, payoff_ratio, edge_ratio,
                avg_r_multiple, median_r_multiple, max_r_multiple, min_r_multiple,
                max_consecutive_wins, max_consecutive_losses,
                avg_time_in_trade, median_time_in_trade, sqn, trade_efficiency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("total_trades", 0),
                comp_summary.get("winning_trades", 0),
                comp_summary.get("losing_trades", 0),
                comp_summary.get("win_rate", 0),
                comp_summary.get("loss_rate", 0),
                comp_summary.get("avg_win", 0),
                comp_summary.get("avg_loss", 0),
                comp_summary.get("largest_win", 0),
                comp_summary.get("largest_loss", 0),
                comp_summary.get("expectancy", 0),
                comp_summary.get("expectancy_r", 0),
                comp_summary.get("profit_factor", 0),
                comp_summary.get("payoff_ratio", 0),
                comp_summary.get("edge_ratio", 0),
                comp_summary.get("avg_r_multiple", 0),
                comp_summary.get("median_r_multiple", 0),
                comp_summary.get("max_r_multiple", 0),
                comp_summary.get("min_r_multiple", 0),
                comp_summary.get("max_consecutive_wins", 0),
                comp_summary.get("max_consecutive_losses", 0),
                comp_summary.get("avg_time_in_trade", 0),
                comp_summary.get("median_time_in_trade", 0),
                comp_summary.get("sqn", 0),
                comp_summary.get("trade_efficiency", 0),
            ),
        )

        # Save return metrics
        cursor.execute(
            """
            INSERT INTO finance_return_metrics (
                backtest_id, net_profit, gross_profit, gross_loss,
                total_return, cagr, annualized_return,
                volatility, annualized_volatility, downside_volatility,
                skew, kurtosis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("net_profit", 0),
                comp_summary.get("gross_profit", 0),
                comp_summary.get("gross_loss", 0),
                comp_summary.get("total_return", 0),
                comp_summary.get("cagr", 0),
                comp_summary.get("annualized_return", 0),
                comp_summary.get("return_volatility", 0),
                comp_summary.get("annualized_volatility", 0),
                comp_summary.get("downside_return_volatility", 0),
                comp_summary.get("return_skewness", 0),
                comp_summary.get("return_kurtosis", 0),
            ),
        )

        # Save drawdown metrics
        cursor.execute(
            """
            INSERT INTO finance_drawdown_metrics (
                backtest_id, max_drawdown, max_drawdown_pct, avg_drawdown,
                max_drawdown_duration, avg_drawdown_duration,
                ulcer_index, pain_index, pain_ratio, recovery_factor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("max_drawdown", 0),
                comp_summary.get("max_drawdown_pct", 0),
                comp_summary.get("avg_drawdown", 0),
                comp_summary.get("max_drawdown_duration", 0),
                comp_summary.get("avg_drawdown_duration", 0),
                comp_summary.get("ulcer_index", 0),
                comp_summary.get("pain_index", 0),
                comp_summary.get("pain_ratio", 0),
                comp_summary.get("recovery_factor", 0),
            ),
        )

        # Save ratio metrics
        cursor.execute(
            """
            INSERT INTO finance_ratio_metrics (
                backtest_id, sharpe, sortino, calmar, omega,
                information_ratio, gain_to_pain,
                profit_to_mae_ratio, mfe_to_mae_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("sharpe_ratio", 0),
                comp_summary.get("sortino_ratio", 0),
                comp_summary.get("calmar_ratio", 0),
                comp_summary.get("omega_ratio", 0),
                comp_summary.get("information_ratio", 0),
                comp_summary.get("gain_to_pain_ratio", 0),
                comp_summary.get("profit_to_mae_ratio", 0),
                comp_summary.get("mfe_to_mae_ratio", 0),
            ),
        )

        # Save risk metrics
        cursor.execute(
            """
            INSERT INTO finance_risk_metrics (
                backtest_id, var_95, cvar_95, var_99, cvar_99,
                risk_of_ruin, max_exposure, avg_exposure, exposure_time_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("value_at_risk_95", 0),
                comp_summary.get("conditional_var_95", 0),
                comp_summary.get("value_at_risk_99", 0),
                comp_summary.get("conditional_var_99", 0),
                comp_summary.get("risk_of_ruin", 0),
                comp_summary.get("max_exposure", 0),
                comp_summary.get("avg_exposure", 0),
                comp_summary.get("exposure_time_ratio", 0),
            ),
        )

        # Save efficiency metrics
        cursor.execute(
            """
            INSERT INTO finance_efficiency_metrics (
                backtest_id, mfe_efficiency, mae_efficiency, exit_efficiency,
                win_efficiency, loss_containment_efficiency,
                time_efficiency, return_per_trade, return_per_unit_risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backtest_id,
                comp_summary.get("mfe_efficiency", 0),
                comp_summary.get("mae_efficiency", 0),
                comp_summary.get("exit_efficiency", 0),
                comp_summary.get("win_efficiency", 0),
                comp_summary.get("loss_containment_efficiency", 0),
                comp_summary.get("time_efficiency", 0),
                comp_summary.get("return_per_trade", 0),
                comp_summary.get("return_per_unit_risk", 0),
            ),
        )

    def get_backtest_run(self, backtest_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a backtest run by ID.

        Args:
            backtest_id (int): Backtest ID

        Returns:
            dict: Backtest run details or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM backtest_runs WHERE backtest_id = ?"
            cursor.execute(query, (backtest_id,))
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Parse JSON fields
            if result.get("symbols"):
                with contextlib.suppress(json.JSONDecodeError):
                    result["symbols"] = json.loads(result["symbols"])

            if result.get("timeframes"):
                with contextlib.suppress(json.JSONDecodeError):
                    result["timeframes"] = json.loads(result["timeframes"])

            return result

        except Exception as e:
            logger.error(f"Error getting backtest run: {e}")
            raise
        finally:
            if conn:
                conn.close()

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

            query = """
            SELECT * FROM backtest_trades
            WHERE backtest_id = ?
            ORDER BY open_time
            """
            cursor.execute(query, (backtest_id,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

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

            query = """
            SELECT * FROM backtest_equity_curve
            WHERE backtest_id = ?
            ORDER BY timestamp
            """
            cursor.execute(query, (backtest_id,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

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

            metrics = {}

            # Fetch all metrics in parallel using executemany would be ideal, but SQLite doesn't support that well
            # Instead, let's fetch them all quickly in sequence with a single connection
            queries = [
                (
                    "trade_metrics",
                    "SELECT * FROM finance_trade_metrics WHERE backtest_id = ?",
                ),
                (
                    "return_metrics",
                    "SELECT * FROM finance_return_metrics WHERE backtest_id = ?",
                ),
                (
                    "drawdown_metrics",
                    "SELECT * FROM finance_drawdown_metrics WHERE backtest_id = ?",
                ),
                (
                    "ratio_metrics",
                    "SELECT * FROM finance_ratio_metrics WHERE backtest_id = ?",
                ),
                (
                    "risk_metrics",
                    "SELECT * FROM finance_risk_metrics WHERE backtest_id = ?",
                ),
                (
                    "efficiency_metrics",
                    "SELECT * FROM finance_efficiency_metrics WHERE backtest_id = ?",
                ),
            ]

            for key, query in queries:
                cursor.execute(query, (backtest_id,))
                row = cursor.fetchone()
                if row:
                    metrics[key] = dict(row)

            return metrics

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

            query = """
            SELECT br.*, sv.strategy_id
            FROM backtest_runs br
            LEFT JOIN strategy_versions sv ON br.strategy_version_id = sv.id
            WHERE 1=1
            """
            params: List[Any] = []

            if user_id is not None:
                query += " AND br.user_id = ?"
                params.append(user_id)

            if strategy_version_id is not None:
                query += " AND br.strategy_version_id = ?"
                params.append(strategy_version_id)

            if status is not None:
                query += " AND br.status = ?"
                params.append(status)

            query += " ORDER BY br.created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                if result.get("symbols"):
                    with contextlib.suppress(json.JSONDecodeError):
                        result["symbols"] = json.loads(result["symbols"])
                if result.get("timeframes"):
                    with contextlib.suppress(json.JSONDecodeError):
                        result["timeframes"] = json.loads(result["timeframes"])
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting all backtests: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_backtest_status(
        self, backtest_id: int, status: str, final_balance: Optional[float] = None
    ) -> bool:
        """
        Update backtest run status.

        Args:
            backtest_id (int): Backtest ID
            status (str): New status (pending/running/completed/failed)
            final_balance (float, optional): Final balance if completed

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if final_balance is not None:
                query = """
                UPDATE backtest_runs
                SET status = ?, final_balance = ?, completed_at = CURRENT_TIMESTAMP
                WHERE backtest_id = ?
                """
                cursor.execute(query, (status, final_balance, backtest_id))
            else:
                query = "UPDATE backtest_runs SET status = ? WHERE backtest_id = ?"
                cursor.execute(query, (status, backtest_id))

            conn.commit()
            logger.info(f"Backtest {backtest_id} status updated to '{status}'")
            return True

        except Exception as e:
            logger.error(f"Error updating backtest status: {e}")
            if conn:
                conn.rollback()
            raise
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

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                "DELETE FROM backtest_runs WHERE backtest_id = ?", (backtest_id,)
            )

            if cursor.rowcount == 0:
                logger.warning(f"Backtest {backtest_id} not found.")
                return False

            conn.commit()
            logger.info(
                f"Backtest {backtest_id} deleted successfully (cascade to all layers)."
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting backtest: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
