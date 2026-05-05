"""Prompt version resolution service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from services.utils.logger import logger
from .prompts import PromptRegistryRecord, PromptStatus


class PromptResolutionError(LookupError):
    """Raised when a prompt version cannot be resolved."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PromptRegistryService:
    """In-memory prompt registry with environment-aware version resolution."""

    def __init__(self, records: Iterable[PromptRegistryRecord]):
        self._by_agent_name: dict[str, list[PromptRegistryRecord]] = defaultdict(list)
        for record in records:
            self._by_agent_name[record.agent_name].append(record)
        for record_list in self._by_agent_name.values():
            record_list.sort(key=lambda item: (item.environment, item.effective_from, item.semantic_version))

    def list_versions(self, agent_name: str, *, environment: str | None = None) -> list[PromptRegistryRecord]:
        records = list(self._by_agent_name.get(agent_name, []))
        if environment is None:
            return records
        return [record for record in records if record.environment == environment]

    def get_version(
        self,
        *,
        agent_name: str,
        prompt_version_id: str,
    ) -> PromptRegistryRecord:
        for record in self._by_agent_name.get(agent_name, []):
            if record.prompt_version_id == prompt_version_id:
                return record
        raise PromptResolutionError(
            f"No prompt version '{prompt_version_id}' found for agent '{agent_name}'."
        )

    def get_active_version(
        self,
        *,
        agent_name: str,
        environment: str,
        at: datetime | None = None,
    ) -> PromptRegistryRecord:
        moment = at or _utc_now()
        candidates = [
            record
            for record in self._by_agent_name.get(agent_name, [])
            if record.environment == environment
            and record.status == PromptStatus.ACTIVE
            and record.effective_from <= moment
            and (record.deprecated_from is None or record.deprecated_from > moment)
        ]
        if not candidates:
            raise PromptResolutionError(
                f"No active prompt found for agent '{agent_name}' in environment '{environment}'."
            )
        return candidates[-1]
