"""SQX Strategy Master management module."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from apps.utils.logger import logger


class SQXManager:
    """StrategyQuant X export management operations."""

    db_path: str

    def _apply_column_mapping(
        self, df: pd.DataFrame, mapping: Dict[str, str]
    ) -> pd.DataFrame:
        rename_map = {v: k for k, v in mapping.items() if v in df.columns}
        return df.rename(columns=rename_map)

    def _apply_identity_defaults(self, df: pd.DataFrame) -> None:
        if "strategy_name" not in df.columns and "Strategy Name" in df.columns:
            df["strategy_name"] = df["Strategy Name"]

        if "symbol" not in df.columns:
            if "Symbol (IS)" in df.columns:
                df["symbol"] = df["Symbol (IS)"]
            elif "Symbol" in df.columns:
                df["symbol"] = df["Symbol"]

        if "timeframe" not in df.columns:
            if "TimeFrame (IS)" in df.columns:
                df["timeframe"] = df["TimeFrame (IS)"]
            elif "TimeFrame" in df.columns:
                df["timeframe"] = df["TimeFrame"]

        if "source_symbol" not in df.columns and "symbol" in df.columns:
            df["source_symbol"] = df["symbol"]
        if "source_timeframe" not in df.columns and "timeframe" in df.columns:
            df["source_timeframe"] = df["timeframe"]

    def _canonicalize_dataframe_symbols(self, df: pd.DataFrame) -> None:
        if "symbol" in df.columns:
            df["symbol"] = df["symbol"].apply(self._canonicalize_symbol)
        else:
            logger.error("Missing 'symbol' column after mapping and defaults.")
            raise ValueError("Missing 'symbol' column. Check CSV or mapping.")

        if "strategy_name" not in df.columns:
            logger.error("Missing 'strategy_name' column after mapping and defaults.")
            raise ValueError("Missing 'strategy_name' column. Check CSV or mapping.")

    def _add_metadata_columns(
        self, df: pd.DataFrame, stage: str, import_name: str
    ) -> None:
        df["stage"] = stage
        df["last_seen_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        df["last_import_name"] = import_name

    def _add_stage_specific_metrics(self, df: pd.DataFrame, stage: str) -> None:
        stage_prefix = {
            "A1_OOS2": "a1",
            "A2_OOS3": "a2",
            "E1_WFM": "e1",
        }.get(stage)
        if stage_prefix:
            stage_cols = {
                "profit_factor",
                "ret_dd_ratio",
                "annual_return_pct",
                "trades",
                "net_profit",
                "max_drawdown_pct",
            }
            for col in stage_cols:
                if col in df.columns:
                    df[f"{stage_prefix}_{col}"] = df[col]
        if stage == "B2_SPREAD_MAX" and "ret_dd_ratio" in df.columns:
            df["spread_max_retdd_ratio"] = df["ret_dd_ratio"]

    def _normalize_and_filter_metrics(
        self, df: pd.DataFrame, valid_columns: Set[str]
    ) -> pd.DataFrame:
        df = self._normalize_win_percent(df)
        cols_to_keep = [c for c in df.columns if c in valid_columns]
        df = df[cols_to_keep].copy()

        for c in df.columns:
            if c not in {
                "symbol",
                "strategy_name",
                "timeframe",
                "source_symbol",
                "source_timeframe",
                "stage",
                "last_seen_at",
                "last_import_name",
            }:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def _prepare_strategy_dataframe(
        self,
        df: pd.DataFrame,
        mapping: Dict[str, str],
        stage: str,
        import_name: str,
        valid_columns: Set[str],
    ) -> pd.DataFrame:
        df = self._apply_column_mapping(df, mapping)
        self._apply_identity_defaults(df)
        self._canonicalize_dataframe_symbols(df)
        self._add_metadata_columns(df, stage, import_name)
        self._add_stage_specific_metrics(df, stage)
        return self._normalize_and_filter_metrics(df, valid_columns)

    def _execute_upsert(self, conn: sqlite3.Connection, df: pd.DataFrame) -> None:
        cols = list(df.columns)
        placeholders = ",".join(["?"] * len(cols))
        col_list = ",".join(cols)

        update_cols = [c for c in cols if c not in {"strategy_name"}]
        update_set = ",".join(
            [f"{c}=excluded.{c}" for c in update_cols] + ["updated_at=datetime('now')"]
        )

        sql = f"""
        INSERT INTO sqx_strategy_edge ({col_list})
        VALUES ({placeholders})
        ON CONFLICT(strategy_name) DO UPDATE SET
          {update_set};
        """
        conn.executemany(sql, df.itertuples(index=False, name=None))

    def merge_sqx_export(
        self,
        df: pd.DataFrame,
        mapping: Dict[str, str],
        stage: str,
        import_name: str,
        purge_missing: bool = False,
    ) -> int:
        """
        Merge an SQX export dataframe into the sqx_strategy_edge table.

        Args:
            df (pd.DataFrame): The dataframe loaded from CSV.
            mapping (dict): Mapping from canonical column names to CSV column names.
            stage (str): The stage label (e.g., 'CORE', 'SPREAD_P99').
            import_name (str): Label for this import.
            purge_missing (bool): Whether to delete strategies missing from this export.

        Returns:
            int: Number of rows merged.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL;")

            cursor = conn.execute("PRAGMA table_info(sqx_strategy_edge)")
            valid_columns = {row[1] for row in cursor.fetchall()}

            df = self._prepare_strategy_dataframe(
                df, mapping, stage, import_name, valid_columns
            )
            self._execute_upsert(conn, df)

            deleted = 0
            if purge_missing:
                symbols_scope = sorted(df["symbol"].unique().astype(str).tolist())
                present_keys = list(
                    zip(
                        df["symbol"].astype(str),
                        df["strategy_name"].astype(str),
                    )
                )
                deleted = self._purge_missing(conn, present_keys, symbols_scope)

            self._log_import(
                conn,
                import_name,
                stage,
                len(df),
                f"purge_missing={purge_missing}, deleted={deleted}",
            )

            conn.commit()
            logger.info(
                f"Merged {len(df)} strategies into sqx_strategy_edge. Stage={stage}, Purged={deleted}"
            )
            return len(df)

        except Exception as e:
            logger.error(f"Error merging SQX export: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _canonicalize_symbol(self, raw: Any) -> str:
        if raw is None:
            return ""
        s = str(raw).strip()
        # common SQX: EURUSD_dukascopy -> EURUSD
        if "_" in s:
            s = s.split("_", 1)[0]
        return s

    def _normalize_win_percent(self, df: pd.DataFrame) -> pd.DataFrame:
        if "win_percent" in df.columns:
            # Check if median is > 1.0 (indicating 0-100 scale), convert to 0-1
            # Using copy to avoid SettingWithCopy warning if slice
            wp = pd.to_numeric(df["win_percent"], errors="coerce")
            if wp.dropna().median() > 1.0:
                df["win_percent"] = wp / 100.0
            else:
                df["win_percent"] = wp
        return df

    def _purge_missing(
        self,
        conn: sqlite3.Connection,
        present_keys: List[Tuple[str, str]],
        symbols_scope: List[str],
    ) -> int:
        if not symbols_scope:
            return 0

        conn.execute("DROP TABLE IF EXISTS _temp_present_keys;")
        conn.execute(
            "CREATE TEMP TABLE _temp_present_keys(symbol TEXT, strategy_name TEXT, PRIMARY KEY(symbol, strategy_name));"
        )
        conn.executemany(
            "INSERT OR IGNORE INTO _temp_present_keys(symbol, strategy_name) VALUES (?,?);",
            present_keys,
        )

        q_marks = ",".join(["?"] * len(symbols_scope))
        sql = f"""
        DELETE FROM sqx_strategy_edge
        WHERE symbol IN ({q_marks})
          AND (symbol, strategy_name) NOT IN (
            SELECT symbol, strategy_name FROM _temp_present_keys
          );
        """
        cur = conn.execute(sql, symbols_scope)
        deleted = cur.rowcount if cur.rowcount is not None else 0

        conn.execute("DROP TABLE IF EXISTS _temp_present_keys;")
        return deleted

    def _log_import(
        self,
        conn: sqlite3.Connection,
        import_name: str,
        stage: str,
        row_count: int,
        notes: str,
    ) -> None:
        conn.execute(
            "INSERT INTO imports(import_name, stage, row_count, notes) VALUES (?,?,?,?);",
            (import_name, stage, row_count, notes),
        )

    def get_sqx_strategies(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve SQX strategies, optionally filtered by symbol."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM sqx_strategy_edge"
            params = []
            if symbol:
                query += " WHERE symbol = ?"
                params.append(symbol)

            query += " ORDER BY final_score DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting SQX strategies: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update_strategy_scores(self, df: pd.DataFrame) -> int:
        """
        Update score columns for strategies in the dataframe.

        Args:
            df (pd.DataFrame): Dataframe containing 'strategy_name' and score columns.

        Returns:
            int: Number of strategies updated.
        """
        if df.empty:
            return 0

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL;")

            # Columns to update
            score_cols = [
                "edge_score",
                "robust_score",
                "stability_score",
                "risk_score",
                "simple_score",
                "fragility_penalty",
                "base_score_0_1",
                "final_score",
                "rank_in_symbol",
                "rejected",
                "a1_edge_score",
                "a2_edge_score",
                "e1_edge_score",
            ]

            # Ensure required columns exist in DF (filter to present ones)
            cols_to_update = [c for c in score_cols if c in df.columns]
            if not cols_to_update:
                return 0

            # Prepare update query
            update_set = ", ".join([f"{c}=?" for c in cols_to_update])
            update_set += ", updated_at=datetime('now')"

            query = f"""
            UPDATE sqx_strategy_edge
            SET {update_set}
            WHERE strategy_name = ?
            """

            # Prepare data list
            # Order: [score_cols..., strategy_name]
            data = []
            for _, row in df.iterrows():
                row_data = [row[c] for c in cols_to_update]
                row_data.append(row["strategy_name"])
                data.append(tuple(row_data))

            cursor = conn.cursor()
            cursor.executemany(query, data)
            conn.commit()

            updated_count = cursor.rowcount
            logger.info(f"Updated scores for {updated_count} strategies.")
            return updated_count

        except Exception as e:
            logger.error(f"Error updating strategy scores: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

