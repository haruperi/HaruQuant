"""SQLite persistence helpers for normalized risk artifacts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from haruquant.risk import LimitEvent
from haruquant.risk import MetricRow, RiskSnapshot
from haruquant.risk import RecommendationResult
from haruquant.risk import ScenarioResult
from haruquant.risk import RiskScorecard, ScoreRow
from haruquant.risk import ReplayFrame, WhatIfComparison
from haruquant.utils import logger

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "simulations" / "exports"


class RiskStorageManager:
    """Persist normalized risk artifacts on top of the shared SQLite database."""

    db_path: str

    def create_risk_run(
        self,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        source: str = "manual",
        backtest_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> int:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO risk_runs (backtest_id, label, description, source, context_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    backtest_id,
                    label,
                    description,
                    source,
                    self._dumps(context or {}),
                ),
            )
            run_id = cursor.lastrowid
            if run_id is None:
                raise ValueError("Failed to create risk run.")
            conn.commit()
            return int(run_id)
        except Exception as exc:
            logger.error(f"Error creating risk run: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_snapshot(
        self,
        *,
        run_id: int,
        snapshot: RiskSnapshot,
        backtest_id: Optional[int] = None,
    ) -> int:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO risk_snapshots (
                    run_id, backtest_id, as_of, summary_json, governance_state_json, regime_state_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    backtest_id,
                    self._normalize_value(snapshot.summary.get("as_of")),
                    self._dumps(snapshot.summary),
                    self._dumps(snapshot.governance_state),
                    self._dumps(snapshot.regime_report),
                ),
            )
            snapshot_id = cursor.lastrowid
            if snapshot_id is None:
                raise ValueError("Failed to create risk snapshot.")
            self._insert_metric_rows(cursor, int(snapshot_id), snapshot.metric_rows)
            self._insert_policy_events(cursor, int(snapshot_id), snapshot.policy_events)
            self._insert_scenarios_from_snapshot(cursor, int(snapshot_id), snapshot.metric_rows)
            conn.commit()
            return int(snapshot_id)
        except Exception as exc:
            logger.error(f"Error saving risk snapshot: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_scorecard(self, *, snapshot_id: int, scorecard: RiskScorecard) -> None:
        self.save_risk_score_rows(snapshot_id=snapshot_id, score_rows=scorecard.score_rows)

    def save_risk_score_rows(self, *, snapshot_id: int, score_rows: Iterable[ScoreRow]) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._insert_score_rows(cursor, snapshot_id, score_rows)
            conn.commit()
        except Exception as exc:
            logger.error(f"Error saving risk score rows: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_policy_events(
        self,
        *,
        snapshot_id: int,
        events: Iterable[LimitEvent],
    ) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._insert_policy_events(cursor, snapshot_id, events)
            conn.commit()
        except Exception as exc:
            logger.error(f"Error saving risk policy events: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_recommendations(
        self,
        *,
        snapshot_id: int,
        recommendations: Iterable[RecommendationResult],
    ) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            rows = []
            for item in recommendations:
                rows.append(
                    (
                        snapshot_id,
                        item.action.action_type,
                        item.action.symbol,
                        float(item.action.delta_lots),
                        float(item.action.current_lots),
                        float(item.action.projected_lots),
                        float(item.recommendation_score.usefulness_score),
                        float(item.recommendation_score.score_delta),
                        float(item.recommendation_score.var_delta),
                        float(item.recommendation_score.es_delta),
                        float(item.recommendation_score.worst_scenario_loss_delta),
                        float(item.recommendation_score.margin_used_delta),
                        1 if item.governance_feasible else 0,
                        item.explanation,
                        self._dumps(
                            {
                                "action_context": item.action.context,
                                "score_context": item.recommendation_score.context,
                                "result_context": item.context,
                                "governance_reason": None
                                if item.governance_report is None
                                else item.governance_report.reason,
                            }
                        ),
                    )
                )
            cursor.executemany(
                """
                INSERT INTO risk_recommendations (
                    snapshot_id, action_type, symbol, delta_lots, current_lots, projected_lots,
                    usefulness_score, score_delta, var_delta, es_delta, worst_scenario_loss_delta,
                    margin_used_delta, governance_feasible, explanation, context_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except Exception as exc:
            logger.error(f"Error saving risk recommendations: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_replay_frame(
        self,
        *,
        run_id: int,
        frame: ReplayFrame,
        snapshot_id: Optional[int] = None,
        backtest_id: Optional[int] = None,
        what_if: Optional[WhatIfComparison] = None,
    ) -> int:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO risk_replay_frames (
                    run_id, backtest_id, frame_index, frame_timestamp, capture_timestamp,
                    snapshot_id, score_summary_json, cockpit_payload_json, what_if_summary_json, context_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    backtest_id,
                    int(frame.frame_index),
                    self._normalize_value(frame.timestamp),
                    self._normalize_value(frame.capture_timestamp),
                    snapshot_id,
                    self._dumps(frame.scorecard.summary),
                    self._dumps(frame.cockpit_state),
                    self._dumps(None if what_if is None else what_if.summary),
                    self._dumps(frame.context),
                ),
            )
            replay_frame_id = cursor.lastrowid
            if replay_frame_id is None:
                row = cursor.execute(
                    """
                    SELECT replay_frame_id FROM risk_replay_frames
                    WHERE run_id = ? AND frame_index = ?
                    """,
                    (run_id, int(frame.frame_index)),
                ).fetchone()
                if row is None:
                    raise ValueError("Failed to create risk replay frame.")
                replay_frame_id = row[0]
            conn.commit()
            return int(replay_frame_id)
        except Exception as exc:
            logger.error(f"Error saving risk replay frame: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_risk_scenarios(
        self,
        *,
        snapshot_id: int,
        scenarios: Iterable[ScenarioResult],
    ) -> None:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            rows = [
                (
                    snapshot_id,
                    item.name,
                    float(item.loss),
                    None if item.stressed_var is None else float(item.stressed_var),
                    None if item.stressed_es is None else float(item.stressed_es),
                    self._dumps(item.context),
                )
                for item in scenarios
            ]
            cursor.executemany(
                """
                INSERT INTO risk_scenarios (
                    snapshot_id, scenario_name, loss, stressed_var, stressed_es, context_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except Exception as exc:
            logger.error(f"Error saving risk scenarios: {exc}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_risk_snapshot_bundle(self, snapshot_id: int) -> dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            snapshot_row = conn.execute(
                "SELECT * FROM risk_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if snapshot_row is None:
                raise ValueError(f"Risk snapshot {snapshot_id} not found.")
            return {
                "snapshot": self._decode_row(snapshot_row),
                "metric_rows": self._fetch_rows(conn, "risk_metric_rows", "snapshot_id", snapshot_id),
                "score_rows": self._fetch_rows(conn, "risk_score_rows", "snapshot_id", snapshot_id),
                "policy_events": self._fetch_rows(conn, "risk_policy_events", "snapshot_id", snapshot_id),
                "recommendations": self._fetch_rows(conn, "risk_recommendations", "snapshot_id", snapshot_id),
                "scenarios": self._fetch_rows(conn, "risk_scenarios", "snapshot_id", snapshot_id),
            }
        finally:
            conn.close()

    def get_risk_run(self, run_id: int) -> dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM risk_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Risk run {run_id} not found.")
            return self._decode_row(row)
        finally:
            conn.close()

    def get_risk_replay_frames(self, run_id: int) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM risk_replay_frames WHERE run_id = ? ORDER BY frame_index ASC",
                (run_id,),
            ).fetchall()
            return [self._decode_row(row) for row in rows]
        finally:
            conn.close()

    def export_risk_snapshot_reports(self, snapshot_id: int) -> dict[str, Any]:
        """Export stored risk snapshot reports as JSON and Markdown."""
        from haruquant.risk import build_risk_snapshot_report, build_scenario_report, render_risk_report_markdown, render_scenario_report_markdown, save_json_report, save_markdown_report

        bundle = self.get_risk_snapshot_bundle(snapshot_id)
        run = self.get_risk_run(int(bundle["snapshot"]["run_id"]))
        risk_report = build_risk_snapshot_report(bundle, run=run)
        scenario_report = build_scenario_report(bundle, run=run)

        export_dir = EXPORT_DIR
        export_dir.mkdir(parents=True, exist_ok=True)

        risk_json = export_dir / f"risk_snapshot_{snapshot_id}.json"
        risk_md = export_dir / f"risk_snapshot_{snapshot_id}.md"
        scenario_json = export_dir / f"risk_scenarios_{snapshot_id}.json"
        scenario_md = export_dir / f"risk_scenarios_{snapshot_id}.md"

        save_json_report(risk_report, risk_json)
        save_markdown_report(render_risk_report_markdown(risk_report), risk_md)
        save_json_report(scenario_report, scenario_json)
        save_markdown_report(render_scenario_report_markdown(scenario_report), scenario_md)

        return {
            "risk_report": risk_report,
            "scenario_report": scenario_report,
            "artifacts": [
                {"artifact_type": "json_report", "artifact_ref": str(risk_json)},
                {"artifact_type": "markdown_report", "artifact_ref": str(risk_md)},
                {"artifact_type": "json_scenario_report", "artifact_ref": str(scenario_json)},
                {"artifact_type": "markdown_scenario_report", "artifact_ref": str(scenario_md)},
            ],
        }

    def export_risk_replay_report(self, run_id: int) -> dict[str, Any]:
        """Export a compact replay report as JSON and Markdown."""
        from haruquant.risk import build_replay_report, render_replay_report_markdown, save_json_report, save_markdown_report

        run = self.get_risk_run(run_id)
        frames = self.get_risk_replay_frames(run_id)
        replay_report = build_replay_report(frames, run=run)

        export_dir = EXPORT_DIR
        export_dir.mkdir(parents=True, exist_ok=True)
        replay_json = export_dir / f"risk_replay_{run_id}.json"
        replay_md = export_dir / f"risk_replay_{run_id}.md"

        save_json_report(replay_report, replay_json)
        save_markdown_report(render_replay_report_markdown(replay_report), replay_md)

        return {
            "replay_report": replay_report,
            "artifacts": [
                {"artifact_type": "json_replay_report", "artifact_ref": str(replay_json)},
                {"artifact_type": "markdown_replay_report", "artifact_ref": str(replay_md)},
            ],
        }

    def _insert_metric_rows(
        self,
        cursor: sqlite3.Cursor,
        snapshot_id: int,
        metric_rows: Iterable[MetricRow],
    ) -> None:
        rows = [
            (
                snapshot_id,
                item.family,
                item.metric_key,
                item.scope,
                item.scope_key,
                item.numeric_value,
                item.text_value,
                item.unit,
                self._dumps(item.context),
            )
            for item in metric_rows
        ]
        cursor.executemany(
            """
            INSERT INTO risk_metric_rows (
                snapshot_id, family, metric_key, scope, scope_key,
                numeric_value, text_value, unit, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_score_rows(
        self,
        cursor: sqlite3.Cursor,
        snapshot_id: int,
        score_rows: Iterable[ScoreRow],
    ) -> None:
        rows = [
            (
                snapshot_id,
                item.family,
                item.score_key,
                float(item.score_value),
                float(item.confidence),
                item.confidence_label,
                item.explanation,
                self._dumps(item.context),
            )
            for item in score_rows
        ]
        cursor.executemany(
            """
            INSERT INTO risk_score_rows (
                snapshot_id, family, score_key, score_value, confidence,
                confidence_label, explanation, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_policy_events(
        self,
        cursor: sqlite3.Cursor,
        snapshot_id: int,
        events: Iterable[LimitEvent],
    ) -> None:
        rows = [
            (
                snapshot_id,
                item.event_type,
                item.rule_key,
                item.severity,
                item.message,
                item.observed_value,
                item.threshold_value,
                item.unit,
                item.scope,
                item.scope_key,
                self._dumps(item.context),
            )
            for item in events
        ]
        if not rows:
            return
        cursor.executemany(
            """
            INSERT INTO risk_policy_events (
                snapshot_id, event_type, rule_key, severity, message,
                observed_value, threshold_value, unit, scope, scope_key, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_scenarios_from_snapshot(
        self,
        cursor: sqlite3.Cursor,
        snapshot_id: int,
        metric_rows: Iterable[MetricRow],
    ) -> None:
        scenario_rows = []
        for item in metric_rows:
            if item.family != "stress_risk" or item.scope != "scenario":
                continue
            scenario_name = item.scope_key or item.context.get("scenario_name")
            if not scenario_name or item.metric_key != "scenario_loss":
                continue
            scenario_rows.append(
                (
                    snapshot_id,
                    scenario_name,
                    None if item.numeric_value is None else float(item.numeric_value),
                    self._metric_context_float(item.context.get("stressed_var")),
                    self._metric_context_float(item.context.get("stressed_es")),
                    self._dumps(item.context),
                )
            )
        if not scenario_rows:
            return
        cursor.executemany(
            """
            INSERT INTO risk_scenarios (
                snapshot_id, scenario_name, loss, stressed_var, stressed_es, context_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            scenario_rows,
        )

    def _fetch_rows(
        self,
        conn: sqlite3.Connection,
        table: str,
        key: str,
        value: Any,
    ) -> list[dict[str, Any]]:
        rows = conn.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchall()
        return [self._decode_row(row) for row in rows]

    def _decode_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for key, value in list(data.items()):
            if key.endswith("_json") and value is not None:
                data[key] = json.loads(value)
        return data

    def _dumps(self, value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(self._normalize_value(value), sort_keys=True)

    def _normalize_value(self, value: Any) -> Any:
        if value is None:
            return None
        if is_dataclass(value):
            return self._normalize_value(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._normalize_value(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, "isoformat") and callable(value.isoformat):
            try:
                return value.isoformat()
            except TypeError:
                pass
        if hasattr(value, "item") and callable(value.item):
            try:
                return value.item()
            except (ValueError, TypeError):
                pass
        return value

    def _metric_context_float(self, value: Any) -> float | None:
        if value is None:
            return None
        return float(value)
