from __future__ import annotations

from datetime import datetime, timezone

from backend_retiring.agents import (
    ADKRunResult,
    PromptRegistryRecord,
    PromptStatus,
    attach_prompt_provenance,
    attach_prompt_provenance_to_run_result,
)


def _record() -> PromptRegistryRecord:
    return PromptRegistryRecord(
        prompt_version_id="prompt_001",
        agent_name="orchestrator_agent",
        prompt_name="default_instruction",
        semantic_version="1.0.0",
        environment="paper",
        instruction_text="Decompose workflow goals into safe steps.",
        status=PromptStatus.ACTIVE,
        effective_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )


def test_attach_prompt_provenance_adds_hash_to_payload() -> None:
    record = _record()

    payload = attach_prompt_provenance({"workflow_id": "wf_001"}, record=record)

    assert payload["prompt_version_id"] == "prompt_001"
    assert payload["prompt_hash"] == record.content_hash


def test_attach_prompt_provenance_to_run_result_sets_prompt_metadata() -> None:
    record = _record()
    run_result = ADKRunResult(
        runner_name="agent-runtime",
        runtime_version="local-adk-wrapper-v1",
        agent_name="orchestrator_agent",
        workflow_id="wf_001",
        correlation_id="corr_001",
        session_id="sess_001",
        model="gemini-2.5-flash",
        prompt_version_id=None,
        prompt_hash=None,
        latency_ms=12,
        output_payload={"contract_type": "WorkflowPlan"},
        final_state="COMPLETED",
        tool_calls=(),
        token_usage={"prompt": 10, "completion": 6},
    )

    attached = attach_prompt_provenance_to_run_result(run_result, record=record)

    assert attached.prompt_version_id == "prompt_001"
    assert attached.prompt_hash == record.content_hash
