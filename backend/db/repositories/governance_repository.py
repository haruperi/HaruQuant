"""Governance repositories over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    action_type: str
    target_ref_type: str
    target_ref_id: str
    required_count: int
    state: str
    compliance_profile_id: str | None
    expires_at: str | None
    created_by_actor_type: str
    created_by_actor_id: str
    created_at: str
    decided_at: str | None
    metadata_json: str


@dataclass(frozen=True)
class ApprovalVoteRecord:
    vote_id: int
    approval_id: str
    approver_role: str
    approver_id: str
    decision: str
    reason_code: str | None
    rationale: str | None
    voted_at: str


@dataclass(frozen=True)
class PolicyRecord:
    policy_version_id: str
    policy_type: str
    version: str
    content_hash: str
    content_ref: str | None
    effective_from: str
    effective_to: str | None
    status: str
    created_at: str
    created_by: str


@dataclass(frozen=True)
class StrategyRecord:
    strategy_id: str
    strategy_name: str
    strategy_family: str
    current_lifecycle_state: str
    code_hash: str
    parameter_hash: str
    owner_id: str | None
    created_at: str
    updated_at: str


class GovernanceRepository:
    """Minimal persistence wrapper for governance and lifecycle state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_compliance_profile(
        self,
        *,
        compliance_profile_id: str,
        name: str,
        version: str,
        profile_json: str,
        active_flag: int = 0,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO gov_compliance_profiles (
                    compliance_profile_id,
                    name,
                    version,
                    profile_json,
                    active_flag
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (compliance_profile_id, name, version, profile_json, active_flag),
            )

    def create_approval(
        self,
        *,
        approval_id: str,
        action_type: str,
        target_ref_type: str,
        target_ref_id: str,
        required_count: int,
        state: str,
        created_by_actor_type: str,
        created_by_actor_id: str,
        compliance_profile_id: str | None = None,
        expires_at: str | None = None,
        metadata_json: str = "{}",
    ) -> ApprovalRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO gov_approvals (
                    approval_id,
                    action_type,
                    target_ref_type,
                    target_ref_id,
                    required_count,
                    state,
                    compliance_profile_id,
                    expires_at,
                    created_by_actor_type,
                    created_by_actor_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    action_type,
                    target_ref_type,
                    target_ref_id,
                    required_count,
                    state,
                    compliance_profile_id,
                    expires_at,
                    created_by_actor_type,
                    created_by_actor_id,
                    metadata_json,
                ),
            )

        record = self.get_approval(approval_id)
        if record is None:
            raise LookupError(f"approval not found after create: {approval_id}")
        return record

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM gov_approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            return None
        return ApprovalRecord(**dict(row))

    def add_vote(
        self,
        *,
        approval_id: str,
        approver_role: str,
        approver_id: str,
        decision: str,
        reason_code: str | None = None,
        rationale: str | None = None,
    ) -> ApprovalVoteRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO gov_approval_votes (
                    approval_id,
                    approver_role,
                    approver_id,
                    decision,
                    reason_code,
                    rationale
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    approver_role,
                    approver_id,
                    decision,
                    reason_code,
                    rationale,
                ),
            )
            record_id = int(cursor.lastrowid)

        record = self.get_vote(record_id)
        if record is None:
            raise LookupError(f"approval vote not found after create: {record_id}")
        return record

    def get_vote(self, vote_id: int) -> ApprovalVoteRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM gov_approval_votes WHERE vote_id = ?",
                (vote_id,),
            ).fetchone()
        if row is None:
            return None
        return ApprovalVoteRecord(**dict(row))

    def create_policy(
        self,
        *,
        policy_version_id: str,
        policy_type: str,
        version: str,
        content_hash: str,
        effective_from: str,
        status: str,
        created_by: str,
        content_ref: str | None = None,
        effective_to: str | None = None,
    ) -> PolicyRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO gov_policies (
                    policy_version_id,
                    policy_type,
                    version,
                    content_hash,
                    content_ref,
                    effective_from,
                    effective_to,
                    status,
                    created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_version_id,
                    policy_type,
                    version,
                    content_hash,
                    content_ref,
                    effective_from,
                    effective_to,
                    status,
                    created_by,
                ),
            )

        record = self.get_policy(policy_version_id)
        if record is None:
            raise LookupError(f"policy not found after create: {policy_version_id}")
        return record

    def get_policy(self, policy_version_id: str) -> PolicyRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM gov_policies WHERE policy_version_id = ?",
                (policy_version_id,),
            ).fetchone()
        if row is None:
            return None
        return PolicyRecord(**dict(row))

    def create_strategy(
        self,
        *,
        strategy_id: str,
        strategy_name: str,
        strategy_family: str,
        current_lifecycle_state: str,
        code_hash: str,
        parameter_hash: str,
        owner_id: str | None = None,
    ) -> StrategyRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO gov_strategy_registry (
                    strategy_id,
                    strategy_name,
                    strategy_family,
                    current_lifecycle_state,
                    code_hash,
                    parameter_hash,
                    owner_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    strategy_name,
                    strategy_family,
                    current_lifecycle_state,
                    code_hash,
                    parameter_hash,
                    owner_id,
                ),
            )

        record = self.get_strategy(strategy_id)
        if record is None:
            raise LookupError(f"strategy not found after create: {strategy_id}")
        return record

    def get_strategy(self, strategy_id: str) -> StrategyRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM gov_strategy_registry WHERE strategy_id = ?",
                (strategy_id,),
            ).fetchone()
        if row is None:
            return None
        return StrategyRecord(**dict(row))
