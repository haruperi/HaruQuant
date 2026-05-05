"""Prompt-hash provenance attachment helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from haruquant.utils import logger
from .prompts import PromptRegistryRecord
from .runner import ADKRunResult


@dataclass(frozen=True)
class PromptProvenance:
    prompt_version_id: str
    prompt_hash: str


def build_prompt_provenance(record: PromptRegistryRecord) -> PromptProvenance:
    return PromptProvenance(
        prompt_version_id=record.prompt_version_id,
        prompt_hash=record.content_hash,
    )


def attach_prompt_provenance(
    payload: dict[str, Any],
    *,
    record: PromptRegistryRecord,
) -> dict[str, Any]:
    attached = dict(payload)
    attached["prompt_version_id"] = record.prompt_version_id
    attached["prompt_hash"] = record.content_hash
    return attached


def attach_prompt_provenance_to_run_result(
    result: ADKRunResult,
    *,
    record: PromptRegistryRecord,
) -> ADKRunResult:
    return ADKRunResult(
        runner_name=result.runner_name,
        runtime_version=result.runtime_version,
        agent_name=result.agent_name,
        workflow_id=result.workflow_id,
        correlation_id=result.correlation_id,
        session_id=result.session_id,
        model=result.model,
        prompt_version_id=record.prompt_version_id,
        prompt_hash=record.content_hash,
        latency_ms=result.latency_ms,
        output_payload=dict(result.output_payload),
        final_state=result.final_state,
        tool_calls=result.tool_calls,
        token_usage=None if result.token_usage is None else dict(result.token_usage),
    )
