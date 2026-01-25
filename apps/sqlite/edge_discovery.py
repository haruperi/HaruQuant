"""Edge Discovery database management module."""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.logger import logger

from .base import DatabaseBase


class EdgeDiscoveryManager(DatabaseBase):
    """Edge Discovery database operations."""

    def save_edge_result(  # noqa: C901
        self,
        result: Dict[str, Any],
        user_id: Optional[int] = None,
        save_trades: bool = True,
    ) -> Optional[int]:
        """
        Save an edge discovery result to the database.

        Args:
            result: EdgeResult as dictionary (from EdgeResult.to_dict())
            user_id: Optional user ID
            save_trades: Whether to save individual trades

        Returns:
            run_id if successful, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = result.get("stats", {})
            config = result.get("config", {})

            # Map EDS name to type
            eds_name = result.get("eds_name", "")
            eds_type_map = {
                "EDS-0": "null",
                "EDS-1": "mr",
                "EDS-2": "tp",
                "EDS-3": "session",
            }
            eds_type = "unknown"
            for prefix, etype in eds_type_map.items():
                if eds_name.startswith(prefix):
                    eds_type = etype
                    break

            # Determine verdict
            ci_low = stats.get("ci_low", 0)
            p_value = stats.get("p_value_perm", 1)
            n_trades = stats.get("n_trades", 0)
            expectancy = stats.get("expectancy_r", 0)

            if n_trades < 30:
                verdict = "INSUFFICIENT_DATA"
            elif ci_low > 0 and p_value < 0.05:
                verdict = "EDGE_CONFIRMED"
            elif ci_low > 0:
                verdict = "POTENTIAL_EDGE"
            elif expectancy > 0:
                verdict = "WEAK_SIGNAL"
            else:
                verdict = "NO_EDGE"

            edge_confirmed = ci_low > 0 and p_value < 0.05

            # Insert run
            run_query = """
            INSERT INTO edge_discovery_runs (
                user_id, symbol, timeframe, eds_name, eds_type, config,
                start_pos, end_pos, bar_count,
                n_trades, expectancy_r, win_rate, profit_factor,
                ci_low, ci_high, p_value_perm,
                verdict, edge_confirmed,
                n_boot, n_perm, block_size, ci_level,
                extras
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Extract bootstrap/perm config from config if available
            bootstrap_cfg = config.get("bootstrap", {})
            perm_cfg = config.get("perm", {})

            cursor.execute(
                run_query,
                (
                    user_id,
                    result.get("symbol", ""),
                    result.get("timeframe", ""),
                    eds_name,
                    eds_type,
                    json.dumps(config),
                    config.get("data", {}).get("start_pos", 0),
                    config.get("data", {}).get("end_pos", 5000),
                    n_trades,  # bar_count approximated
                    n_trades,
                    stats.get("expectancy_r", 0),
                    stats.get("win_rate", 0),
                    stats.get("profit_factor", 0),
                    ci_low,
                    stats.get("ci_high", 0),
                    p_value,
                    verdict,
                    edge_confirmed,
                    bootstrap_cfg.get("n_boot", 2000),
                    perm_cfg.get("n_perm", 2000),
                    bootstrap_cfg.get("block_size", 20),
                    bootstrap_cfg.get("ci_level", 0.95),
                    json.dumps(stats.get("extras")) if stats.get("extras") else None,
                ),
            )

            run_id = cursor.lastrowid

            # Insert stats
            stats_query = """
            INSERT INTO edge_discovery_stats (
                run_id, n_trades, expectancy_r, win_rate, profit_factor,
                median_mae_r, median_mfe_r, avg_hold_bars,
                ci_low, ci_high, p_value_perm, extras
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                stats_query,
                (
                    run_id,
                    n_trades,
                    stats.get("expectancy_r", 0),
                    stats.get("win_rate", 0),
                    stats.get("profit_factor", 0),
                    stats.get("median_mae_r", 0),
                    stats.get("median_mfe_r", 0),
                    stats.get("avg_hold_bars", 0),
                    ci_low,
                    stats.get("ci_high", 0),
                    p_value,
                    json.dumps(stats.get("extras")) if stats.get("extras") else None,
                ),
            )

            # Insert trades if requested
            if save_trades:
                trades = result.get("trades", [])
                if trades:
                    trade_query = """
                    INSERT INTO edge_discovery_trades (
                        run_id, entry_time, exit_time, side,
                        entry_price, exit_price, r_multiple,
                        mae_r, mfe_r, hold_bars, meta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    for trade in trades:
                        cursor.execute(
                            trade_query,
                            (
                                run_id,
                                trade.get("entry_time"),
                                trade.get("exit_time"),
                                trade.get("side"),
                                trade.get("entry_price"),
                                trade.get("exit_price"),
                                trade.get("r_multiple"),
                                trade.get("mae_r"),
                                trade.get("mfe_r"),
                                trade.get("hold_bars"),
                                (
                                    json.dumps(trade.get("meta"))
                                    if trade.get("meta")
                                    else None
                                ),
                            ),
                        )

            conn.commit()
            logger.info(
                f"Saved edge result: {eds_name} {result.get('symbol')} "
                f"{result.get('timeframe')} -> {verdict} (run_id={run_id})"
            )
            return run_id

        except Exception as e:
            logger.error(f"Error saving edge result: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def get_edge_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve an edge discovery run by ID.

        Args:
            run_id: The run ID

        Returns:
            Run data as dictionary, or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM edge_discovery_runs WHERE run_id = ?", (run_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Parse JSON fields
            if result.get("config"):
                result["config"] = json.loads(result["config"])
            if result.get("extras"):
                result["extras"] = json.loads(result["extras"])

            return result

        except Exception as e:
            logger.error(f"Error getting edge run {run_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_edge_runs(  # noqa: C901
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        eds_type: Optional[str] = None,
        verdict: Optional[str] = None,
        edge_confirmed_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve edge discovery runs with optional filtering.

        Args:
            symbol: Filter by symbol
            timeframe: Filter by timeframe
            eds_type: Filter by EDS type (null, mr, tp, session)
            verdict: Filter by verdict
            edge_confirmed_only: Only return confirmed edges
            limit: Max results
            offset: Result offset

        Returns:
            List of run dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM edge_discovery_runs WHERE 1=1"
            params: List[Any] = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            if eds_type:
                query += " AND eds_type = ?"
                params.append(eds_type)
            if verdict:
                query += " AND verdict = ?"
                params.append(verdict)
            if edge_confirmed_only:
                query += " AND edge_confirmed = 1"

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get("config"):
                    result["config"] = json.loads(result["config"])
                if result.get("extras"):
                    result["extras"] = json.loads(result["extras"])
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting edge runs: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_edge_runs_count(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        eds_type: Optional[str] = None,
        verdict: Optional[str] = None,
        edge_confirmed_only: bool = False,
    ) -> int:
        """
        Get total count of edge discovery runs with optional filtering.

        Args:
            symbol: Filter by symbol
            timeframe: Filter by timeframe
            eds_type: Filter by EDS type (null, mr, tp, session)
            verdict: Filter by verdict
            edge_confirmed_only: Only count confirmed edges

        Returns:
            Count of runs
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT COUNT(*) FROM edge_discovery_runs WHERE 1=1"
            params: List[Any] = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            if eds_type:
                query += " AND eds_type = ?"
                params.append(eds_type)
            if verdict:
                query += " AND verdict = ?"
                params.append(verdict)
            if edge_confirmed_only:
                query += " AND edge_confirmed = 1"

            cursor.execute(query, params)
            result = cursor.fetchone()
            return int(result[0]) if result else 0

        except Exception as e:
            logger.error(f"Error getting edge run count: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def _fetch_summary_runs(
        self,
        symbol: Optional[str],
        timeframe: Optional[str],
    ) -> List[sqlite3.Row]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM edge_discovery_runs WHERE 1=1"
            params: List[Any] = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _parse_run_dt(value: Any) -> Optional[datetime]:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return value if isinstance(value, datetime) else None

    def _process_run_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        run = dict(row)
        if run.get("config"):
            run["config"] = json.loads(run["config"])
        if run.get("extras"):
            run["extras"] = json.loads(run["extras"])
        return run

    def _update_grouped_entry(
        self,
        entry: Dict[str, Any],
        run: Dict[str, Any],
        created_at: Optional[datetime],
    ) -> None:
        # Update latest run
        latest = entry["latest_run"]
        if latest is None:
            entry["latest_run"] = run
        else:
            latest_dt = self._parse_run_dt(latest.get("created_at"))
            if created_at and (not latest_dt or created_at > latest_dt):
                entry["latest_run"] = run

        # Update type-specific runs
        eds_type = run.get("eds_type")
        target_key = (
            "mr_run" if eds_type == "mr" else "bo_run" if eds_type == "tp" else None
        )

        if target_key:
            current = entry[target_key]
            if current is None:
                entry[target_key] = run
            else:
                current_dt = self._parse_run_dt(current.get("created_at"))
                if created_at and (not current_dt or created_at > current_dt):
                    entry[target_key] = run

    def _group_summary_rows(self, rows: List[sqlite3.Row]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            run = self._process_run_row(row)
            key = f"{run.get('symbol')}|{run.get('timeframe')}"
            created_at = self._parse_run_dt(run.get("created_at"))

            entry = grouped.setdefault(
                key,
                {
                    "symbol": run.get("symbol"),
                    "timeframe": run.get("timeframe"),
                    "latest_run": None,
                    "mr_run": None,
                    "bo_run": None,
                },
            )
            self._update_grouped_entry(entry, run, created_at)
        return grouped

    def get_edge_summary_rows(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get grouped edge discovery summary rows by symbol and timeframe.

        Returns:
            List of summary dictionaries with latest MR/TP runs per symbol/timeframe.
        """
        try:
            rows = self._fetch_summary_runs(symbol, timeframe)
            grouped = self._group_summary_rows(rows)

            summaries: List[Dict[str, Any]] = []
            for entry in grouped.values():
                latest = entry["latest_run"]
                run_meta = (
                    (latest.get("config") or {}).get("run_meta", {}) if latest else {}
                )

                summaries.append(
                    {
                        "symbol": entry["symbol"],
                        "timeframe": entry["timeframe"],
                        "latest_run_id": latest.get("run_id") if latest else None,
                        "latest_created_at": (
                            latest.get("created_at") if latest else None
                        ),
                        "verdict": latest.get("verdict") if latest else None,
                        "edge_confirmed": latest.get("edge_confirmed") if latest else 0,
                        "range_meta": run_meta,
                        "mr": entry["mr_run"],
                        "bo": entry["bo_run"],
                    }
                )

            return summaries

        except Exception as e:
            logger.error(f"Error getting edge summary rows: {e}")
            return []

    def get_edge_trades(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve trades for an edge discovery run.

        Args:
            run_id: The run ID

        Returns:
            List of trade dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM edge_discovery_trades WHERE run_id = ? ORDER BY entry_time",
                (run_id,),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get("meta"):
                    result["meta"] = json.loads(result["meta"])
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting edge trades for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_edge_stats(self, run_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve stats for an edge discovery run.

        Args:
            run_id: The run ID

        Returns:
            Stats dictionary, or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM edge_discovery_stats WHERE run_id = ?", (run_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)
            if result.get("extras"):
                result["extras"] = json.loads(result["extras"])

            return result

        except Exception as e:
            logger.error(f"Error getting edge stats for run {run_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_confirmed_edges(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get all confirmed edges, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter
            limit: Max results

        Returns:
            List of confirmed edge runs
        """
        return self.get_edge_runs(
            symbol=symbol,
            edge_confirmed_only=True,
            limit=limit,
        )

    def get_edge_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics across all edge discovery runs.

        Returns:
            Summary dictionary with counts and aggregates
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total runs
            cursor.execute("SELECT COUNT(*) FROM edge_discovery_runs")
            total_runs = cursor.fetchone()[0]

            # Confirmed edges
            cursor.execute(
                "SELECT COUNT(*) FROM edge_discovery_runs WHERE edge_confirmed = 1"
            )
            confirmed_count = cursor.fetchone()[0]

            # By verdict
            cursor.execute(
                "SELECT verdict, COUNT(*) FROM edge_discovery_runs GROUP BY verdict"
            )
            by_verdict = {row[0]: row[1] for row in cursor.fetchall()}

            # By EDS type
            cursor.execute(
                "SELECT eds_type, COUNT(*) FROM edge_discovery_runs GROUP BY eds_type"
            )
            by_eds_type = {row[0]: row[1] for row in cursor.fetchall()}

            # By symbol
            cursor.execute(
                "SELECT symbol, COUNT(*) FROM edge_discovery_runs GROUP BY symbol"
            )
            by_symbol = {row[0]: row[1] for row in cursor.fetchall()}

            # Average expectancy for confirmed edges
            cursor.execute(
                "SELECT AVG(expectancy_r) FROM edge_discovery_runs WHERE edge_confirmed = 1"
            )
            avg_expectancy_confirmed = cursor.fetchone()[0] or 0

            return {
                "total_runs": total_runs,
                "confirmed_count": confirmed_count,
                "confirmation_rate": (
                    confirmed_count / total_runs if total_runs > 0 else 0
                ),
                "by_verdict": by_verdict,
                "by_eds_type": by_eds_type,
                "by_symbol": by_symbol,
                "avg_expectancy_confirmed": avg_expectancy_confirmed,
            }

        except Exception as e:
            logger.error(f"Error getting edge summary: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def delete_edge_run(self, run_id: int) -> bool:
        """
        Delete an edge discovery run and all associated data.

        Args:
            run_id: The run ID

        Returns:
            True if deleted, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                "DELETE FROM edge_discovery_runs WHERE run_id = ?", (run_id,)
            )

            if cursor.rowcount == 0:
                logger.warning(f"Edge run {run_id} not found for deletion")
                return False

            conn.commit()
            logger.info(f"Deleted edge run {run_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting edge run {run_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
