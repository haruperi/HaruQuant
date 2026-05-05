"""Validation helpers for artifacts produced by AI chat tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class ChatArtifactValidation:
    valid: bool
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"valid": self.valid, "issues": list(self.issues)}


@dataclass(frozen=True)
class ChatArtifact:
    artifact_type: str
    payload: dict[str, object]
    status: str = "draft"
    tool_id: str | None = None
    agent_name: str | None = None
    thread_id: str | None = None
    message_id: str | None = None
    artifact_id: str = field(default_factory=lambda: f"chat_artifact_{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation: ChatArtifactValidation = field(default_factory=lambda: ChatArtifactValidation(valid=True))

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "tool_id": self.tool_id,
            "agent_name": self.agent_name,
            "thread_id": self.thread_id,
            "message_id": self.message_id,
            "status": self.status,
            "payload": self.payload,
            "validation": self.validation.to_dict(),
            "created_at": self.created_at.isoformat(),
        }


class ChatArtifactService:
    """Create schema-shaped chat artifacts with lightweight validation.

    Persistence is intentionally left to the conversation/message metadata path
    until the product needs a separate artifact table.
    """

    VALID_STATUSES = {"draft", "validated", "needs_review", "rejected", "materialized"}

    def build_artifact(
        self,
        *,
        artifact_type: str,
        payload: dict[str, object],
        tool_id: str | None = None,
        agent_name: str | None = None,
        thread_id: str | None = None,
        message_id: str | None = None,
        status: str = "draft",
    ) -> ChatArtifact:
        issues: list[str] = []
        if not artifact_type.strip():
            issues.append("artifact_type_required")
        if not isinstance(payload, dict) or not payload:
            issues.append("payload_required")
        if status not in self.VALID_STATUSES:
            issues.append(f"invalid_status:{status}")

        return ChatArtifact(
            artifact_type=artifact_type,
            payload=payload if isinstance(payload, dict) else {},
            tool_id=tool_id,
            agent_name=agent_name,
            thread_id=thread_id,
            message_id=message_id,
            status=status if status in self.VALID_STATUSES else "needs_review",
            validation=ChatArtifactValidation(valid=not issues, issues=tuple(issues)),
        )


__all__ = ["ChatArtifact", "ChatArtifactService", "ChatArtifactValidation"]
