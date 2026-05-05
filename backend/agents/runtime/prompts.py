"""Prompt registry domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import hashlib

from haruquant.utils import logger

class PromptStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class PromptRegistryRecord:
    """Versioned prompt record for one agent/runtime surface."""

    prompt_version_id: str
    agent_name: str
    prompt_name: str
    semantic_version: str
    environment: str
    instruction_text: str
    status: PromptStatus
    effective_from: datetime
    deprecated_from: datetime | None = None
    changelog_summary: str = ""
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.prompt_version_id:
            raise ValueError("prompt_version_id must be non-empty")
        if not self.agent_name:
            raise ValueError("agent_name must be non-empty")
        if not self.prompt_name:
            raise ValueError("prompt_name must be non-empty")
        if not self.semantic_version:
            raise ValueError("semantic_version must be non-empty")
        if not self.environment:
            raise ValueError("environment must be non-empty")
        if not self.instruction_text.strip():
            raise ValueError("instruction_text must be non-empty")
        object.__setattr__(
            self,
            "content_hash",
            hashlib.sha256(self.instruction_text.encode("utf-8")).hexdigest(),
        )
