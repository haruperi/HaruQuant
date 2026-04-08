"""Risk repositories over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class RiskAssessmentRequestRecord:
    risk_request_id: str
    workflow_id: str
    proposal_id: str
    action_type: str
    account_snapshot_ref: str | None
    portfolio_snapshot_ref: str | None
    market_snapshot_ref: str | None
    requested_freshness_json: str
    strategy_lifecycle_state: str
    active_policy_bundle_json: str
    compliance_profile_id: str | None
    current_kill_switch_state: str
    created_at: str


@dataclass(frozen=True)
class RiskDecisionRecord:
    risk_decision_id: str
    risk_request_id: str
    proposal_id: str
    workflow_id: str
    decision: str
    rationale_text: str
    risk_metrics_snapshot_json: str
    freshness_expiry: str
    policy_version_id: str
    formula_version: str
    provenance_bundle_id: str | None
    approval_token: str | None
    freshness_status: str
    created_at: str


@dataclass(frozen=True)
class RiskConstraintRecord:
    constraint_id: int
    risk_decision_id: str
    constraint_type: str
    constraint_value_json: str
    created_at: str


class RiskRepository:
    """Minimal persistence wrapper for risk request/decision state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_request(
        self,
        *,
        risk_request_id: str,
        workflow_id: str,
        proposal_id: str,
        action_type: str,
        strategy_lifecycle_state: str,
        active_policy_bundle_json: str,
        current_kill_switch_state: str,
        account_snapshot_ref: str | None = None,
        portfolio_snapshot_ref: str | None = None,
        market_snapshot_ref: str | None = None,
        requested_freshness_json: str = "{}",
        compliance_profile_id: str | None = None,
    ) -> RiskAssessmentRequestRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO risk_risk_assessment_requests (
                    risk_request_id,
                    workflow_id,
                    proposal_id,
                    action_type,
                    account_snapshot_ref,
                    portfolio_snapshot_ref,
                    market_snapshot_ref,
                    requested_freshness_json,
                    strategy_lifecycle_state,
                    active_policy_bundle_json,
                    compliance_profile_id,
                    current_kill_switch_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    risk_request_id,
                    workflow_id,
                    proposal_id,
                    action_type,
                    account_snapshot_ref,
                    portfolio_snapshot_ref,
                    market_snapshot_ref,
                    requested_freshness_json,
                    strategy_lifecycle_state,
                    active_policy_bundle_json,
                    compliance_profile_id,
                    current_kill_switch_state,
                ),
            )

        record = self.get_request(risk_request_id)
        if record is None:
            raise LookupError(f"risk request not found after create: {risk_request_id}")
        return record

    def get_request(self, risk_request_id: str) -> RiskAssessmentRequestRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_risk_assessment_requests WHERE risk_request_id = ?",
                (risk_request_id,),
            ).fetchone()
        if row is None:
            return None
        return RiskAssessmentRequestRecord(**dict(row))

    def create_decision(
        self,
        *,
        risk_decision_id: str,
        risk_request_id: str,
        proposal_id: str,
        workflow_id: str,
        decision: str,
        rationale_text: str,
        risk_metrics_snapshot_json: str,
        freshness_expiry: str,
        policy_version_id: str,
        formula_version: str,
        provenance_bundle_id: str | None = None,
        approval_token: str | None = None,
        freshness_status: str = "fresh",
    ) -> RiskDecisionRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO risk_risk_decisions (
                    risk_decision_id,
                    risk_request_id,
                    proposal_id,
                    workflow_id,
                    decision,
                    rationale_text,
                    risk_metrics_snapshot_json,
                    freshness_expiry,
                    policy_version_id,
                    formula_version,
                    provenance_bundle_id,
                    approval_token,
                    freshness_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    risk_decision_id,
                    risk_request_id,
                    proposal_id,
                    workflow_id,
                    decision,
                    rationale_text,
                    risk_metrics_snapshot_json,
                    freshness_expiry,
                    policy_version_id,
                    formula_version,
                    provenance_bundle_id,
                    approval_token,
                    freshness_status,
                ),
            )

        record = self.get_decision(risk_decision_id)
        if record is None:
            raise LookupError(f"risk decision not found after create: {risk_decision_id}")
        return record

    def get_decision(self, risk_decision_id: str) -> RiskDecisionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_risk_decisions WHERE risk_decision_id = ?",
                (risk_decision_id,),
            ).fetchone()
        if row is None:
            return None
        return RiskDecisionRecord(**dict(row))

    def get_decision_by_approval_token(self, approval_token: str) -> RiskDecisionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_risk_decisions WHERE approval_token = ?",
                (approval_token,),
            ).fetchone()
        if row is None:
            return None
        return RiskDecisionRecord(**dict(row))

    def list_decisions_expired_before(self, timestamp: str) -> list[RiskDecisionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM risk_risk_decisions
                WHERE freshness_expiry < ?
                ORDER BY freshness_expiry
                """,
                (timestamp,),
            ).fetchall()
        return [RiskDecisionRecord(**dict(row)) for row in rows]

    def add_constraint(
        self,
        *,
        risk_decision_id: str,
        constraint_type: str,
        constraint_value_json: str,
    ) -> RiskConstraintRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO risk_risk_constraints (
                    risk_decision_id,
                    constraint_type,
                    constraint_value_json
                ) VALUES (?, ?, ?)
                """,
                (
                    risk_decision_id,
                    constraint_type,
                    constraint_value_json,
                ),
            )
            constraint_id = int(cursor.lastrowid)

        record = self.get_constraint(constraint_id)
        if record is None:
            raise LookupError(f"risk constraint not found after create: {constraint_id}")
        return record

    def get_constraint(self, constraint_id: int) -> RiskConstraintRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_risk_constraints WHERE constraint_id = ?",
                (constraint_id,),
            ).fetchone()
        if row is None:
            return None
        return RiskConstraintRecord(**dict(row))
