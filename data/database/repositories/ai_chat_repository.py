"""SQLite persistence for AI chat threads, messages, memory, and signal proposals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from uuid import uuid4


@dataclass(frozen=True)
class AiChatThreadRow:
    thread_id: str
    user_id: str
    title: str
    status: str
    retention_class: str
    active_context_revision: str | None
    current_route: str | None
    current_page_type: str | None
    created_at: str
    updated_at: str
    last_message_at: str | None
    archived_at: str | None = None
    deleted_at: str | None = None
    purged_at: str | None = None
    retention_expires_at: str | None = None
    purge_after: str | None = None
    legal_hold_until: str | None = None
    legal_hold_reason: str | None = None


@dataclass(frozen=True)
class AiChatMessageRow:
    message_id: str
    thread_id: str
    role: str
    content: str
    request_id: str | None
    tool_calls_json: str
    signal_proposal_id: str | None
    action_draft_id: str | None
    context_revision: str | None
    created_at: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    latency_ms: int | None = None
    metadata_json: str = "{}"



@dataclass(frozen=True)
class AiChatMemorySummaryRow:
    summary_id: str
    thread_id: str
    summary_text: str
    source_message_count: int
    created_at: str


@dataclass(frozen=True)
class AiChatPinnedFactRow:
    fact_id: int
    thread_id: str
    fact_key: str
    fact_value: str
    source: str
    created_at: str


@dataclass(frozen=True)
class AiChatSignalProposalRow:
    proposal_id: str
    thread_id: str
    user_id: str
    request_id: str | None
    title: str
    hypothesis: str
    symbol: str
    timeframe: str
    direction: str
    entry_logic: str
    exit_logic: str
    confidence: int
    rationale: str
    risk_note: str
    status: str
    watchlist_saved: int
    review_queue_saved: int
    non_executed_label: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AiChatActionDraftRow:
    draft_id: str
    thread_id: str
    user_id: str
    request_id: str | None
    draft_type: str
    title: str
    description: str
    payload_json: str
    risk_precheck_status: str
    risk_precheck_notes: str
    approval_id: str | None
    status: str
    requires_human_approval: int
    side_effect_status: str
    governed_workflow_id: str | None
    execution_intent_id: str | None
    execution_receipt_id: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AiChatLifecycleAuditEventRow:
    event_id: str
    thread_id: str
    user_id: str
    actor_id: str
    action: str
    from_status: str | None
    to_status: str | None
    from_retention_class: str | None
    to_retention_class: str | None
    reason: str
    metadata_json: str
    created_at: str


class AiChatRepository:
    """Persistence wrapper for AI chat conversation state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_thread(
        self,
        *,
        thread_id: str,
        user_id: str,
        title: str,
        status: str = "active",
        retention_class: str = "standard",
        active_context_revision: str | None = None,
        current_route: str | None = None,
        current_page_type: str | None = None,
    ) -> AiChatThreadRow:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_threads (
                    thread_id,
                    user_id,
                    title,
                    status,
                    retention_class,
                    active_context_revision,
                    current_route,
                    current_page_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    user_id,
                    title,
                    status,
                    retention_class,
                    active_context_revision,
                    current_route,
                    current_page_type,
                ),
            )
        record = self.get_thread(thread_id, user_id=user_id)
        if record is None:
            raise LookupError(f"thread not found after create: {thread_id}")
        self.record_lifecycle_event(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=user_id,
            action="thread_created",
            to_status=record.status,
            to_retention_class=record.retention_class,
            reason="Conversation thread created.",
        )
        return record

    def get_thread(
        self,
        thread_id: str,
        *,
        user_id: str | None = None,
        include_deleted: bool = False,
    ) -> AiChatThreadRow | None:
        query = "SELECT * FROM ai_chat_threads WHERE thread_id = ?"
        params: list[object] = [thread_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if not include_deleted:
            query += " AND status NOT IN ('deleted', 'purged')"
        with self._connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
        return None if row is None else AiChatThreadRow(**dict(row))

    def list_threads(
        self,
        *,
        user_id: str,
        include_deleted: bool = False,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[AiChatThreadRow]:
        query = "SELECT * FROM ai_chat_threads WHERE user_id = ?"
        params: list[object] = [user_id]
        if not include_deleted:
            query += " AND status NOT IN ('deleted', 'purged')"
        if not include_archived:
            query += " AND status != 'archived'"
        query += " ORDER BY COALESCE(last_message_at, updated_at) DESC, created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [AiChatThreadRow(**dict(row)) for row in rows]

    def update_thread_title(self, *, thread_id: str, user_id: str, title: str) -> AiChatThreadRow:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ai_chat_threads
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status != 'deleted'
                """,
                (title, thread_id, user_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"thread not found: {thread_id}")
        record = self.get_thread(thread_id, user_id=user_id)
        if record is None:
            raise LookupError(f"thread not found after title update: {thread_id}")
        return record

    def update_thread_context(
        self,
        *,
        thread_id: str,
        user_id: str,
        current_route: str | None,
        current_page_type: str | None,
        active_context_revision: str | None,
    ) -> AiChatThreadRow:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ai_chat_threads
                SET current_route = ?,
                    current_page_type = ?,
                    active_context_revision = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status != 'deleted'
                """,
                (
                    current_route,
                    current_page_type,
                    active_context_revision,
                    thread_id,
                    user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"thread not found: {thread_id}")
        record = self.get_thread(thread_id, user_id=user_id)
        if record is None:
            raise LookupError(f"thread not found after context update: {thread_id}")
        return record

    def soft_delete_thread(self, *, thread_id: str, user_id: str) -> bool:
        current = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None or current.status in {"deleted", "purged"}:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ai_chat_threads
                SET status = 'deleted',
                    deleted_at = CURRENT_TIMESTAMP,
                    purge_after = CASE
                        WHEN retention_class IN ('regulated', 'legal_hold') THEN purge_after
                        ELSE COALESCE(purge_after, datetime('now', '+30 days'))
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status != 'deleted'
                """,
                (thread_id, user_id),
            )
            deleted = cursor.rowcount == 1
        if deleted:
            updated = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
            self.record_lifecycle_event(
                thread_id=thread_id,
                user_id=user_id,
                actor_id=user_id,
                action="thread_deleted",
                from_status=current.status,
                to_status=updated.status if updated else "deleted",
                from_retention_class=current.retention_class,
                to_retention_class=updated.retention_class if updated else current.retention_class,
                reason="User requested conversation deletion.",
            )
        return deleted

    def archive_thread(self, *, thread_id: str, user_id: str, actor_id: str | None = None, reason: str = "") -> AiChatThreadRow:
        current = self.get_thread(thread_id, user_id=user_id)
        if current is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ai_chat_threads
                SET status = 'archived',
                    archived_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status = 'active'
                """,
                (thread_id, user_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"thread cannot be archived: {thread_id}")
        updated = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if updated is None:
            raise LookupError(f"thread not found after archive: {thread_id}")
        self.record_lifecycle_event(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=actor_id or user_id,
            action="thread_archived",
            from_status=current.status,
            to_status=updated.status,
            from_retention_class=current.retention_class,
            to_retention_class=updated.retention_class,
            reason=reason or "Conversation archived.",
        )
        return updated

    def restore_thread(self, *, thread_id: str, user_id: str, actor_id: str | None = None, reason: str = "") -> AiChatThreadRow:
        current = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None or current.status not in {"archived", "deleted"}:
            raise LookupError(f"thread cannot be restored: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ai_chat_threads
                SET status = 'active',
                    deleted_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status IN ('archived', 'deleted')
                """,
                (thread_id, user_id),
            )
        updated = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if updated is None:
            raise LookupError(f"thread not found after restore: {thread_id}")
        self.record_lifecycle_event(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=actor_id or user_id,
            action="thread_restored",
            from_status=current.status,
            to_status=updated.status,
            from_retention_class=current.retention_class,
            to_retention_class=updated.retention_class,
            reason=reason or "Conversation restored.",
        )
        return updated

    def update_thread_retention(
        self,
        *,
        thread_id: str,
        user_id: str,
        retention_class: str,
        retention_expires_at: str | None = None,
        purge_after: str | None = None,
        legal_hold_until: str | None = None,
        legal_hold_reason: str | None = None,
        actor_id: str | None = None,
        reason: str = "",
    ) -> AiChatThreadRow:
        current = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ai_chat_threads
                SET retention_class = ?,
                    retention_expires_at = ?,
                    purge_after = ?,
                    legal_hold_until = ?,
                    legal_hold_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND status != 'purged'
                """,
                (
                    retention_class,
                    retention_expires_at,
                    purge_after,
                    legal_hold_until,
                    legal_hold_reason,
                    thread_id,
                    user_id,
                ),
            )
        updated = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if updated is None:
            raise LookupError(f"thread not found after retention update: {thread_id}")
        self.record_lifecycle_event(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=actor_id or user_id,
            action="retention_class_changed",
            from_status=current.status,
            to_status=updated.status,
            from_retention_class=current.retention_class,
            to_retention_class=updated.retention_class,
            reason=reason or "Retention class updated.",
        )
        return updated

    def purge_thread(self, *, thread_id: str, user_id: str, actor_id: str | None = None, reason: str = "") -> bool:
        current = self.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None or current.retention_class in {"regulated", "legal_hold"} or current.status == "purged":
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ai_chat_messages
                SET content = '[purged]',
                    tool_calls_json = '[]',
                    metadata_json = '{}'
                WHERE thread_id = ?
                """,
                (thread_id,),
            )
            connection.execute("DELETE FROM ai_chat_memory_summaries WHERE thread_id = ?", (thread_id,))
            connection.execute("DELETE FROM ai_chat_pinned_facts WHERE thread_id = ?", (thread_id,))
            connection.execute(
                """
                UPDATE ai_chat_threads
                SET status = 'purged',
                    title = '[purged]',
                    active_context_revision = NULL,
                    current_route = NULL,
                    current_page_type = NULL,
                    purged_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ? AND retention_class NOT IN ('regulated', 'legal_hold')
                """,
                (thread_id, user_id),
            )
        self.record_lifecycle_event(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=actor_id or user_id,
            action="thread_purged",
            from_status=current.status,
            to_status="purged",
            from_retention_class=current.retention_class,
            to_retention_class=current.retention_class,
            reason=reason or f"Conversation purged; message rows redacted: {cursor.rowcount}.",
        )
        return True

    def list_threads_due_for_lifecycle(self, *, now: str, limit: int = 200) -> list[AiChatThreadRow]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ai_chat_threads
                WHERE status != 'purged'
                  AND retention_class != 'legal_hold'
                  AND (
                    (retention_expires_at IS NOT NULL AND retention_expires_at <= ?)
                    OR (purge_after IS NOT NULL AND purge_after <= ?)
                  )
                ORDER BY COALESCE(purge_after, retention_expires_at) ASC
                LIMIT ?
                """,
                (now, now, limit),
            ).fetchall()
        return [AiChatThreadRow(**dict(row)) for row in rows]

    def record_lifecycle_event(
        self,
        *,
        thread_id: str,
        user_id: str,
        actor_id: str,
        action: str,
        from_status: str | None = None,
        to_status: str | None = None,
        from_retention_class: str | None = None,
        to_retention_class: str | None = None,
        reason: str = "",
        metadata_json: str = "{}",
    ) -> AiChatLifecycleAuditEventRow:
        event_id = f"chat-audit-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_lifecycle_audit_events (
                    event_id,
                    thread_id,
                    user_id,
                    actor_id,
                    action,
                    from_status,
                    to_status,
                    from_retention_class,
                    to_retention_class,
                    reason,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    thread_id,
                    user_id,
                    actor_id,
                    action,
                    from_status,
                    to_status,
                    from_retention_class,
                    to_retention_class,
                    reason,
                    metadata_json,
                ),
            )
            row = connection.execute(
                "SELECT * FROM ai_chat_lifecycle_audit_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return AiChatLifecycleAuditEventRow(**dict(row))

    def list_lifecycle_events(self, *, thread_id: str, user_id: str, limit: int = 100) -> list[AiChatLifecycleAuditEventRow]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ai_chat_lifecycle_audit_events
                WHERE thread_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (thread_id, user_id, limit),
            ).fetchall()
        return [AiChatLifecycleAuditEventRow(**dict(row)) for row in rows]

    def add_message(
        self,
        *,
        message_id: str,
        thread_id: str,
        user_id: str,
        role: str,
        content: str,
        request_id: str | None = None,
        tool_calls_json: str = "[]",
        signal_proposal_id: str | None = None,
        action_draft_id: str | None = None,
        context_revision: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost: float | None = None,
        latency_ms: int | None = None,
        metadata_json: str | None = None,
    ) -> AiChatMessageRow:
        thread = self.get_thread(thread_id, user_id=user_id)
        if thread is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_messages (
                    message_id,
                    thread_id,
                    role,
                    content,
                    request_id,
                    tool_calls_json,
                    signal_proposal_id,
                    action_draft_id,
                    context_revision,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost,
                    latency_ms,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    thread_id,
                    role,
                    content,
                    request_id,
                    tool_calls_json,
                    signal_proposal_id,
                    action_draft_id,
                    context_revision,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost,
                    latency_ms,
                    metadata_json or "{}",
                ),
            )
            connection.execute(
                """
                UPDATE ai_chat_threads
                SET updated_at = CURRENT_TIMESTAMP,
                    last_message_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ?
                """,
                (thread_id, user_id),
            )
        record = self.get_message(message_id=message_id, thread_id=thread_id, user_id=user_id)
        if record is None:
            raise LookupError(f"message not found after create: {message_id}")
        return record

    def get_message(self, *, message_id: str, thread_id: str, user_id: str) -> AiChatMessageRow | None:
        if self.get_thread(thread_id, user_id=user_id) is None:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM ai_chat_messages
                WHERE message_id = ? AND thread_id = ?
                """,
                (message_id, thread_id),
            ).fetchone()
        return None if row is None else AiChatMessageRow(**dict(row))

    def list_messages(self, *, thread_id: str, user_id: str, limit: int = 100) -> list[AiChatMessageRow]:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ai_chat_messages
                WHERE thread_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
        return [AiChatMessageRow(**dict(row)) for row in rows]

    def create_memory_summary(
        self,
        *,
        summary_id: str,
        thread_id: str,
        user_id: str,
        summary_text: str,
        source_message_count: int,
    ) -> AiChatMemorySummaryRow:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_memory_summaries (
                    summary_id,
                    thread_id,
                    summary_text,
                    source_message_count
                ) VALUES (?, ?, ?, ?)
                """,
                (summary_id, thread_id, summary_text, source_message_count),
            )
        record = self.get_latest_memory_summary(thread_id=thread_id, user_id=user_id)
        if record is None:
            raise LookupError(f"summary not found after create: {summary_id}")
        return record

    def get_latest_memory_summary(
        self,
        *,
        thread_id: str,
        user_id: str,
    ) -> AiChatMemorySummaryRow | None:
        if self.get_thread(thread_id, user_id=user_id) is None:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM ai_chat_memory_summaries
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (thread_id,),
            ).fetchone()
        return None if row is None else AiChatMemorySummaryRow(**dict(row))

    def upsert_pinned_fact(
        self,
        *,
        thread_id: str,
        user_id: str,
        fact_key: str,
        fact_value: str,
        source: str,
    ) -> AiChatPinnedFactRow:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_pinned_facts (
                    thread_id,
                    fact_key,
                    fact_value,
                    source
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(thread_id, fact_key)
                DO UPDATE SET
                    fact_value = excluded.fact_value,
                    source = excluded.source,
                    created_at = CURRENT_TIMESTAMP
                """,
                (thread_id, fact_key, fact_value, source),
            )
        rows = self.list_pinned_facts(thread_id=thread_id, user_id=user_id)
        for row in rows:
            if row.fact_key == fact_key:
                return row
        raise LookupError(f"pinned fact not found after upsert: {fact_key}")

    def list_pinned_facts(self, *, thread_id: str, user_id: str) -> list[AiChatPinnedFactRow]:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ai_chat_pinned_facts
                WHERE thread_id = ?
                ORDER BY created_at DESC, fact_id DESC
                """,
                (thread_id,),
            ).fetchall()
        return [AiChatPinnedFactRow(**dict(row)) for row in rows]

    def create_signal_proposal(
        self,
        *,
        proposal_id: str,
        thread_id: str,
        user_id: str,
        request_id: str | None,
        title: str,
        hypothesis: str,
        symbol: str,
        timeframe: str,
        direction: str,
        entry_logic: str,
        exit_logic: str,
        confidence: int,
        rationale: str,
        risk_note: str,
        status: str = "draft",
        watchlist_saved: bool = False,
        review_queue_saved: bool = False,
        non_executed_label: str = "non_executed_signal_proposal",
    ) -> AiChatSignalProposalRow:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_signal_proposals (
                    proposal_id,
                    thread_id,
                    user_id,
                    request_id,
                    title,
                    hypothesis,
                    symbol,
                    timeframe,
                    direction,
                    entry_logic,
                    exit_logic,
                    confidence,
                    rationale,
                    risk_note,
                    status,
                    watchlist_saved,
                    review_queue_saved,
                    non_executed_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    thread_id,
                    user_id,
                    request_id,
                    title,
                    hypothesis,
                    symbol,
                    timeframe,
                    direction,
                    entry_logic,
                    exit_logic,
                    confidence,
                    rationale,
                    risk_note,
                    status,
                    int(watchlist_saved),
                    int(review_queue_saved),
                    non_executed_label,
                ),
            )
        record = self.get_signal_proposal(proposal_id=proposal_id, user_id=user_id)
        if record is None:
            raise LookupError(f"signal proposal not found after create: {proposal_id}")
        return record

    def get_signal_proposal(self, *, proposal_id: str, user_id: str) -> AiChatSignalProposalRow | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM ai_chat_signal_proposals
                WHERE proposal_id = ? AND user_id = ?
                """,
                (proposal_id, user_id),
            ).fetchone()
        return None if row is None else AiChatSignalProposalRow(**dict(row))

    def list_signal_proposals(
        self,
        *,
        user_id: str,
        thread_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AiChatSignalProposalRow]:
        query = "SELECT * FROM ai_chat_signal_proposals WHERE user_id = ?"
        params: list[object] = [user_id]
        if thread_id is not None:
            query += " AND thread_id = ?"
            params.append(thread_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [AiChatSignalProposalRow(**dict(row)) for row in rows]

    def update_signal_proposal_state(
        self,
        *,
        proposal_id: str,
        user_id: str,
        status: str,
        watchlist_saved: bool | None = None,
        review_queue_saved: bool | None = None,
    ) -> AiChatSignalProposalRow:
        current = self.get_signal_proposal(proposal_id=proposal_id, user_id=user_id)
        if current is None:
            raise LookupError(f"signal proposal not found: {proposal_id}")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ai_chat_signal_proposals
                SET status = ?,
                    watchlist_saved = ?,
                    review_queue_saved = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE proposal_id = ? AND user_id = ?
                """,
                (
                    status,
                    int(current.watchlist_saved if watchlist_saved is None else watchlist_saved),
                    int(current.review_queue_saved if review_queue_saved is None else review_queue_saved),
                    proposal_id,
                    user_id,
                ),
            )
        updated = self.get_signal_proposal(proposal_id=proposal_id, user_id=user_id)
        if updated is None:
            raise LookupError(f"signal proposal not found after update: {proposal_id}")
        return updated

    def create_action_draft(
        self,
        *,
        draft_id: str,
        thread_id: str,
        user_id: str,
        request_id: str | None,
        draft_type: str,
        title: str,
        description: str,
        payload_json: str,
        risk_precheck_status: str,
        risk_precheck_notes: str,
        approval_id: str | None = None,
        status: str = "draft",
        requires_human_approval: bool = True,
        side_effect_status: str = "not_executed",
    ) -> AiChatActionDraftRow:
        if self.get_thread(thread_id, user_id=user_id) is None:
            raise LookupError(f"thread not found: {thread_id}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_chat_action_drafts (
                    draft_id,
                    thread_id,
                    user_id,
                    request_id,
                    draft_type,
                    title,
                    description,
                    payload_json,
                    risk_precheck_status,
                    risk_precheck_notes,
                    approval_id,
                    status,
                    requires_human_approval,
                    side_effect_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    thread_id,
                    user_id,
                    request_id,
                    draft_type,
                    title,
                    description,
                    payload_json,
                    risk_precheck_status,
                    risk_precheck_notes,
                    approval_id,
                    status,
                    int(requires_human_approval),
                    side_effect_status,
                ),
            )
        record = self.get_action_draft(draft_id=draft_id, user_id=user_id)
        if record is None:
            raise LookupError(f"action draft not found after create: {draft_id}")
        return record

    def get_action_draft(self, *, draft_id: str, user_id: str) -> AiChatActionDraftRow | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM ai_chat_action_drafts
                WHERE draft_id = ? AND user_id = ?
                """,
                (draft_id, user_id),
            ).fetchone()
        return None if row is None else AiChatActionDraftRow(**dict(row))

    def list_action_drafts(
        self,
        *,
        user_id: str,
        thread_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AiChatActionDraftRow]:
        query = "SELECT * FROM ai_chat_action_drafts WHERE user_id = ?"
        params: list[object] = [user_id]
        if thread_id is not None:
            query += " AND thread_id = ?"
            params.append(thread_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [AiChatActionDraftRow(**dict(row)) for row in rows]

    def update_action_draft(
        self,
        *,
        draft_id: str,
        user_id: str,
        status: str | None = None,
        approval_id: str | None = None,
        risk_precheck_status: str | None = None,
        risk_precheck_notes: str | None = None,
        side_effect_status: str | None = None,
        governed_workflow_id: str | None = None,
        execution_intent_id: str | None = None,
        execution_receipt_id: str | None = None,
    ) -> AiChatActionDraftRow:
        current = self.get_action_draft(draft_id=draft_id, user_id=user_id)
        if current is None:
            raise LookupError(f"action draft not found: {draft_id}")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ai_chat_action_drafts
                SET status = ?,
                    approval_id = ?,
                    risk_precheck_status = ?,
                    risk_precheck_notes = ?,
                    side_effect_status = ?,
                    governed_workflow_id = ?,
                    execution_intent_id = ?,
                    execution_receipt_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE draft_id = ? AND user_id = ?
                """,
                (
                    current.status if status is None else status,
                    current.approval_id if approval_id is None else approval_id,
                    current.risk_precheck_status if risk_precheck_status is None else risk_precheck_status,
                    current.risk_precheck_notes if risk_precheck_notes is None else risk_precheck_notes,
                    current.side_effect_status if side_effect_status is None else side_effect_status,
                    current.governed_workflow_id if governed_workflow_id is None else governed_workflow_id,
                    current.execution_intent_id if execution_intent_id is None else execution_intent_id,
                    current.execution_receipt_id if execution_receipt_id is None else execution_receipt_id,
                    draft_id,
                    user_id,
                ),
            )
        updated = self.get_action_draft(draft_id=draft_id, user_id=user_id)
        if updated is None:
            raise LookupError(f"action draft not found after update: {draft_id}")
        return updated
