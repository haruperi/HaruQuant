"""Execution repositories over the SQLite baseline schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any, Iterable


@dataclass(frozen=True)
class ExecutionIntentRecord:
    execution_intent_id: str
    workflow_id: str
    proposal_id: str
    risk_decision_id: str
    action_type: str
    symbol: str
    side: str
    order_type: str
    size_json: str
    price_params_json: str
    sl_tp_params_json: str
    idempotency_key: str
    client_order_id: str | None
    status: str
    expiry_at: str | None
    pre_send_validation_snapshot_ref: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ExecutionSendAttemptRecord:
    send_attempt_id: int
    execution_intent_id: str
    attempt_no: int
    submitted_payload_hash: str
    transport_status: str
    broker_request_ref: str | None
    error_code: str | None
    error_message: str | None
    started_at: str
    finished_at: str | None
    latency_ms: int | None


@dataclass(frozen=True)
class ExecutionReceiptRecord:
    receipt_id: str
    execution_intent_id: str
    broker: str
    broker_order_id: str | None
    broker_deal_id: str | None
    receipt_status: str
    requested_price: float | None
    fill_price: float | None
    fill_qty: float | None
    spread_points: float | None
    slippage_points: float | None
    slippage_bps: float | None
    raw_receipt_ref: str | None
    broker_message: str | None
    broker_retcode: int | None
    authoritative_state: str
    received_at: str


@dataclass(frozen=True)
class ReconciliationRunRecord:
    reconciliation_run_id: int
    execution_intent_id: str
    run_reason: str
    result_state: str
    broker_truth_json: str
    local_truth_json: str
    conflict_flag: int
    incident_id: str | None
    started_at: str
    completed_at: str | None


class ExecutionRepository:
    """Minimal persistence wrapper for execution state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_intent(
        self,
        *,
        execution_intent_id: str,
        workflow_id: str,
        proposal_id: str,
        risk_decision_id: str,
        action_type: str,
        symbol: str,
        side: str,
        order_type: str,
        size_json: str,
        idempotency_key: str,
        status: str,
        price_params_json: str = "{}",
        sl_tp_params_json: str = "{}",
        client_order_id: str | None = None,
        expiry_at: str | None = None,
        pre_send_validation_snapshot_ref: str | None = None,
    ) -> ExecutionIntentRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_execution_intents (
                    execution_intent_id,
                    workflow_id,
                    proposal_id,
                    risk_decision_id,
                    action_type,
                    symbol,
                    side,
                    order_type,
                    size_json,
                    price_params_json,
                    sl_tp_params_json,
                    idempotency_key,
                    client_order_id,
                    status,
                    expiry_at,
                    pre_send_validation_snapshot_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_intent_id,
                    workflow_id,
                    proposal_id,
                    risk_decision_id,
                    action_type,
                    symbol,
                    side,
                    order_type,
                    size_json,
                    price_params_json,
                    sl_tp_params_json,
                    idempotency_key,
                    client_order_id,
                    status,
                    expiry_at,
                    pre_send_validation_snapshot_ref,
                ),
            )

        record = self.get_intent(execution_intent_id)
        if record is None:
            raise LookupError(f"execution intent not found after create: {execution_intent_id}")
        return record

    def get_intent(self, execution_intent_id: str) -> ExecutionIntentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_execution_intents WHERE execution_intent_id = ?",
                (execution_intent_id,),
            ).fetchone()
        if row is None:
            return None
        return ExecutionIntentRecord(**dict(row))

    def get_intent_by_idempotency_key(self, idempotency_key: str) -> ExecutionIntentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_execution_intents WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return ExecutionIntentRecord(**dict(row))

    def list_intents_by_statuses(
        self,
        statuses: Iterable[str],
    ) -> list[ExecutionIntentRecord]:
        status_values = tuple(statuses)
        if not status_values:
            return []

        placeholders = ", ".join("?" for _ in status_values)
        query = f"""
            SELECT *
            FROM core_execution_intents
            WHERE status IN ({placeholders})
            ORDER BY created_at ASC, execution_intent_id ASC
        """
        with self._connect() as connection:
            rows = connection.execute(query, status_values).fetchall()
        return [ExecutionIntentRecord(**dict(row)) for row in rows]

    def add_send_attempt(
        self,
        *,
        execution_intent_id: str,
        attempt_no: int,
        submitted_payload_hash: str,
        transport_status: str,
        broker_request_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        finished_at: str | None = None,
        latency_ms: int | None = None,
    ) -> ExecutionSendAttemptRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO core_execution_send_attempts (
                    execution_intent_id,
                    attempt_no,
                    submitted_payload_hash,
                    transport_status,
                    broker_request_ref,
                    error_code,
                    error_message,
                    finished_at,
                    latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_intent_id,
                    attempt_no,
                    submitted_payload_hash,
                    transport_status,
                    broker_request_ref,
                    error_code,
                    error_message,
                    finished_at,
                    latency_ms,
                ),
            )
            record_id = int(cursor.lastrowid)

        record = self.get_send_attempt(record_id)
        if record is None:
            raise LookupError(f"send attempt not found after create: {record_id}")
        return record

    def get_send_attempt(self, send_attempt_id: int) -> ExecutionSendAttemptRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_execution_send_attempts WHERE send_attempt_id = ?",
                (send_attempt_id,),
            ).fetchone()
        if row is None:
            return None
        return ExecutionSendAttemptRecord(**dict(row))

    def add_receipt(
        self,
        *,
        receipt_id: str,
        execution_intent_id: str,
        receipt_status: str,
        broker: str = "mt5",
        broker_order_id: str | None = None,
        broker_deal_id: str | None = None,
        requested_price: float | None = None,
        fill_price: float | None = None,
        fill_qty: float | None = None,
        spread_points: float | None = None,
        slippage_points: float | None = None,
        slippage_bps: float | None = None,
        raw_receipt_ref: str | None = None,
        broker_message: str | None = None,
        broker_retcode: int | None = None,
        authoritative_state: str = "PROVISIONAL",
    ) -> ExecutionReceiptRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO core_execution_receipts (
                    receipt_id,
                    execution_intent_id,
                    broker,
                    broker_order_id,
                    broker_deal_id,
                    receipt_status,
                    requested_price,
                    fill_price,
                    fill_qty,
                    spread_points,
                    slippage_points,
                    slippage_bps,
                    raw_receipt_ref,
                    broker_message,
                    broker_retcode,
                    authoritative_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    execution_intent_id,
                    broker,
                    broker_order_id,
                    broker_deal_id,
                    receipt_status,
                    requested_price,
                    fill_price,
                    fill_qty,
                    spread_points,
                    slippage_points,
                    slippage_bps,
                    raw_receipt_ref,
                    broker_message,
                    broker_retcode,
                    authoritative_state,
                ),
            )

        record = self.get_receipt(receipt_id)
        if record is None:
            raise LookupError(f"receipt not found after create: {receipt_id}")
        return record

    def get_receipt(self, receipt_id: str) -> ExecutionReceiptRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_execution_receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        if row is None:
            return None
        return ExecutionReceiptRecord(**dict(row))

    def get_latest_receipt_for_intent(
        self,
        execution_intent_id: str,
    ) -> ExecutionReceiptRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM core_execution_receipts
                WHERE execution_intent_id = ?
                ORDER BY received_at DESC, receipt_id DESC
                LIMIT 1
                """,
                (execution_intent_id,),
            ).fetchone()
        if row is None:
            return None
        return ExecutionReceiptRecord(**dict(row))

    def add_reconciliation_run(
        self,
        *,
        execution_intent_id: str,
        run_reason: str,
        result_state: str,
        broker_truth_json: str = "{}",
        local_truth_json: str = "{}",
        conflict_flag: int = 0,
        incident_id: str | None = None,
        completed_at: str | None = None,
    ) -> ReconciliationRunRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO core_reconciliation_runs (
                    execution_intent_id,
                    run_reason,
                    result_state,
                    broker_truth_json,
                    local_truth_json,
                    conflict_flag,
                    incident_id,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_intent_id,
                    run_reason,
                    result_state,
                    broker_truth_json,
                    local_truth_json,
                    conflict_flag,
                    incident_id,
                    completed_at,
                ),
            )
            record_id = int(cursor.lastrowid)

        record = self.get_reconciliation_run(record_id)
        if record is None:
            raise LookupError(f"reconciliation run not found after create: {record_id}")
        return record

    def get_reconciliation_run(self, reconciliation_run_id: int) -> ReconciliationRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM core_reconciliation_runs WHERE reconciliation_run_id = ?",
                (reconciliation_run_id,),
            ).fetchone()
        if row is None:
            return None
        return ReconciliationRunRecord(**dict(row))
