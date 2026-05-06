"""Retention lifecycle policy for AI chat conversations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from data.database.repositories.ai_chat_repository import AiChatRepository, AiChatThreadRow


RETENTION_PERIODS = {
    "ephemeral": timedelta(days=30),
    "standard": timedelta(days=730),
    "regulated": timedelta(days=2555),
}
ARCHIVE_AFTER = {
    "standard": timedelta(days=365),
    "regulated": timedelta(days=365),
}
PURGE_AFTER_DELETE = timedelta(days=30)

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{12,})['\"]?"), r"\1=[redacted]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[redacted-email]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[redacted-number]"),
)


@dataclass(frozen=True)
class RetentionDecision:
    action: str
    thread_id: str
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_sqlite_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat(sep=" ")


def redact_sensitive_text(content: str) -> str:
    redacted = content
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def retention_expiry_for(retention_class: str, now: datetime | None = None) -> str | None:
    period = RETENTION_PERIODS.get(retention_class)
    if period is None:
        return None
    return to_sqlite_timestamp((now or utc_now()) + period)


def purge_after_for(retention_class: str, now: datetime | None = None) -> str | None:
    if retention_class in {"regulated", "legal_hold"}:
        return None
    return retention_expiry_for(retention_class, now)


class ConversationRetentionService:
    """Applies lifecycle, archival, legal hold, and purge rules."""

    def __init__(self, repository: AiChatRepository) -> None:
        self.repository = repository

    def initialize_thread_policy(self, *, thread_id: str, user_id: str, retention_class: str = "standard") -> AiChatThreadRow:
        return self.repository.update_thread_retention(
            thread_id=thread_id,
            user_id=user_id,
            retention_class=retention_class,
            retention_expires_at=retention_expiry_for(retention_class),
            purge_after=purge_after_for(retention_class),
            reason=f"Initialized {retention_class} retention policy.",
        )

    def mark_regulated(self, *, thread_id: str, user_id: str, reason: str) -> AiChatThreadRow:
        current = self.repository.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None:
            raise LookupError(f"thread not found: {thread_id}")
        if current.retention_class in {"regulated", "legal_hold"}:
            return current
        return self.repository.update_thread_retention(
            thread_id=thread_id,
            user_id=user_id,
            retention_class="regulated",
            retention_expires_at=retention_expiry_for("regulated"),
            purge_after=None,
            reason=reason,
        )

    def set_ephemeral(self, *, thread_id: str, user_id: str, reason: str = "User requested ephemeral retention.") -> AiChatThreadRow:
        current = self.repository.get_thread(thread_id, user_id=user_id, include_deleted=True)
        if current is None:
            raise LookupError(f"thread not found: {thread_id}")
        if current.retention_class in {"regulated", "legal_hold"}:
            return current
        return self.repository.update_thread_retention(
            thread_id=thread_id,
            user_id=user_id,
            retention_class="ephemeral",
            retention_expires_at=retention_expiry_for("ephemeral"),
            purge_after=purge_after_for("ephemeral"),
            reason=reason,
        )

    def apply_legal_hold(
        self,
        *,
        thread_id: str,
        user_id: str,
        actor_id: str,
        reason: str,
        until: str | None = None,
    ) -> AiChatThreadRow:
        return self.repository.update_thread_retention(
            thread_id=thread_id,
            user_id=user_id,
            retention_class="legal_hold",
            retention_expires_at=None,
            purge_after=None,
            legal_hold_until=until,
            legal_hold_reason=reason,
            actor_id=actor_id,
            reason=reason,
        )

    def release_legal_hold(self, *, thread_id: str, user_id: str, actor_id: str, reason: str) -> AiChatThreadRow:
        return self.repository.update_thread_retention(
            thread_id=thread_id,
            user_id=user_id,
            retention_class="regulated",
            retention_expires_at=retention_expiry_for("regulated"),
            purge_after=None,
            legal_hold_until=None,
            legal_hold_reason=None,
            actor_id=actor_id,
            reason=reason,
        )

    def run_lifecycle(self, *, now: datetime | None = None, limit: int = 200) -> list[RetentionDecision]:
        current_time = now or utc_now()
        now_text = to_sqlite_timestamp(current_time)
        decisions: list[RetentionDecision] = []
        for thread in self.repository.list_threads_due_for_lifecycle(now=now_text, limit=limit):
            if thread.retention_class == "legal_hold":
                decisions.append(RetentionDecision("skipped", thread.thread_id, "Legal hold blocks lifecycle action."))
                continue

            if thread.status == "deleted" and thread.purge_after and thread.purge_after <= now_text:
                purged = self.repository.purge_thread(
                    thread_id=thread.thread_id,
                    user_id=thread.user_id,
                    actor_id="retention-job",
                    reason="Deleted conversation reached purge date.",
                )
                decisions.append(RetentionDecision("purged" if purged else "skipped", thread.thread_id, "Deleted purge review."))
                continue

            if thread.retention_class == "ephemeral" and thread.retention_expires_at and thread.retention_expires_at <= now_text:
                self.repository.soft_delete_thread(thread_id=thread.thread_id, user_id=thread.user_id)
                purged = self.repository.purge_thread(
                    thread_id=thread.thread_id,
                    user_id=thread.user_id,
                    actor_id="retention-job",
                    reason="Ephemeral conversation expired.",
                )
                decisions.append(RetentionDecision("purged" if purged else "deleted", thread.thread_id, "Ephemeral retention expired."))
                continue

            archive_after = ARCHIVE_AFTER.get(thread.retention_class)
            if thread.status == "active" and archive_after is not None and thread.last_message_at:
                try:
                    last_message = datetime.fromisoformat(thread.last_message_at.replace("Z", "+00:00"))
                except ValueError:
                    last_message = current_time
                if current_time - last_message >= archive_after:
                    self.repository.archive_thread(
                        thread_id=thread.thread_id,
                        user_id=thread.user_id,
                        actor_id="retention-job",
                        reason=f"{thread.retention_class} conversation inactive past archive threshold.",
                    )
                    decisions.append(RetentionDecision("archived", thread.thread_id, "Inactive conversation archived."))
        return decisions

