"""Research and audit repositories over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class EvidenceBundleRecord:
    evidence_bundle_id: str
    workflow_id: str | None
    bundle_type: str
    summary: str
    content_ref: str | None
    content_hash: str
    freshness_status: str
    created_at: str


@dataclass(frozen=True)
class TrajectoryLogRecord:
    log_id: str
    workflow_id: str
    correlation_id: str
    agent_name: str
    phase: str
    iteration_no: int
    input_schema: str
    input_hash: str
    output_schema: str
    output_hash: str
    tool_calls_json: str
    observation_payload_ref: str | None
    evaluation_output_ref: str | None
    latency_ms: int
    token_usage_json: str | None
    final_state: str
    signature: str | None
    artifact_ref: str | None
    created_at: str


@dataclass(frozen=True)
class EvaluationReportRecord:
    evaluation_id: str
    workflow_id: str | None
    target_type: str
    target_ref: str
    rubric_name: str
    rubric_scores_json: str
    overall_score: float
    verdict: str
    issues_json: str
    improvement_actions_json: str
    evaluator_identity: str
    evaluation_model_id: str | None
    created_at: str


@dataclass(frozen=True)
class ReplayBundleRecord:
    replay_bundle_id: str
    workflow_id: str
    bundle_hash: str
    object_store_uri: str
    completeness_status: str
    export_profile: str | None
    integrity_manifest_ref: str | None
    created_at: str


@dataclass(frozen=True)
class LegalHoldRecord:
    legal_hold_id: int
    target_type: str
    target_ref_id: str
    hold_reason: str
    placed_by_actor_id: str
    placed_at: str
    released_at: str | None


class ResearchAuditRepository:
    """Minimal persistence wrapper for research evidence and audit metadata."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_evidence_bundle(
        self,
        *,
        evidence_bundle_id: str,
        bundle_type: str,
        summary: str,
        content_hash: str,
        freshness_status: str,
        workflow_id: str | None = None,
        content_ref: str | None = None,
    ) -> EvidenceBundleRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_evidence_bundles (
                    evidence_bundle_id,
                    workflow_id,
                    bundle_type,
                    summary,
                    content_ref,
                    content_hash,
                    freshness_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_bundle_id,
                    workflow_id,
                    bundle_type,
                    summary,
                    content_ref,
                    content_hash,
                    freshness_status,
                ),
            )

        record = self.get_evidence_bundle(evidence_bundle_id)
        if record is None:
            raise LookupError(f"evidence bundle not found after create: {evidence_bundle_id}")
        return record

    def get_evidence_bundle(self, evidence_bundle_id: str) -> EvidenceBundleRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM research_evidence_bundles WHERE evidence_bundle_id = ?",
                (evidence_bundle_id,),
            ).fetchone()
        if row is None:
            return None
        return EvidenceBundleRecord(**dict(row))

    def list_evidence_bundles_for_workflow(self, workflow_id: str) -> list[EvidenceBundleRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM research_evidence_bundles
                WHERE workflow_id = ?
                ORDER BY created_at ASC, evidence_bundle_id ASC
                """,
                (workflow_id,),
            ).fetchall()
        return [EvidenceBundleRecord(**dict(row)) for row in rows]

    def add_trajectory_log(
        self,
        *,
        log_id: str,
        workflow_id: str,
        correlation_id: str,
        agent_name: str,
        phase: str,
        iteration_no: int,
        input_schema: str,
        input_hash: str,
        output_schema: str,
        output_hash: str,
        latency_ms: int,
        final_state: str,
        tool_calls_json: str = "[]",
        observation_payload_ref: str | None = None,
        evaluation_output_ref: str | None = None,
        token_usage_json: str | None = None,
        signature: str | None = None,
        artifact_ref: str | None = None,
    ) -> TrajectoryLogRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_trajectory_logs (
                    log_id,
                    workflow_id,
                    correlation_id,
                    agent_name,
                    phase,
                    iteration_no,
                    input_schema,
                    input_hash,
                    output_schema,
                    output_hash,
                    tool_calls_json,
                    observation_payload_ref,
                    evaluation_output_ref,
                    latency_ms,
                    token_usage_json,
                    final_state,
                    signature,
                    artifact_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    workflow_id,
                    correlation_id,
                    agent_name,
                    phase,
                    iteration_no,
                    input_schema,
                    input_hash,
                    output_schema,
                    output_hash,
                    tool_calls_json,
                    observation_payload_ref,
                    evaluation_output_ref,
                    latency_ms,
                    token_usage_json,
                    final_state,
                    signature,
                    artifact_ref,
                ),
            )

        record = self.get_trajectory_log(log_id)
        if record is None:
            raise LookupError(f"trajectory log not found after create: {log_id}")
        return record

    def get_trajectory_log(self, log_id: str) -> TrajectoryLogRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_trajectory_logs WHERE log_id = ?",
                (log_id,),
            ).fetchone()
        if row is None:
            return None
        return TrajectoryLogRecord(**dict(row))

    def list_trajectory_logs_for_workflow(self, workflow_id: str) -> list[TrajectoryLogRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_trajectory_logs
                WHERE workflow_id = ?
                ORDER BY created_at ASC, log_id ASC
                """,
                (workflow_id,),
            ).fetchall()
        return [TrajectoryLogRecord(**dict(row)) for row in rows]

    def add_evaluation_report(
        self,
        *,
        evaluation_id: str,
        target_type: str,
        target_ref: str,
        rubric_name: str,
        rubric_scores_json: str,
        overall_score: float,
        verdict: str,
        evaluator_identity: str,
        workflow_id: str | None = None,
        issues_json: str = "[]",
        improvement_actions_json: str = "[]",
        evaluation_model_id: str | None = None,
    ) -> EvaluationReportRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_evaluation_reports (
                    evaluation_id,
                    workflow_id,
                    target_type,
                    target_ref,
                    rubric_name,
                    rubric_scores_json,
                    overall_score,
                    verdict,
                    issues_json,
                    improvement_actions_json,
                    evaluator_identity,
                    evaluation_model_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation_id,
                    workflow_id,
                    target_type,
                    target_ref,
                    rubric_name,
                    rubric_scores_json,
                    overall_score,
                    verdict,
                    issues_json,
                    improvement_actions_json,
                    evaluator_identity,
                    evaluation_model_id,
                ),
            )

        record = self.get_evaluation_report(evaluation_id)
        if record is None:
            raise LookupError(f"evaluation report not found after create: {evaluation_id}")
        return record

    def get_evaluation_report(self, evaluation_id: str) -> EvaluationReportRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_evaluation_reports WHERE evaluation_id = ?",
                (evaluation_id,),
            ).fetchone()
        if row is None:
            return None
        return EvaluationReportRecord(**dict(row))

    def list_evaluation_reports_for_workflow(
        self,
        workflow_id: str,
    ) -> list[EvaluationReportRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM core_evaluation_reports
                WHERE workflow_id = ?
                ORDER BY created_at ASC, evaluation_id ASC
                """,
                (workflow_id,),
            ).fetchall()
        return [EvaluationReportRecord(**dict(row)) for row in rows]

    def create_replay_bundle(
        self,
        *,
        replay_bundle_id: str,
        workflow_id: str,
        bundle_hash: str,
        object_store_uri: str,
        completeness_status: str,
        export_profile: str | None = None,
        integrity_manifest_ref: str | None = None,
    ) -> ReplayBundleRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_replay_bundles (
                    replay_bundle_id,
                    workflow_id,
                    bundle_hash,
                    object_store_uri,
                    completeness_status,
                    export_profile,
                    integrity_manifest_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    replay_bundle_id,
                    workflow_id,
                    bundle_hash,
                    object_store_uri,
                    completeness_status,
                    export_profile,
                    integrity_manifest_ref,
                ),
            )

        record = self.get_replay_bundle(replay_bundle_id)
        if record is None:
            raise LookupError(f"replay bundle not found after create: {replay_bundle_id}")
        return record

    def get_replay_bundle(self, replay_bundle_id: str) -> ReplayBundleRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_replay_bundles WHERE replay_bundle_id = ?",
                (replay_bundle_id,),
            ).fetchone()
        if row is None:
            return None
        return ReplayBundleRecord(**dict(row))

    def place_legal_hold(
        self,
        *,
        target_type: str,
        target_ref_id: str,
        hold_reason: str,
        placed_by_actor_id: str,
        released_at: str | None = None,
    ) -> LegalHoldRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_legal_holds (
                    target_type,
                    target_ref_id,
                    hold_reason,
                    placed_by_actor_id,
                    released_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    target_type,
                    target_ref_id,
                    hold_reason,
                    placed_by_actor_id,
                    released_at,
                ),
            )
            record_id = int(cursor.lastrowid)

        record = self.get_legal_hold(record_id)
        if record is None:
            raise LookupError(f"legal hold not found after create: {record_id}")
        return record

    def get_legal_hold(self, legal_hold_id: int) -> LegalHoldRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_legal_holds WHERE legal_hold_id = ?",
                (legal_hold_id,),
            ).fetchone()
        if row is None:
            return None
        return LegalHoldRecord(**dict(row))

    def list_active_legal_holds(self, *, target_type: str, target_ref_id: str) -> list[LegalHoldRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_legal_holds
                WHERE target_type = ? AND target_ref_id = ? AND released_at IS NULL
                ORDER BY placed_at
                """,
                (target_type, target_ref_id),
            ).fetchall()
        return [LegalHoldRecord(**dict(row)) for row in rows]
