from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.agents import (
    PromptRegistryRecord,
    PromptRegistryService,
    PromptResolutionError,
    PromptStatus,
)


def test_prompt_registry_record_computes_content_hash() -> None:
    record = PromptRegistryRecord(
        prompt_version_id="prompt_001",
        agent_name="orchestrator_agent",
        prompt_name="default_instruction",
        semantic_version="1.0.0",
        environment="paper",
        instruction_text="Decompose workflow goals into safe steps.",
        status=PromptStatus.ACTIVE,
        effective_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )

    assert record.status == PromptStatus.ACTIVE
    assert len(record.content_hash) == 64


def test_prompt_registry_record_rejects_blank_instruction_text() -> None:
    with pytest.raises(ValueError, match="instruction_text must be non-empty"):
        PromptRegistryRecord(
            prompt_version_id="prompt_001",
            agent_name="orchestrator_agent",
            prompt_name="default_instruction",
            semantic_version="1.0.0",
            environment="paper",
            instruction_text="   ",
            status=PromptStatus.DRAFT,
            effective_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )


def test_prompt_registry_service_resolves_active_version_by_environment() -> None:
    records = [
        PromptRegistryRecord(
            prompt_version_id="prompt_001",
            agent_name="orchestrator_agent",
            prompt_name="default_instruction",
            semantic_version="1.0.0",
            environment="paper",
            instruction_text="Draft prompt",
            status=PromptStatus.DEPRECATED,
            effective_from=datetime(2026, 4, 8, tzinfo=timezone.utc),
            deprecated_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
        ),
        PromptRegistryRecord(
            prompt_version_id="prompt_002",
            agent_name="orchestrator_agent",
            prompt_name="default_instruction",
            semantic_version="1.1.0",
            environment="paper",
            instruction_text="Active prompt",
            status=PromptStatus.ACTIVE,
            effective_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
        ),
    ]
    service = PromptRegistryService(records)

    record = service.get_active_version(
        agent_name="orchestrator_agent",
        environment="paper",
        at=datetime(2026, 4, 9, 1, tzinfo=timezone.utc),
    )

    assert record.prompt_version_id == "prompt_002"


def test_prompt_registry_service_fails_when_no_active_prompt_exists() -> None:
    service = PromptRegistryService(())

    with pytest.raises(PromptResolutionError):
        service.get_active_version(
            agent_name="strategy_agent",
            environment="paper",
        )
