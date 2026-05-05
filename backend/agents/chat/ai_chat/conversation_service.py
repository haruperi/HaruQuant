"""Durable conversation service for AI chat threads, memory, and signal proposals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from haruquant.utils import generate_prefixed_id
from backend.data.database.repositories.ai_chat_repository import AiChatRepository
from backend.data.database.repositories.governance_repository import GovernanceRepository

from .models import (
    ActionDraftRecord,
    ConversationMessageRecord,
    ConversationThreadRecord,
    MemorySummary,
    PinnedFact,
    SignalProposalRecord,
)


DEFAULT_THREAD_TITLE = "New conversation"
SUMMARY_REFRESH_THRESHOLD = 6
SUMMARY_WINDOW = 8


class ConversationService:
    """Application service for AI chat storage and restoration."""

    def __init__(self, repository: AiChatRepository) -> None:
        self.repository = repository

    def create_thread(
        self,
        *,
        user_id: int | str,
        title: str | None = None,
        current_route: str | None = None,
        current_page_type: str | None = None,
        active_context_revision: str | None = None,
    ) -> ConversationThreadRecord:
        thread = self.repository.create_thread(
            thread_id=self._generate_identifier("thread"),
            user_id=str(user_id),
            title=(title or DEFAULT_THREAD_TITLE).strip() or DEFAULT_THREAD_TITLE,
            current_route=current_route,
            current_page_type=current_page_type,
            active_context_revision=active_context_revision,
        )
        return self._build_thread_record(thread_id=thread.thread_id, user_id=str(user_id))

    def list_threads(
        self,
        *,
        user_id: int | str,
        limit: int = 50,
        query: str | None = None,
    ) -> list[ConversationThreadRecord]:
        records = [
            self._thread_row_to_record(row)
            for row in self.repository.list_threads(user_id=str(user_id), limit=limit)
        ]
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return records
        return [
            record
            for record in records
            if normalized_query in record.title.lower()
            or normalized_query in (record.current_route or "").lower()
            or normalized_query in (record.current_page_type or "").lower()
        ]

    def get_thread(self, *, user_id: int | str, thread_id: str) -> ConversationThreadRecord:
        return self._build_thread_record(thread_id=thread_id, user_id=str(user_id))

    def rename_thread(
        self,
        *,
        user_id: int | str,
        thread_id: str,
        title: str,
    ) -> ConversationThreadRecord:
        normalized_title = " ".join(title.split()).strip()
        if not normalized_title:
            raise ValueError("thread title cannot be empty")
        self.repository.update_thread_title(
            thread_id=thread_id,
            user_id=str(user_id),
            title=self._truncate_text(normalized_title, 128),
        )
        return self._build_thread_record(thread_id=thread_id, user_id=str(user_id))

    def delete_thread(self, *, user_id: int | str, thread_id: str) -> bool:
        return self.repository.soft_delete_thread(thread_id=thread_id, user_id=str(user_id))

    def update_thread_context(
        self,
        *,
        user_id: int | str,
        thread_id: str,
        current_route: str | None,
        current_page_type: str | None,
        active_context_revision: str | None,
    ) -> ConversationThreadRecord:
        self.repository.update_thread_context(
            thread_id=thread_id,
            user_id=str(user_id),
            current_route=current_route,
            current_page_type=current_page_type,
            active_context_revision=active_context_revision,
        )
        return self._build_thread_record(thread_id=thread_id, user_id=str(user_id))

    def add_message(
        self,
        *,
        user_id: int | str,
        thread_id: str,
        role: str,
        content: str,
        request_id: str | None = None,
        context_revision: str | None = None,
        tool_calls: list[str] | None = None,
        signal_proposal_id: str | None = None,
        action_draft_id: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost: float | None = None,
        latency_ms: int | None = None,
        metadata: dict | None = None,
    ) -> ConversationMessageRecord:
        user_key = str(user_id)
        normalized_content = content.strip()
        message = self.repository.add_message(
            message_id=self._generate_identifier("msg"),
            thread_id=thread_id,
            user_id=user_key,
            role=role,
            content=normalized_content,
            request_id=request_id,
            context_revision=context_revision,
            tool_calls_json=json.dumps(tool_calls or []),
            signal_proposal_id=signal_proposal_id,
            action_draft_id=action_draft_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            metadata_json=json.dumps(metadata or {}),
        )
        self._promote_title_if_needed(
            user_id=user_key,
            thread_id=thread_id,
            role=role,
            content=normalized_content,
        )
        self._refresh_memory_summary_if_needed(user_id=user_key, thread_id=thread_id)
        return self._message_row_to_record(message)

    def refresh_memory_summary(self, *, user_id: int | str, thread_id: str) -> MemorySummary:
        messages = self.repository.list_messages(thread_id=thread_id, user_id=str(user_id), limit=100)
        if not messages:
            raise LookupError(f"thread has no messages: {thread_id}")

        selected = messages[-SUMMARY_WINDOW:]
        lines = [
            f"{message.role.title()}: {self._truncate_text(message.content, 180)}"
            for message in selected
        ]
        summary = self.repository.create_memory_summary(
            summary_id=self._generate_identifier("summary"),
            thread_id=thread_id,
            user_id=str(user_id),
            summary_text="\n".join(lines),
            source_message_count=len(messages),
        )
        return MemorySummary(
            summary_text=summary.summary_text,
            generated_at=summary.created_at,
            source_message_count=summary.source_message_count,
        )

    def upsert_pinned_fact(
        self,
        *,
        user_id: int | str,
        thread_id: str,
        key: str,
        value: str,
        source: str,
    ) -> PinnedFact:
        fact = self.repository.upsert_pinned_fact(
            thread_id=thread_id,
            user_id=str(user_id),
            fact_key=key,
            fact_value=value,
            source=source,
        )
        return PinnedFact(key=fact.fact_key, value=fact.fact_value, source=fact.source)

    def create_signal_proposal(
        self,
        *,
        user_id: int | str,
        thread_id: str,
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
    ) -> SignalProposalRecord:
        proposal = self.repository.create_signal_proposal(
            proposal_id=generate_prefixed_id("sig"),
            thread_id=thread_id,
            user_id=str(user_id),
            request_id=request_id,
            title=title,
            hypothesis=hypothesis,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_logic=entry_logic,
            exit_logic=exit_logic,
            confidence=confidence,
            rationale=rationale,
            risk_note=risk_note,
        )
        return self._signal_proposal_row_to_record(proposal)

    def get_signal_proposal(self, *, user_id: int | str, proposal_id: str) -> SignalProposalRecord:
        proposal = self.repository.get_signal_proposal(proposal_id=proposal_id, user_id=str(user_id))
        if proposal is None:
            raise LookupError(f"signal proposal not found: {proposal_id}")
        return self._signal_proposal_row_to_record(proposal)

    def create_action_draft(
        self,
        *,
        user_id: int | str,
        thread_id: str,
        request_id: str | None,
        draft_type: str,
        title: str,
        description: str,
        payload: dict,
        risk_precheck_status: str,
        risk_precheck_notes: str,
        requires_human_approval: bool = True,
        side_effect_status: str = "not_executed",
    ) -> ActionDraftRecord:
        draft = self.repository.create_action_draft(
            draft_id=generate_prefixed_id("draft"),
            thread_id=thread_id,
            user_id=str(user_id),
            request_id=request_id,
            draft_type=draft_type,
            title=title,
            description=description,
            payload_json=json.dumps(payload),
            risk_precheck_status=risk_precheck_status,
            risk_precheck_notes=risk_precheck_notes,
            requires_human_approval=requires_human_approval,
            side_effect_status=side_effect_status,
        )
        return self._action_draft_row_to_record(draft)

    def get_action_draft(self, *, user_id: int | str, draft_id: str) -> ActionDraftRecord:
        draft = self.repository.get_action_draft(draft_id=draft_id, user_id=str(user_id))
        if draft is None:
            raise LookupError(f"action draft not found: {draft_id}")
        draft = self._refresh_action_draft_approval_state(user_id=str(user_id), row=draft)
        return self._action_draft_row_to_record(draft)

    def list_action_drafts(
        self,
        *,
        user_id: int | str,
        thread_id: str | None = None,
        status: str | None = None,
    ) -> list[ActionDraftRecord]:
        return [
            self._action_draft_row_to_record(row)
            for row in (
                self._refresh_action_draft_approval_state(user_id=str(user_id), row=row)
                for row in self.repository.list_action_drafts(
                    user_id=str(user_id),
                    thread_id=thread_id,
                    status=status,
                )
            )
        ]

    def request_action_draft_approval(
        self,
        *,
        user_id: int | str,
        draft_id: str,
        actor_type: str = "user",
    ) -> ActionDraftRecord:
        draft = self.get_action_draft(user_id=user_id, draft_id=draft_id)
        if draft.approval_id:
            return draft
        governance = GovernanceRepository(self.repository.db_path)
        expiry = datetime.now(timezone.utc) + timedelta(days=1)
        approval = governance.create_approval(
            approval_id=generate_prefixed_id("approval"),
            action_type=f"ai_chat.{draft.draft_type}",
            target_ref_type="ai_chat_action_draft",
            target_ref_id=draft.draft_id,
            required_count=1,
            state="PENDING",
            created_by_actor_type=actor_type,
            created_by_actor_id=str(user_id),
            expires_at=expiry.isoformat(),
            metadata_json=json.dumps(
                {
                    "thread_id": draft.thread_id,
                    "draft_type": draft.draft_type,
                    "risk_precheck_status": draft.risk_precheck_status,
                    "side_effect_status": draft.side_effect_status,
                }
            ),
        )
        updated = self.repository.update_action_draft(
            draft_id=draft_id,
            user_id=str(user_id),
            approval_id=approval.approval_id,
            status="approval_requested",
        )
        return self._action_draft_row_to_record(updated)

    def list_signal_proposals(
        self,
        *,
        user_id: int | str,
        thread_id: str | None = None,
        status: str | None = None,
    ) -> list[SignalProposalRecord]:
        return [
            self._signal_proposal_row_to_record(row)
            for row in self.repository.list_signal_proposals(
                user_id=str(user_id),
                thread_id=thread_id,
                status=status,
            )
        ]

    def save_signal_proposal_to_watchlist(
        self,
        *,
        user_id: int | str,
        proposal_id: str,
    ) -> SignalProposalRecord:
        proposal = self.repository.update_signal_proposal_state(
            proposal_id=proposal_id,
            user_id=str(user_id),
            status="watchlist",
            watchlist_saved=True,
        )
        return self._signal_proposal_row_to_record(proposal)

    def queue_signal_proposal_for_review(
        self,
        *,
        user_id: int | str,
        proposal_id: str,
    ) -> SignalProposalRecord:
        proposal = self.repository.update_signal_proposal_state(
            proposal_id=proposal_id,
            user_id=str(user_id),
            status="review_queue",
            review_queue_saved=True,
        )
        return self._signal_proposal_row_to_record(proposal)

    def get_last_user_prompt(self, *, user_id: int | str, thread_id: str) -> ConversationMessageRecord:
        thread = self._build_thread_record(thread_id=thread_id, user_id=str(user_id))
        for message in reversed(thread.messages):
            if message.role == "user":
                return message
        raise LookupError(f"thread has no user message to regenerate: {thread_id}")

    def export_thread(self, *, user_id: int | str, thread_id: str, format: str = "markdown") -> dict[str, object]:
        thread = self._build_thread_record(thread_id=thread_id, user_id=str(user_id))
        payload = thread.model_dump(mode="json")
        if format == "json":
            return {
                "thread_id": thread.thread_id,
                "title": thread.title,
                "format": "json",
                "content": payload,
            }
        if format != "markdown":
            raise ValueError(f"unsupported export format: {format}")
        lines = [
            f"# {thread.title}",
            "",
            f"- Thread ID: `{thread.thread_id}`",
            f"- Route: `{thread.current_route or 'unknown'}`",
            f"- Page Type: `{thread.current_page_type or 'generic'}`",
            f"- Updated: `{thread.updated_at.isoformat()}`",
            "",
        ]
        if thread.memory_summary is not None:
            lines.extend(
                [
                    "## Memory Summary",
                    "",
                    thread.memory_summary.summary_text,
                    "",
                ]
            )
        signal_proposals = self.list_signal_proposals(user_id=user_id, thread_id=thread_id)
        action_drafts = self.list_action_drafts(user_id=user_id, thread_id=thread_id)
        if signal_proposals:
            lines.extend(["## Signal Proposals", ""])
            for proposal in signal_proposals:
                lines.extend(
                    [
                        f"- {proposal.title} [{proposal.status}] {proposal.symbol} {proposal.direction} {proposal.timeframe}",
                        f"  confidence={proposal.confidence} risk_note={proposal.risk_note}",
                    ]
                )
            lines.append("")
        if action_drafts:
            lines.extend(["## Action Drafts", ""])
            for draft in action_drafts:
                lines.extend(
                    [
                        f"- {draft.title} [{draft.status}] {draft.draft_type}",
                        f"  risk_precheck={draft.risk_precheck_status} approval_id={draft.approval_id or 'pending'} side_effect_status={draft.side_effect_status}",
                    ]
                )
            lines.append("")
        for message in thread.messages:
            lines.extend(
                [
                    f"## {message.role.title()}",
                    "",
                    message.content,
                    "",
                ]
            )
            if message.tool_calls:
                lines.extend(
                    [
                        f"Tools used: {', '.join(message.tool_calls)}",
                        "",
                    ]
                )
            if message.signal_proposal_id:
                lines.extend(
                    [
                        f"Signal proposal: {message.signal_proposal_id}",
                        "",
                    ]
                )
            if message.action_draft_id:
                lines.extend(
                    [
                        f"Action draft: {message.action_draft_id}",
                        "",
                    ]
                )
        return {
            "thread_id": thread.thread_id,
            "title": thread.title,
            "format": "markdown",
            "content": "\n".join(lines).strip(),
        }

    def _build_thread_record(self, *, thread_id: str, user_id: str) -> ConversationThreadRecord:
        thread = self.repository.get_thread(thread_id, user_id=user_id)
        if thread is None:
            raise LookupError(f"thread not found: {thread_id}")
        latest_summary = self.repository.get_latest_memory_summary(thread_id=thread_id, user_id=user_id)
        pinned_facts = self.repository.list_pinned_facts(thread_id=thread_id, user_id=user_id)
        messages = self.repository.list_messages(thread_id=thread_id, user_id=user_id, limit=200)
        thread_payload = self._thread_row_to_record(thread).model_dump(
            exclude={"memory_summary", "pinned_facts", "messages"},
        )
        return ConversationThreadRecord(
            **thread_payload,
            memory_summary=(
                MemorySummary(
                    summary_text=latest_summary.summary_text,
                    generated_at=latest_summary.created_at,
                    source_message_count=latest_summary.source_message_count,
                )
                if latest_summary is not None
                else None
            ),
            pinned_facts=[
                PinnedFact(key=fact.fact_key, value=fact.fact_value, source=fact.source)
                for fact in pinned_facts
            ],
            messages=[self._message_row_to_record(message) for message in messages],
        )

    def _thread_row_to_record(self, row: object) -> ConversationThreadRecord:
        return ConversationThreadRecord(
            thread_id=row.thread_id,
            user_id=row.user_id,
            title=row.title,
            status=row.status,
            retention_class=row.retention_class,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_message_at=row.last_message_at,
            active_context_revision=row.active_context_revision,
            current_route=row.current_route,
            current_page_type=row.current_page_type,
        )

    def _message_row_to_record(self, row: object) -> ConversationMessageRecord:
        return ConversationMessageRecord(
            message_id=row.message_id,
            thread_id=row.thread_id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
            request_id=row.request_id,
            tool_calls=json.loads(row.tool_calls_json),
            signal_proposal_id=row.signal_proposal_id,
            action_draft_id=row.action_draft_id,
            context_revision=row.context_revision,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            total_tokens=row.total_tokens,
            cost=row.cost,
            latency_ms=row.latency_ms,
            metadata=json.loads(row.metadata_json or "{}"),
        )

    @staticmethod
    def _signal_proposal_row_to_record(row: object) -> SignalProposalRecord:
        return SignalProposalRecord(
            proposal_id=row.proposal_id,
            thread_id=row.thread_id,
            user_id=row.user_id,
            request_id=row.request_id,
            title=row.title,
            hypothesis=row.hypothesis,
            symbol=row.symbol,
            timeframe=row.timeframe,
            direction=row.direction,
            entry_logic=row.entry_logic,
            exit_logic=row.exit_logic,
            confidence=row.confidence,
            rationale=row.rationale,
            risk_note=row.risk_note,
            status=row.status,
            watchlist_saved=bool(row.watchlist_saved),
            review_queue_saved=bool(row.review_queue_saved),
            non_executed_label=row.non_executed_label,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _action_draft_row_to_record(row: object) -> ActionDraftRecord:
        return ActionDraftRecord(
            draft_id=row.draft_id,
            thread_id=row.thread_id,
            user_id=row.user_id,
            request_id=row.request_id,
            draft_type=row.draft_type,
            title=row.title,
            description=row.description,
            payload=json.loads(row.payload_json),
            risk_precheck_status=row.risk_precheck_status,
            risk_precheck_notes=row.risk_precheck_notes,
            approval_id=row.approval_id,
            status=row.status,
            requires_human_approval=bool(row.requires_human_approval),
            side_effect_status=row.side_effect_status,
            governed_workflow_id=row.governed_workflow_id,
            execution_intent_id=row.execution_intent_id,
            execution_receipt_id=row.execution_receipt_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _refresh_action_draft_approval_state(self, *, user_id: str, row: object):
        if not row.approval_id:
            return row
        governance = GovernanceRepository(self.repository.db_path)
        approval = governance.get_approval(row.approval_id)
        if approval is None:
            return row
        mapped_status = row.status
        if approval.state == "APPROVED":
            mapped_status = "approved"
        elif approval.state == "REJECTED":
            mapped_status = "rejected"
        elif approval.state in {"PENDING", "PARTIALLY_APPROVED"}:
            mapped_status = "approval_requested"
        if mapped_status == row.status:
            return row
        return self.repository.update_action_draft(
            draft_id=row.draft_id,
            user_id=user_id,
            status=mapped_status,
        )

    def _promote_title_if_needed(
        self,
        *,
        user_id: str,
        thread_id: str,
        role: str,
        content: str,
    ) -> None:
        if role != "user":
            return
        thread = self.repository.get_thread(thread_id, user_id=user_id)
        if thread is None or thread.title != DEFAULT_THREAD_TITLE:
            return
        self.repository.update_thread_title(
            thread_id=thread_id,
            user_id=user_id,
            title=self._make_title_from_prompt(content),
        )

    def _refresh_memory_summary_if_needed(self, *, user_id: str, thread_id: str) -> None:
        messages = self.repository.list_messages(thread_id=thread_id, user_id=user_id, limit=100)
        if len(messages) < SUMMARY_REFRESH_THRESHOLD:
            return
        self.refresh_memory_summary(user_id=user_id, thread_id=thread_id)

    @staticmethod
    def _generate_identifier(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    @staticmethod
    def _truncate_text(value: str, limit: int) -> str:
        trimmed = " ".join(value.split())
        if len(trimmed) <= limit:
            return trimmed
        return f"{trimmed[: limit - 3].rstrip()}..."

    def _make_title_from_prompt(self, content: str) -> str:
        single_line = " ".join(content.split())
        if not single_line:
            return DEFAULT_THREAD_TITLE
        return self._truncate_text(single_line, 64)
