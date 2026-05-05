"""Repository for Agentic Firm Phase 4 persistence tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class AgentTaskRecord:
    task_id: str
    parent_task_id: str | None
    workflow_id: str | None
    title: str
    description: str
    owner_agent: str
    status: str
    priority: int
    expected_output_contract: str | None
    required_tools_json: str
    input_refs_json: str
    metadata_json: str
    created_at: str
    updated_at: str
    due_at: str | None


@dataclass(frozen=True)
class AgentTaskEventRecord:
    event_id: int
    task_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    actor_type: str
    actor_id: str
    event_payload_json: str
    created_at: str


@dataclass(frozen=True)
class EvidenceRefRecord:
    evidence_id: str
    evidence_type: str
    workflow_id: str | None
    task_id: str | None
    source_table: str | None
    source_ref_id: str | None
    uri: str | None
    content_hash: str | None
    summary: str | None
    source_agent: str | None
    metadata_json: str
    created_at: str


@dataclass(frozen=True)
class AuditLogRecord:
    audit_id: str
    actor_name: str
    agent_name: str | None
    tool_name: str | None
    action_type: str
    target_type: str | None
    target_ref_id: str | None
    input_hash: str
    output_hash: str | None
    evidence_refs_json: str
    request_id: str | None
    parent_task_id: str | None
    workflow_id: str | None
    metadata_json: str
    created_at: str


class AgenticFirmRepository:
    """Persistence wrapper for Phase 4 firm tables."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def _insert(self, table: str, values: dict[str, Any]) -> None:
        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                tuple(values[column] for column in columns),
            )

    def _get_by_id(
        self,
        table: str,
        key_column: str,
        key_value: str | int,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ?",
                (key_value,),
            ).fetchone()
        return self._row_to_dict(row)

    def create_agent_task(
        self,
        *,
        task_id: str,
        title: str,
        description: str,
        owner_agent: str,
        status: str = "pending",
        parent_task_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 3,
        expected_output_contract: str | None = None,
        required_tools_json: str = "[]",
        input_refs_json: str = "[]",
        metadata_json: str = "{}",
        due_at: str | None = None,
    ) -> AgentTaskRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_tasks (
                    task_id,
                    parent_task_id,
                    workflow_id,
                    title,
                    description,
                    owner_agent,
                    status,
                    priority,
                    expected_output_contract,
                    required_tools_json,
                    input_refs_json,
                    metadata_json,
                    due_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    parent_task_id,
                    workflow_id,
                    title,
                    description,
                    owner_agent,
                    status,
                    priority,
                    expected_output_contract,
                    required_tools_json,
                    input_refs_json,
                    metadata_json,
                    due_at,
                ),
            )

        record = self.get_agent_task(task_id)
        if record is None:
            raise LookupError(f"agent task not found after create: {task_id}")
        return record

    def get_agent_task(self, task_id: str) -> AgentTaskRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentTaskRecord(**dict(row))

    def append_agent_task_event(
        self,
        *,
        task_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        from_status: str | None = None,
        to_status: str | None = None,
        event_payload_json: str = "{}",
    ) -> AgentTaskEventRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_task_events (
                    task_id,
                    event_type,
                    from_status,
                    to_status,
                    actor_type,
                    actor_id,
                    event_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    event_type,
                    from_status,
                    to_status,
                    actor_type,
                    actor_id,
                    event_payload_json,
                ),
            )
            event_id = int(cursor.lastrowid)

        record = self.get_agent_task_event(event_id)
        if record is None:
            raise LookupError(f"agent task event not found after create: {event_id}")
        return record

    def get_agent_task_event(self, event_id: int) -> AgentTaskEventRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_task_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentTaskEventRecord(**dict(row))

    def create_tool_call(
        self,
        *,
        tool_call_id: str,
        task_id: str,
        requesting_agent: str,
        tool_name: str,
        status: str = "planned",
        risk_level: str = "read_only",
        requires_human_approval: bool = False,
        requires_risk_governor: bool = False,
        arguments_json: str = "{}",
        result_json: str | None = None,
        error_message: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        self._insert(
            "agent_tool_calls",
            {
                "tool_call_id": tool_call_id,
                "task_id": task_id,
                "requesting_agent": requesting_agent,
                "tool_name": tool_name,
                "status": status,
                "risk_level": risk_level,
                "requires_human_approval": int(requires_human_approval),
                "requires_risk_governor": int(requires_risk_governor),
                "arguments_json": arguments_json,
                "result_json": result_json,
                "error_message": error_message,
                "started_at": started_at,
                "completed_at": completed_at,
            },
        )
        record = self.get_tool_call(tool_call_id)
        if record is None:
            raise LookupError(f"tool call not found after create: {tool_call_id}")
        return record

    def get_tool_call(self, tool_call_id: str) -> dict[str, Any] | None:
        return self._get_by_id("agent_tool_calls", "tool_call_id", tool_call_id)

    def create_observation(
        self,
        *,
        observation_id: str,
        task_id: str,
        agent_name: str,
        observation_type: str,
        summary: str,
        data_json: str = "{}",
        evidence_refs_json: str = "[]",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        self._insert(
            "agent_observations",
            {
                "observation_id": observation_id,
                "task_id": task_id,
                "agent_name": agent_name,
                "observation_type": observation_type,
                "summary": summary,
                "data_json": data_json,
                "evidence_refs_json": evidence_refs_json,
                "confidence": confidence,
            },
        )
        record = self.get_observation(observation_id)
        if record is None:
            raise LookupError(f"observation not found after create: {observation_id}")
        return record

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        return self._get_by_id("agent_observations", "observation_id", observation_id)

    def create_decision(
        self,
        *,
        decision_id: str,
        task_id: str,
        agent_name: str,
        decision_type: str,
        decision: str,
        rationale: str,
        evidence_refs_json: str = "[]",
        requires_board_approval: bool = False,
        requires_risk_governor: bool = False,
    ) -> dict[str, Any]:
        self._insert(
            "agent_decisions",
            {
                "decision_id": decision_id,
                "task_id": task_id,
                "agent_name": agent_name,
                "decision_type": decision_type,
                "decision": decision,
                "rationale": rationale,
                "evidence_refs_json": evidence_refs_json,
                "requires_board_approval": int(requires_board_approval),
                "requires_risk_governor": int(requires_risk_governor),
            },
        )
        record = self.get_decision(decision_id)
        if record is None:
            raise LookupError(f"decision not found after create: {decision_id}")
        return record

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._get_by_id("agent_decisions", "decision_id", decision_id)

    def create_evidence_ref(
        self,
        *,
        evidence_id: str,
        evidence_type: str,
        workflow_id: str | None = None,
        task_id: str | None = None,
        source_table: str | None = None,
        source_ref_id: str | None = None,
        uri: str | None = None,
        content_hash: str | None = None,
        summary: str | None = None,
        source_agent: str | None = None,
        metadata_json: str = "{}",
    ) -> EvidenceRefRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_refs (
                    evidence_id,
                    evidence_type,
                    workflow_id,
                    task_id,
                    source_table,
                    source_ref_id,
                    uri,
                    content_hash,
                    summary,
                    source_agent,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    evidence_type,
                    workflow_id,
                    task_id,
                    source_table,
                    source_ref_id,
                    uri,
                    content_hash,
                    summary,
                    source_agent,
                    metadata_json,
                ),
            )

        record = self.get_evidence_ref(evidence_id)
        if record is None:
            raise LookupError(f"evidence ref not found after create: {evidence_id}")
        return record

    def get_evidence_ref(self, evidence_id: str) -> EvidenceRefRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence_refs WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        if row is None:
            return None
        return EvidenceRefRecord(**dict(row))

    def create_research_report(
        self,
        *,
        research_report_id: str,
        research_question: str,
        report_json: str,
        created_by_agent: str,
        workflow_id: str | None = None,
        task_id: str | None = None,
        confidence: float = 0.0,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "research_reports",
            {
                "research_report_id": research_report_id,
                "workflow_id": workflow_id,
                "task_id": task_id,
                "research_question": research_question,
                "report_json": report_json,
                "confidence": confidence,
                "evidence_refs_json": evidence_refs_json,
                "created_by_agent": created_by_agent,
            },
        )
        record = self.get_research_report(research_report_id)
        if record is None:
            raise LookupError(
                f"research report not found after create: {research_report_id}"
            )
        return record

    def get_research_report(self, research_report_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "research_reports",
            "research_report_id",
            research_report_id,
        )

    def create_strategy_spec(
        self,
        *,
        strategy_spec_id: str,
        strategy_name: str,
        version: str,
        market: str,
        symbol: str,
        timeframe: str,
        spec_json: str,
        created_by_agent: str,
        workflow_id: str | None = None,
        task_id: str | None = None,
        strategy_id: str | None = None,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "strategy_specs",
            {
                "strategy_spec_id": strategy_spec_id,
                "workflow_id": workflow_id,
                "task_id": task_id,
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "version": version,
                "market": market,
                "symbol": symbol,
                "timeframe": timeframe,
                "spec_json": spec_json,
                "evidence_refs_json": evidence_refs_json,
                "created_by_agent": created_by_agent,
            },
        )
        record = self.get_strategy_spec(strategy_spec_id)
        if record is None:
            raise LookupError(f"strategy spec not found after create: {strategy_spec_id}")
        return record

    def get_strategy_spec(self, strategy_spec_id: str) -> dict[str, Any] | None:
        return self._get_by_id("strategy_specs", "strategy_spec_id", strategy_spec_id)

    def create_strategy_review(
        self,
        *,
        strategy_review_id: str,
        reviewer_agent: str,
        verdict: str,
        review_json: str,
        strategy_spec_id: str | None = None,
        strategy_id: str | None = None,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "strategy_reviews",
            {
                "strategy_review_id": strategy_review_id,
                "strategy_spec_id": strategy_spec_id,
                "strategy_id": strategy_id,
                "reviewer_agent": reviewer_agent,
                "verdict": verdict,
                "review_json": review_json,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_strategy_review(strategy_review_id)
        if record is None:
            raise LookupError(
                f"strategy review not found after create: {strategy_review_id}"
            )
        return record

    def get_strategy_review(self, strategy_review_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "strategy_reviews",
            "strategy_review_id",
            strategy_review_id,
        )

    def create_backtest_run_ref(
        self,
        *,
        backtest_run_ref_id: str,
        strategy_id: str,
        result_ref: str,
        workflow_id: str | None = None,
        strategy_spec_id: str | None = None,
        backtest_id: str | None = None,
        summary_json: str = "{}",
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "backtest_run_refs",
            {
                "backtest_run_ref_id": backtest_run_ref_id,
                "workflow_id": workflow_id,
                "strategy_id": strategy_id,
                "strategy_spec_id": strategy_spec_id,
                "backtest_id": backtest_id,
                "result_ref": result_ref,
                "summary_json": summary_json,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_backtest_run_ref(backtest_run_ref_id)
        if record is None:
            raise LookupError(
                f"backtest run ref not found after create: {backtest_run_ref_id}"
            )
        return record

    def get_backtest_run_ref(self, backtest_run_ref_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "backtest_run_refs",
            "backtest_run_ref_id",
            backtest_run_ref_id,
        )

    def create_robustness_run_ref(
        self,
        *,
        robustness_run_ref_id: str,
        strategy_id: str,
        robustness_type: str,
        result_ref: str,
        workflow_id: str | None = None,
        strategy_spec_id: str | None = None,
        summary_json: str = "{}",
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "robustness_run_refs",
            {
                "robustness_run_ref_id": robustness_run_ref_id,
                "workflow_id": workflow_id,
                "strategy_id": strategy_id,
                "strategy_spec_id": strategy_spec_id,
                "robustness_type": robustness_type,
                "result_ref": result_ref,
                "summary_json": summary_json,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_robustness_run_ref(robustness_run_ref_id)
        if record is None:
            raise LookupError(
                "robustness run ref not found after create: "
                f"{robustness_run_ref_id}"
            )
        return record

    def get_robustness_run_ref(
        self,
        robustness_run_ref_id: str,
    ) -> dict[str, Any] | None:
        return self._get_by_id(
            "robustness_run_refs",
            "robustness_run_ref_id",
            robustness_run_ref_id,
        )

    def create_risk_review_ref(
        self,
        *,
        risk_review_ref_id: str,
        reviewer_agent: str,
        verdict: str,
        review_ref: str,
        workflow_id: str | None = None,
        strategy_id: str | None = None,
        proposal_id: str | None = None,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "risk_review_refs",
            {
                "risk_review_ref_id": risk_review_ref_id,
                "workflow_id": workflow_id,
                "strategy_id": strategy_id,
                "proposal_id": proposal_id,
                "reviewer_agent": reviewer_agent,
                "verdict": verdict,
                "review_ref": review_ref,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_risk_review_ref(risk_review_ref_id)
        if record is None:
            raise LookupError(
                f"risk review ref not found after create: {risk_review_ref_id}"
            )
        return record

    def get_risk_review_ref(self, risk_review_ref_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "risk_review_refs",
            "risk_review_ref_id",
            risk_review_ref_id,
        )

    def create_paper_trade_ref(
        self,
        *,
        paper_trade_ref_id: str,
        strategy_id: str,
        execution_ref: str,
        workflow_id: str | None = None,
        proposal_id: str | None = None,
        result_json: str = "{}",
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "paper_trade_refs",
            {
                "paper_trade_ref_id": paper_trade_ref_id,
                "workflow_id": workflow_id,
                "strategy_id": strategy_id,
                "proposal_id": proposal_id,
                "execution_ref": execution_ref,
                "result_json": result_json,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_paper_trade_ref(paper_trade_ref_id)
        if record is None:
            raise LookupError(
                f"paper trade ref not found after create: {paper_trade_ref_id}"
            )
        return record

    def get_paper_trade_ref(self, paper_trade_ref_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "paper_trade_refs",
            "paper_trade_ref_id",
            paper_trade_ref_id,
        )

    def create_live_trade_ref(
        self,
        *,
        live_trade_ref_id: str,
        strategy_id: str,
        workflow_id: str | None = None,
        proposal_id: str | None = None,
        execution_intent_id: str | None = None,
        execution_receipt_id: str | None = None,
        broker_ref: str | None = None,
        result_json: str = "{}",
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "live_trade_refs",
            {
                "live_trade_ref_id": live_trade_ref_id,
                "workflow_id": workflow_id,
                "strategy_id": strategy_id,
                "proposal_id": proposal_id,
                "execution_intent_id": execution_intent_id,
                "execution_receipt_id": execution_receipt_id,
                "broker_ref": broker_ref,
                "result_json": result_json,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_live_trade_ref(live_trade_ref_id)
        if record is None:
            raise LookupError(
                f"live trade ref not found after create: {live_trade_ref_id}"
            )
        return record

    def get_live_trade_ref(self, live_trade_ref_id: str) -> dict[str, Any] | None:
        return self._get_by_id("live_trade_refs", "live_trade_ref_id", live_trade_ref_id)

    def upsert_strategy_lifecycle(
        self,
        *,
        strategy_id: str,
        current_state: str,
        lifecycle_version: str = "1.0.0",
        active_strategy_version_id: str | None = None,
        evidence_bundle_id: str | None = None,
        metadata_json: str = "{}",
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO strategy_lifecycle (
                    strategy_id,
                    current_state,
                    lifecycle_version,
                    active_strategy_version_id,
                    evidence_bundle_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id) DO UPDATE SET
                    current_state = excluded.current_state,
                    lifecycle_version = excluded.lifecycle_version,
                    active_strategy_version_id = excluded.active_strategy_version_id,
                    evidence_bundle_id = excluded.evidence_bundle_id,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    strategy_id,
                    current_state,
                    lifecycle_version,
                    active_strategy_version_id,
                    evidence_bundle_id,
                    metadata_json,
                ),
            )
        record = self.get_strategy_lifecycle(strategy_id)
        if record is None:
            raise LookupError(
                f"strategy lifecycle not found after upsert: {strategy_id}"
            )
        return record

    def get_strategy_lifecycle(self, strategy_id: str) -> dict[str, Any] | None:
        return self._get_by_id("strategy_lifecycle", "strategy_id", strategy_id)

    def create_strategy_version(
        self,
        *,
        strategy_version_id: str,
        strategy_id: str,
        version: str,
        created_by_agent: str,
        code_ref: str | None = None,
        code_hash: str | None = None,
        spec_ref: str | None = None,
        parameter_hash: str | None = None,
        metadata_json: str = "{}",
    ) -> dict[str, Any]:
        self._insert(
            "strategy_versions",
            {
                "strategy_version_id": strategy_version_id,
                "strategy_id": strategy_id,
                "version": version,
                "code_ref": code_ref,
                "code_hash": code_hash,
                "spec_ref": spec_ref,
                "parameter_hash": parameter_hash,
                "created_by_agent": created_by_agent,
                "metadata_json": metadata_json,
            },
        )
        record = self.get_strategy_version(strategy_version_id)
        if record is None:
            raise LookupError(
                f"strategy version not found after create: {strategy_version_id}"
            )
        return record

    def get_strategy_version(self, strategy_version_id: str) -> dict[str, Any] | None:
        return self._get_by_id(
            "strategy_versions",
            "strategy_version_id",
            strategy_version_id,
        )

    def append_strategy_status_history(
        self,
        *,
        strategy_id: str,
        to_state: str,
        reason: str,
        actor_type: str,
        actor_id: str,
        from_state: str | None = None,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO strategy_status_history (
                    strategy_id,
                    from_state,
                    to_state,
                    reason,
                    actor_type,
                    actor_id,
                    evidence_refs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    from_state,
                    to_state,
                    reason,
                    actor_type,
                    actor_id,
                    evidence_refs_json,
                ),
            )
            status_history_id = int(cursor.lastrowid)
        record = self.get_strategy_status_history(status_history_id)
        if record is None:
            raise LookupError(
                "strategy status history not found after create: "
                f"{status_history_id}"
            )
        return record

    def get_strategy_status_history(
        self,
        status_history_id: int,
    ) -> dict[str, Any] | None:
        return self._get_by_id(
            "strategy_status_history",
            "status_history_id",
            status_history_id,
        )

    def create_strategy_promotion_request(
        self,
        *,
        promotion_request_id: str,
        strategy_id: str,
        from_state: str,
        to_state: str,
        requested_by_agent: str,
        rationale: str,
        status: str = "pending",
        evidence_refs_json: str = "[]",
        decided_at: str | None = None,
        decision_ref: str | None = None,
    ) -> dict[str, Any]:
        self._insert(
            "strategy_promotion_requests",
            {
                "promotion_request_id": promotion_request_id,
                "strategy_id": strategy_id,
                "from_state": from_state,
                "to_state": to_state,
                "requested_by_agent": requested_by_agent,
                "rationale": rationale,
                "evidence_refs_json": evidence_refs_json,
                "status": status,
                "decided_at": decided_at,
                "decision_ref": decision_ref,
            },
        )
        record = self.get_strategy_promotion_request(promotion_request_id)
        if record is None:
            raise LookupError(
                "strategy promotion request not found after create: "
                f"{promotion_request_id}"
            )
        return record

    def get_strategy_promotion_request(
        self,
        promotion_request_id: str,
    ) -> dict[str, Any] | None:
        return self._get_by_id(
            "strategy_promotion_requests",
            "promotion_request_id",
            promotion_request_id,
        )

    def create_strategy_retirement_record(
        self,
        *,
        retirement_id: str,
        strategy_id: str,
        retired_from_state: str,
        reason: str,
        retired_by_actor_type: str,
        retired_by_actor_id: str,
        evidence_refs_json: str = "[]",
    ) -> dict[str, Any]:
        self._insert(
            "strategy_retirement_records",
            {
                "retirement_id": retirement_id,
                "strategy_id": strategy_id,
                "retired_from_state": retired_from_state,
                "reason": reason,
                "retired_by_actor_type": retired_by_actor_type,
                "retired_by_actor_id": retired_by_actor_id,
                "evidence_refs_json": evidence_refs_json,
            },
        )
        record = self.get_strategy_retirement_record(retirement_id)
        if record is None:
            raise LookupError(
                f"strategy retirement record not found after create: {retirement_id}"
            )
        return record

    def get_strategy_retirement_record(
        self,
        retirement_id: str,
    ) -> dict[str, Any] | None:
        return self._get_by_id(
            "strategy_retirement_records",
            "retirement_id",
            retirement_id,
        )

    def append_audit_log(
        self,
        *,
        audit_id: str,
        actor_name: str,
        action_type: str,
        input_hash: str,
        agent_name: str | None = None,
        tool_name: str | None = None,
        target_type: str | None = None,
        target_ref_id: str | None = None,
        output_hash: str | None = None,
        evidence_refs_json: str = "[]",
        request_id: str | None = None,
        parent_task_id: str | None = None,
        workflow_id: str | None = None,
        metadata_json: str = "{}",
    ) -> AuditLogRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_log (
                    audit_id,
                    actor_name,
                    agent_name,
                    tool_name,
                    action_type,
                    target_type,
                    target_ref_id,
                    input_hash,
                    output_hash,
                    evidence_refs_json,
                    request_id,
                    parent_task_id,
                    workflow_id,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    actor_name,
                    agent_name,
                    tool_name,
                    action_type,
                    target_type,
                    target_ref_id,
                    input_hash,
                    output_hash,
                    evidence_refs_json,
                    request_id,
                    parent_task_id,
                    workflow_id,
                    metadata_json,
                ),
            )

        record = self.get_audit_log(audit_id)
        if record is None:
            raise LookupError(f"audit log not found after append: {audit_id}")
        return record

    def get_audit_log(self, audit_id: str) -> AuditLogRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audit_log WHERE audit_id = ?",
                (audit_id,),
            ).fetchone()
        if row is None:
            return None
        return AuditLogRecord(**dict(row))


__all__ = [
    "AgentTaskEventRecord",
    "AgentTaskRecord",
    "AgenticFirmRepository",
    "AuditLogRecord",
    "EvidenceRefRecord",
]
