"""Edge Discovery database management module."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from haruquant.research import CoreMetricProfile
from haruquant.research import MarketStructureProfile
from haruquant.research import build_edge_profile_snapshot
from haruquant.research import build_dashboard_summary, comparison_report_markdown, save_json_report, save_markdown_report, snapshot_report_json, snapshot_report_markdown
from haruquant.utils import logger

from .base import DatabaseBase

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "simulations" / "exports"


class EdgeDiscoveryManager(DatabaseBase):
    """Edge Discovery database operations."""

    def save_profile_snapshot(
        self,
        payload: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Optional[int]:
        """Persist one versioned Edge Lab profile snapshot."""
        snapshot = build_edge_profile_snapshot(payload)
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO edge_profile_snapshots (
                    user_id, symbol, timeframe, data_source, range_by,
                    model_version, baseline_id, core_metric_run_id, market_structure_run_id,
                    dataset_meta, core_metric_summary, seasonality_summary,
                    market_structure_summary, unsupervised_summary, scorecard_summary,
                    automation_metadata, artifact_refs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    snapshot.get("symbol"),
                    snapshot.get("timeframe"),
                    snapshot.get("data_source"),
                    snapshot.get("range_by"),
                    snapshot.get("model_version"),
                    snapshot.get("baseline_id"),
                    snapshot.get("core_metric_run_id"),
                    snapshot.get("market_structure_run_id"),
                    json.dumps(snapshot.get("dataset_meta") or {}),
                    json.dumps(snapshot.get("core_metric_summary") or {}),
                    json.dumps(snapshot.get("seasonality_summary") or {}),
                    json.dumps(snapshot.get("market_structure_summary") or {}),
                    json.dumps(snapshot.get("unsupervised_summary") or {}),
                    json.dumps(snapshot.get("scorecard_summary") or {}),
                    json.dumps(snapshot.get("automation_metadata") or {}),
                    json.dumps(snapshot.get("artifact_refs") or []),
                ),
            )
            snapshot_id = int(cursor.lastrowid)

            for row in snapshot.get("metrics") or []:
                cursor.execute(
                    """
                    INSERT INTO edge_profile_snapshot_metrics (
                        snapshot_id, section, metric_key, value_num, value_text, value_type, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        row.get("section"),
                        row.get("metric_key"),
                        row.get("value_num"),
                        row.get("value_text"),
                        row.get("value_type"),
                        json.dumps(row.get("context") or {}),
                    ),
                )

            for row in snapshot.get("scores") or []:
                cursor.execute(
                    """
                    INSERT INTO edge_profile_snapshot_scores (
                        snapshot_id, score_key, label, score, confidence, explanation, inputs
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        row.get("score_key"),
                        row.get("label"),
                        row.get("score"),
                        row.get("confidence"),
                        row.get("explanation"),
                        json.dumps(row.get("inputs") or {}),
                    ),
                )

            for row in snapshot.get("strategy_fit") or []:
                cursor.execute(
                    """
                    INSERT INTO edge_profile_snapshot_strategy_fit (
                        snapshot_id, rank_order, archetype, fit_score, rationale,
                        warnings, anti_fit_conditions, inputs
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        row.get("rank_order"),
                        row.get("archetype"),
                        row.get("fit_score"),
                        row.get("rationale"),
                        json.dumps(row.get("warnings") or []),
                        json.dumps(row.get("anti_fit_conditions") or []),
                        json.dumps(row.get("inputs") or {}),
                    ),
                )

            for row in snapshot.get("artifact_refs") or []:
                cursor.execute(
                    """
                    INSERT INTO edge_profile_snapshot_artifacts (
                        snapshot_id, artifact_type, artifact_ref, metadata
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        row.get("artifact_type"),
                        row.get("artifact_ref"),
                        json.dumps(row.get("metadata") or {}),
                    ),
                )

            conn.commit()
            return snapshot_id
        except Exception as e:
            logger.error(f"Error saving profile snapshot: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def get_profile_snapshots(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List stored Edge Lab profile snapshots."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM edge_profile_snapshots WHERE 1=1"
            params: List[Any] = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                for field in (
                    "dataset_meta",
                    "core_metric_summary",
                    "seasonality_summary",
                    "market_structure_summary",
                    "unsupervised_summary",
                    "scorecard_summary",
                    "automation_metadata",
                    "artifact_refs",
                ):
                    if item.get(field):
                        item[field] = json.loads(item[field])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting profile snapshots: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_profile_snapshot(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Get one profile snapshot with metrics, scores, strategy fit, and artifacts."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_profile_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            for field in (
                "dataset_meta",
                "core_metric_summary",
                "seasonality_summary",
                "market_structure_summary",
                "unsupervised_summary",
                "scorecard_summary",
                "automation_metadata",
                "artifact_refs",
            ):
                if item.get(field):
                    item[field] = json.loads(item[field])
            item["metrics"] = self.get_profile_snapshot_metrics(snapshot_id)
            item["scores"] = self.get_profile_snapshot_scores(snapshot_id)
            item["strategy_fit"] = self.get_profile_snapshot_strategy_fit(snapshot_id)
            item["artifacts"] = self.get_profile_snapshot_artifacts(snapshot_id)
            return item
        except Exception as e:
            logger.error(f"Error getting profile snapshot {snapshot_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def find_matching_profile_snapshot(
        self,
        *,
        symbol: str,
        timeframe: str,
        data_source: str,
        range_by: str,
        start: Optional[str],
        end: Optional[str],
        row_count: Optional[int],
        dataset_fingerprint: Optional[str] = None,
        config_fingerprint: Optional[str] = None,
        model_version: Optional[str] = None,
        baseline_id: Optional[str] = None,
        limit: int = 25,
    ) -> Optional[Dict[str, Any]]:
        """Find the latest snapshot matching the same request + dataset window."""
        rows = self.get_profile_snapshots(symbol=symbol, timeframe=timeframe, limit=limit, offset=0)
        for row in rows:
            dataset_meta = dict(row.get("dataset_meta") or {})
            if str(row.get("data_source") or "").lower() != data_source.lower():
                continue
            if str(row.get("range_by") or "").lower() != range_by.lower():
                continue
            if start and str(dataset_meta.get("start") or "") != start:
                continue
            if end and str(dataset_meta.get("end") or "") != end:
                continue
            if row_count is not None and int(dataset_meta.get("n_rows") or -1) != int(row_count):
                continue
            if dataset_fingerprint and str(dataset_meta.get("dataset_fingerprint") or "") != dataset_fingerprint:
                continue
            if config_fingerprint and str(dataset_meta.get("config_fingerprint") or "") != config_fingerprint:
                continue
            if model_version and str(row.get("model_version") or "") != model_version:
                continue
            if baseline_id and str(row.get("baseline_id") or "") != baseline_id:
                continue
            return self.get_profile_snapshot(int(row["snapshot_id"]))
        return None

    def get_profile_snapshot_metrics(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """Get normalized metrics for one snapshot."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM edge_profile_snapshot_metrics
                WHERE snapshot_id = ?
                ORDER BY section ASC, metric_key ASC
                """,
                (snapshot_id,),
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("context"):
                    item["context"] = json.loads(item["context"])
                item["value"] = (
                    item.get("value_num")
                    if item.get("value_type") == "number"
                    else item.get("value_text")
                )
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting snapshot metrics for {snapshot_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_profile_snapshot_scores(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """Get scorecard rows for one snapshot."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM edge_profile_snapshot_scores
                WHERE snapshot_id = ?
                ORDER BY id ASC
                """,
                (snapshot_id,),
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("inputs"):
                    item["inputs"] = json.loads(item["inputs"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting snapshot scores for {snapshot_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_profile_snapshot_strategy_fit(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """Get ranked strategy-fit rows for one snapshot."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM edge_profile_snapshot_strategy_fit
                WHERE snapshot_id = ?
                ORDER BY rank_order ASC
                """,
                (snapshot_id,),
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("warnings"):
                    item["warnings"] = json.loads(item["warnings"])
                if item.get("anti_fit_conditions"):
                    item["anti_fit_conditions"] = json.loads(item["anti_fit_conditions"])
                if item.get("inputs"):
                    item["inputs"] = json.loads(item["inputs"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting snapshot strategy fit for {snapshot_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_profile_snapshot_artifacts(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """Get artifact references for one snapshot."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM edge_profile_snapshot_artifacts
                WHERE snapshot_id = ?
                ORDER BY id ASC
                """,
                (snapshot_id,),
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("metadata"):
                    item["metadata"] = json.loads(item["metadata"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting snapshot artifacts for {snapshot_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def compare_profile_snapshots(
        self,
        left_snapshot_id: int,
        right_snapshot_id: int,
    ) -> Dict[str, Any]:
        """Compare two snapshots by scalar summaries, metrics, scores, and primary strategy fit."""
        left = self.get_profile_snapshot(left_snapshot_id)
        right = self.get_profile_snapshot(right_snapshot_id)
        if left is None or right is None:
            return {}

        left_metrics = {
            f"{row['section']}.{row['metric_key']}": row.get("value")
            for row in left.get("metrics", [])
        }
        right_metrics = {
            f"{row['section']}.{row['metric_key']}": row.get("value")
            for row in right.get("metrics", [])
        }
        metric_diffs = []
        for key in sorted(set(left_metrics) & set(right_metrics)):
            if left_metrics[key] == right_metrics[key]:
                continue
            metric_diffs.append(
                {
                    "key": key,
                    "left_value": left_metrics[key],
                    "right_value": right_metrics[key],
                }
            )

        left_scores = {row["score_key"]: row for row in left.get("scores", [])}
        right_scores = {row["score_key"]: row for row in right.get("scores", [])}
        score_diffs = []
        for key in sorted(set(left_scores) & set(right_scores)):
            if left_scores[key].get("score") == right_scores[key].get("score"):
                continue
            score_diffs.append(
                {
                    "score_key": key,
                    "label": left_scores[key].get("label") or right_scores[key].get("label"),
                    "left_score": left_scores[key].get("score"),
                    "right_score": right_scores[key].get("score"),
                }
            )

        return {
            "left_snapshot": {
                "snapshot_id": left.get("snapshot_id"),
                "symbol": left.get("symbol"),
                "timeframe": left.get("timeframe"),
                "created_at": left.get("created_at"),
                "scorecard_summary": left.get("scorecard_summary"),
                "primary_strategy_fit": (left.get("strategy_fit") or [{}])[0] if left.get("strategy_fit") else None,
            },
            "right_snapshot": {
                "snapshot_id": right.get("snapshot_id"),
                "symbol": right.get("symbol"),
                "timeframe": right.get("timeframe"),
                "created_at": right.get("created_at"),
                "scorecard_summary": right.get("scorecard_summary"),
                "primary_strategy_fit": (right.get("strategy_fit") or [{}])[0] if right.get("strategy_fit") else None,
            },
            "metric_diffs": metric_diffs,
            "score_diffs": score_diffs,
        }

    def export_profile_snapshot_metrics_parquet(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Export one snapshot's wide metrics to Parquet and persist the artifact reference."""
        snapshot = self.get_profile_snapshot(snapshot_id)
        if snapshot is None:
            return None

        metrics = snapshot.get("metrics") or []
        if not metrics:
            return None

        wide: Dict[str, Any] = {
            "snapshot_id": snapshot_id,
            "symbol": snapshot.get("symbol"),
            "timeframe": snapshot.get("timeframe"),
            "created_at": snapshot.get("created_at"),
        }
        for row in metrics:
            wide[f"{row['section']}.{row['metric_key']}"] = row.get("value")

        export_dir = EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)
        file_path = export_dir / f"edge_profile_snapshot_{snapshot_id}.parquet"
        pd.DataFrame([wide]).to_parquet(file_path, index=False)

        artifact = {
            "artifact_type": "parquet_wide_metrics",
            "artifact_ref": str(file_path),
            "metadata": {"snapshot_id": snapshot_id},
        }
        self._insert_snapshot_artifacts(snapshot_id, [artifact])

        return artifact

    def export_profile_snapshot_reports(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Export Markdown and JSON reports for one snapshot and persist artifact refs."""
        snapshot = self.get_profile_snapshot(snapshot_id)
        if snapshot is None:
            return None

        export_dir = EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)

        markdown_path = export_dir / f"edge_profile_snapshot_{snapshot_id}.md"
        json_path = export_dir / f"edge_profile_snapshot_{snapshot_id}.json"

        markdown_content = snapshot_report_markdown(snapshot)
        json_content = snapshot_report_json(snapshot)
        save_markdown_report(markdown_content, markdown_path)
        save_json_report(json_content, json_path)

        artifacts = [
            {
                "artifact_type": "markdown_report",
                "artifact_ref": str(markdown_path),
                "metadata": {"snapshot_id": snapshot_id},
            },
            {
                "artifact_type": "json_report",
                "artifact_ref": str(json_path),
                "metadata": {"snapshot_id": snapshot_id},
            },
        ]
        self._insert_snapshot_artifacts(snapshot_id, artifacts)
        return {
            "summary": build_dashboard_summary(snapshot),
            "artifacts": artifacts,
        }

    def export_profile_snapshot_comparison_markdown(
        self,
        left_snapshot_id: int,
        right_snapshot_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Export a Markdown comparison report for two snapshots."""
        comparison = self.compare_profile_snapshots(left_snapshot_id, right_snapshot_id)
        if not comparison:
            return None

        export_dir = EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)
        path = export_dir / f"edge_profile_comparison_{left_snapshot_id}_{right_snapshot_id}.md"
        save_markdown_report(comparison_report_markdown(comparison), path)

        artifact = {
            "artifact_type": "markdown_comparison_report",
            "artifact_ref": str(path),
            "metadata": {
                "left_snapshot_id": left_snapshot_id,
                "right_snapshot_id": right_snapshot_id,
            },
        }
        self._insert_snapshot_artifacts(left_snapshot_id, [artifact])
        return {
            "comparison": comparison,
            "artifact": artifact,
        }

    def _insert_snapshot_artifacts(
        self,
        snapshot_id: int,
        artifacts: List[Dict[str, Any]],
    ) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for artifact in artifacts:
                cursor.execute(
                    """
                    INSERT INTO edge_profile_snapshot_artifacts (
                        snapshot_id, artifact_type, artifact_ref, metadata
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        artifact.get("artifact_type"),
                        artifact.get("artifact_ref"),
                        json.dumps(artifact.get("metadata") or {}),
                    ),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting snapshot artifacts for {snapshot_id}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def save_market_structure_profile(
        self,
        profile: MarketStructureProfile,
        user_id: Optional[int] = None,
    ) -> Optional[int]:
        """Persist a Market Structure profile and its normalized values."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO edge_market_structure_runs (
                    user_id, symbol, timeframe, data_source, range_by,
                    start_date, end_date, number_of_bars, bar_count,
                    is_valid, warning_count, fatal_error_count, report, summary, calibration_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    profile.symbol,
                    profile.timeframe,
                    profile.data_source,
                    profile.range_by,
                    profile.start_date,
                    profile.end_date,
                    profile.number_of_bars,
                    profile.bar_count,
                    1 if profile.report.is_valid else 0,
                    len(profile.report.warnings),
                    len(profile.report.fatal_errors),
                    json.dumps(profile.to_dict().get("report", {})),
                    json.dumps(profile.summary or {}),
                    json.dumps((profile.summary or {}).get("calibration_metadata", {})),
                ),
            )
            run_id = cursor.lastrowid

            for value in profile.values:
                value_num = None
                value_text = None
                if value.value_type == "number":
                    value_num = float(value.value) if value.value is not None else None
                else:
                    value_text = str(value.value) if value.value is not None else None
                cursor.execute(
                    """
                    INSERT INTO edge_market_structure_values (
                        run_id, family, metric_key, value_num, value_text, value_type, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        value.family,
                        value.key,
                        value_num,
                        value_text,
                        value.value_type,
                        json.dumps(value.context) if value.context else None,
                    ),
                )

            for row in profile.score_rows:
                cursor.execute(
                    """
                    INSERT INTO edge_market_structure_scores (
                        run_id, score_group, score_key, label, raw_value, score, weight, contribution, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        row.group,
                        row.key,
                        row.label,
                        json.dumps(row.raw_value),
                        row.score,
                        row.weight,
                        row.contribution,
                        row.notes,
                    ),
                )

            for point in profile.swing_points:
                cursor.execute(
                    """
                    INSERT INTO edge_market_structure_swings (
                        run_id, timestamp, price, swing_type, label, swing_index, atr_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        point.timestamp,
                        point.price,
                        point.swing_type,
                        point.label,
                        point.index,
                        point.atr_value,
                    ),
                )

            for leg in profile.trend_legs:
                cursor.execute(
                    """
                    INSERT INTO edge_market_structure_legs (
                        run_id, start_time, end_time, direction, amplitude_pips,
                        duration_bars, efficiency_ratio, directional_consistency,
                        pullback_depth, pullback_duration, continuation_after_pullback
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        leg.start_time,
                        leg.end_time,
                        leg.direction,
                        leg.amplitude_pips,
                        leg.duration_bars,
                        leg.efficiency_ratio,
                        leg.directional_consistency,
                        leg.pullback_depth,
                        leg.pullback_duration,
                        None if leg.continuation_after_pullback is None else (1 if leg.continuation_after_pullback else 0),
                    ),
                )

            conn.commit()
            return int(run_id)
        except Exception as e:
            logger.error(f"Error saving market structure profile: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def save_core_metric_profile(
        self,
        profile: CoreMetricProfile,
        user_id: Optional[int] = None,
    ) -> Optional[int]:
        """Persist a Core Metric profile and its normalized values."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO edge_core_metric_runs (
                    user_id, symbol, timeframe, data_source, range_by,
                    start_date, end_date, number_of_bars, bar_count,
                    is_valid, warning_count, fatal_error_count, report, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    profile.symbol,
                    profile.timeframe,
                    profile.data_source,
                    profile.range_by,
                    profile.start_date,
                    profile.end_date,
                    profile.number_of_bars,
                    profile.bar_count,
                    1 if profile.report.is_valid else 0,
                    len(profile.report.warnings),
                    len(profile.report.fatal_errors),
                    json.dumps(profile.to_dict().get("report", {})),
                    json.dumps(profile.summary or {}),
                ),
            )
            run_id = cursor.lastrowid

            for value in profile.values:
                value_num = None
                value_text = None
                if value.value_type == "number":
                    value_num = float(value.value) if value.value is not None else None
                else:
                    value_text = str(value.value) if value.value is not None else None

                cursor.execute(
                    """
                    INSERT INTO edge_core_metric_values (
                        run_id, family, metric_key, value_num, value_text, value_type, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        value.family,
                        value.key,
                        value_num,
                        value_text,
                        value.value_type,
                        json.dumps(value.context) if value.context else None,
                    ),
                )

            conn.commit()
            return int(run_id)
        except Exception as e:
            logger.error(f"Error saving core metric profile: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def get_market_structure_runs(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List stored Market Structure runs."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM edge_market_structure_runs WHERE 1=1"
            params: List[Any] = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("report"):
                    item["report"] = json.loads(item["report"])
                if item.get("summary"):
                    item["summary"] = json.loads(item["summary"])
                if item.get("calibration_metadata"):
                    item["calibration_metadata"] = json.loads(item["calibration_metadata"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting market structure runs: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_market_structure_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get one Market Structure run with normalized detail tables."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_market_structure_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            if item.get("report"):
                item["report"] = json.loads(item["report"])
            if item.get("summary"):
                item["summary"] = json.loads(item["summary"])
            if item.get("calibration_metadata"):
                item["calibration_metadata"] = json.loads(item["calibration_metadata"])
            item["values"] = self.get_market_structure_values(run_id)
            item["score_rows"] = self.get_market_structure_scores(run_id)
            item["swing_points"] = self.get_market_structure_swings(run_id)
            item["trend_legs"] = self.get_market_structure_legs(run_id)
            return item
        except Exception as e:
            logger.error(f"Error getting market structure run {run_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_market_structure_values(self, run_id: int) -> List[Dict[str, Any]]:
        """Get normalized Market Structure values for a run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_market_structure_values WHERE run_id = ? ORDER BY family ASC, metric_key ASC",
                (run_id,),
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("context"):
                    item["context"] = json.loads(item["context"])
                item["value"] = item.get("value_num") if item.get("value_type") == "number" else item.get("value_text")
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error getting market structure values for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_market_structure_scores(self, run_id: int) -> List[Dict[str, Any]]:
        """Get score rows for a Market Structure run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_market_structure_scores WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("raw_value"):
                    item["raw_value"] = json.loads(item["raw_value"])
                group = item.get("score_group")
                if not group:
                    score_key = str(item.get("score_key") or "")
                    if score_key in {
                        "swing_bias_balance",
                        "chain_strength",
                        "follow_through_probability",
                        "pullback_quality",
                        "directional_efficiency",
                    }:
                        group = "direction"
                    else:
                        group = "confidence"
                item["group"] = group
                item["key"] = item.get("score_key")
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting market structure scores for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_market_structure_swings(self, run_id: int) -> List[Dict[str, Any]]:
        """Get audited swing points for a Market Structure run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_market_structure_swings WHERE run_id = ? ORDER BY swing_index ASC",
                (run_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting market structure swings for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_market_structure_legs(self, run_id: int) -> List[Dict[str, Any]]:
        """Get market structure leg analytics for a run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_market_structure_legs WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting market structure legs for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def delete_market_structure_run(self, run_id: int) -> bool:
        """Delete a Market Structure run and all associated data."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                "DELETE FROM edge_market_structure_runs WHERE run_id = ?",
                (run_id,),
            )
            if cursor.rowcount == 0:
                logger.warning(f"Market structure run {run_id} not found for deletion")
                return False
            conn.commit()
            logger.info(f"Deleted market structure run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting market structure run {run_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def save_market_structure_evaluation(self, row: Dict[str, Any]) -> bool:
        """Upsert one persisted forward-evaluation row for a Market Structure run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO edge_market_structure_evaluations (
                    run_id, symbol, timeframe, run_created_at, predicted_verdict, realized_verdict,
                    matched, decision_confidence_score, confidence_bucket, forward_end,
                    net_move_pips, path_pips, efficiency, reversion_ratio, flip_rate,
                    avg_range_pips, max_excursion_pips, continuation_label, range_reentry_label,
                    breakout_failure_label, chop_label, calibration_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    symbol=excluded.symbol,
                    timeframe=excluded.timeframe,
                    run_created_at=excluded.run_created_at,
                    predicted_verdict=excluded.predicted_verdict,
                    realized_verdict=excluded.realized_verdict,
                    matched=excluded.matched,
                    decision_confidence_score=excluded.decision_confidence_score,
                    confidence_bucket=excluded.confidence_bucket,
                    forward_end=excluded.forward_end,
                    net_move_pips=excluded.net_move_pips,
                    path_pips=excluded.path_pips,
                    efficiency=excluded.efficiency,
                    reversion_ratio=excluded.reversion_ratio,
                    flip_rate=excluded.flip_rate,
                    avg_range_pips=excluded.avg_range_pips,
                    max_excursion_pips=excluded.max_excursion_pips,
                    continuation_label=excluded.continuation_label,
                    range_reentry_label=excluded.range_reentry_label,
                    breakout_failure_label=excluded.breakout_failure_label,
                    chop_label=excluded.chop_label,
                    calibration_metadata=excluded.calibration_metadata
                """,
                (
                    row.get("run_id"),
                    row.get("symbol"),
                    row.get("timeframe"),
                    row.get("run_created_at"),
                    row.get("predicted_verdict"),
                    row.get("realized_verdict"),
                    1 if row.get("matched") else 0,
                    row.get("decision_confidence_score"),
                    row.get("confidence_bucket"),
                    row.get("forward_end"),
                    row.get("net_move_pips"),
                    row.get("path_pips"),
                    row.get("efficiency"),
                    row.get("reversion_ratio"),
                    row.get("flip_rate"),
                    row.get("avg_range_pips"),
                    row.get("max_excursion_pips"),
                    row.get("continuation_label"),
                    row.get("range_reentry_label"),
                    row.get("breakout_failure_label"),
                    row.get("chop_label"),
                    json.dumps(row.get("calibration_metadata") or {}),
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving market structure evaluation for run {row.get('run_id')}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_market_structure_evaluations(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List persisted Market Structure forward evaluations."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM edge_market_structure_evaluations WHERE 1=1"
            params: List[Any] = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            query += " ORDER BY run_created_at DESC, id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("calibration_metadata"):
                    item["calibration_metadata"] = json.loads(item["calibration_metadata"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting market structure evaluations: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_core_metric_runs(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List stored Core Metric profile runs."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM edge_core_metric_runs WHERE 1=1"
            params: List[Any] = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("report"):
                    item["report"] = json.loads(item["report"])
                if item.get("summary"):
                    item["summary"] = json.loads(item["summary"])
                rows.append(item)
            return rows
        except Exception as e:
            logger.error(f"Error getting core metric runs: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_core_metric_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get one Core Metric run with summary fields."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM edge_core_metric_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            if item.get("report"):
                item["report"] = json.loads(item["report"])
            if item.get("summary"):
                item["summary"] = json.loads(item["summary"])
            item["values"] = self.get_core_metric_values(run_id)
            return item
        except Exception as e:
            logger.error(f"Error getting core metric run {run_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def delete_core_metric_run(self, run_id: int) -> bool:
        """Delete a Core Metric run and all associated data."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                "DELETE FROM edge_core_metric_runs WHERE run_id = ?",
                (run_id,),
            )
            if cursor.rowcount == 0:
                logger.warning(f"Core metric run {run_id} not found for deletion")
                return False
            conn.commit()
            logger.info(f"Deleted core metric run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting core metric run {run_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_core_metric_values(
        self,
        run_id: int,
        family: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get normalized Core Metric values for a run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM edge_core_metric_values WHERE run_id = ?"
            params: List[Any] = [run_id]
            if family:
                query += " AND family = ?"
                params.append(family)
            query += " ORDER BY family ASC, metric_key ASC"
            cursor.execute(query, params)
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("context"):
                    item["context"] = json.loads(item["context"])
                item["value"] = (
                    item.get("value_num")
                    if item.get("value_type") == "number"
                    else item.get("value_text")
                )
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error getting core metric values for run {run_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

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

