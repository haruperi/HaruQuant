"""Proposal repository over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class ProposalRecord:
    """Stored trade proposal state."""

    proposal_id: str
    workflow_id: str
    hypothesis_id: str
    state: str
    symbol: str
    direction: str
    candidate_price_logic_json: str
    proposed_size_json: str
    operating_envelope_json: str
    session_restrictions_json: str
    expiry_at: str | None
    transformation_version: str
    readiness_state: str
    created_at: str
    updated_at: str


class ProposalRepository:
    """Minimal persistence wrapper for trade proposals."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_proposal(
        self,
        *,
        proposal_id: str,
        workflow_id: str,
        hypothesis_id: str,
        state: str,
        symbol: str,
        direction: str,
        candidate_price_logic_json: str,
        proposed_size_json: str,
        transformation_version: str,
        readiness_state: str,
        operating_envelope_json: str = "{}",
        session_restrictions_json: str = "{}",
        expiry_at: str | None = None,
    ) -> ProposalRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_trade_proposals (
                    proposal_id,
                    workflow_id,
                    hypothesis_id,
                    state,
                    symbol,
                    direction,
                    candidate_price_logic_json,
                    proposed_size_json,
                    operating_envelope_json,
                    session_restrictions_json,
                    expiry_at,
                    transformation_version,
                    readiness_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    workflow_id,
                    hypothesis_id,
                    state,
                    symbol,
                    direction,
                    candidate_price_logic_json,
                    proposed_size_json,
                    operating_envelope_json,
                    session_restrictions_json,
                    expiry_at,
                    transformation_version,
                    readiness_state,
                ),
            )

        record = self.get_proposal(proposal_id)
        if record is None:
            raise LookupError(f"proposal not found after create: {proposal_id}")
        return record

    def get_proposal(self, proposal_id: str) -> ProposalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_trade_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def update_state(
        self,
        *,
        proposal_id: str,
        state: str,
        readiness_state: str | None = None,
        expiry_at: str | None = None,
    ) -> ProposalRecord:
        current = self.get_proposal(proposal_id)
        if current is None:
            raise LookupError(f"proposal not found: {proposal_id}")

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE core_trade_proposals
                SET state = ?,
                    readiness_state = ?,
                    expiry_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE proposal_id = ?
                """,
                (
                    state,
                    readiness_state if readiness_state is not None else current.readiness_state,
                    expiry_at if expiry_at is not None else current.expiry_at,
                    proposal_id,
                ),
            )

        updated = self.get_proposal(proposal_id)
        if updated is None:
            raise LookupError(f"proposal not found after update: {proposal_id}")
        return updated

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ProposalRecord:
        payload: dict[str, Any] = dict(row)
        return ProposalRecord(**payload)
