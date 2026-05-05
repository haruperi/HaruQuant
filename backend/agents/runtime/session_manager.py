"""Workflow-scoped session state manager abstraction."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from services.utils.logger import logger
from services.utils import generate_id


class SessionState(StrEnum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class AgentSession:
    """Ephemeral session state for one operator or workflow context."""

    session_id: str
    state: SessionState
    created_at: datetime
    updated_at: datetime
    workflow_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """In-memory session manager until a Redis-backed store is added."""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}

    def create_session(
        self,
        *,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AgentSession:
        now = datetime.now(UTC)
        session = AgentSession(
            session_id=session_id or generate_id("session"),
            state=SessionState.CREATED,
            created_at=now,
            updated_at=now,
            metadata={} if metadata is None else dict(metadata),
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)

    def activate_session(self, session_id: str) -> AgentSession:
        session = self._require_session(session_id)
        updated = replace(
            session,
            state=SessionState.ACTIVE,
            updated_at=datetime.now(UTC),
        )
        self._sessions[session_id] = updated
        return updated

    def bind_workflow(self, *, session_id: str, workflow_id: str) -> AgentSession:
        session = self._require_session(session_id)
        workflow_ids = session.workflow_ids
        if workflow_id not in workflow_ids:
            workflow_ids = (*workflow_ids, workflow_id)
        updated = replace(
            session,
            workflow_ids=workflow_ids,
            updated_at=datetime.now(UTC),
        )
        self._sessions[session_id] = updated
        return updated

    def close_session(self, session_id: str) -> AgentSession:
        session = self._require_session(session_id)
        updated = replace(
            session,
            state=SessionState.CLOSED,
            updated_at=datetime.now(UTC),
        )
        self._sessions[session_id] = updated
        return updated

    def _require_session(self, session_id: str) -> AgentSession:
        session = self.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        return session
