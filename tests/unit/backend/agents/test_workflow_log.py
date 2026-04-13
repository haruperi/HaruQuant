"""Unit tests for WorkflowExecutionLog."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from backend.agents.runtime.workflow_log import (
    WorkflowExecutionLog,
    WorkflowLogCollector,
    WorkflowStepRecord,
)


def test_workflow_log_collector_records_steps() -> None:
    collector = WorkflowLogCollector("wf-001", "corr-001", "sequential")

    started = datetime.now(timezone.utc)
    time.sleep(0.01)
    completed = datetime.now(timezone.utc)

    collector.record_step(
        step_name="research",
        agent_name="research_agent",
        started_at=started,
        completed_at=completed,
        input_payload={"query": "EURUSD"},
        output_payload={"result": "bullish"},
        final_state="COMPLETED",
        latency_ms=10,
        token_usage={"total_tokens": 150},
    )

    log = collector.finalize("COMPLETED")
    assert log.workflow_id == "wf-001"
    assert log.pattern == "sequential"
    assert len(log.steps) == 1
    assert log.steps[0].step_name == "research"
    assert log.steps[0].agent_name == "research_agent"
    assert log.final_state == "COMPLETED"


def test_workflow_log_tracks_failed_steps() -> None:
    collector = WorkflowLogCollector("wf-002", "corr-002", "sequential")
    now = datetime.now(timezone.utc)

    collector.record_step(
        step_name="step_one",
        agent_name="strategy_agent",
        started_at=now,
        completed_at=now,
        input_payload={},
        output_payload=None,
        final_state="VALIDATION_FAILED",
        latency_ms=5,
        error="Wrong contract type",
    )

    log = collector.finalize("FAILED")
    assert len(log.failed_steps) == 1
    assert log.failed_steps[0].error == "Wrong contract type"


def test_workflow_log_summarizes_totals() -> None:
    collector = WorkflowLogCollector("wf-003", "corr-003", "parallel")
    now = datetime.now(timezone.utc)

    for i in range(3):
        collector.record_step(
            step_name=f"task_{i}",
            agent_name=f"agent_{i}",
            started_at=now,
            completed_at=now,
            input_payload={},
            output_payload={"result": i},
            final_state="COMPLETED",
            latency_ms=10 * (i + 1),
            token_usage={"total_tokens": 100 * (i + 1)},
        )

    log = collector.finalize("COMPLETED")
    assert log.total_latency_ms == 60  # 10 + 20 + 30
    assert log.total_tokens == 600  # 100 + 200 + 300
    assert len(log.failed_steps) == 0


def test_workflow_step_record_to_dict() -> None:
    now = datetime.now(timezone.utc)
    record = WorkflowStepRecord(
        step_name="test",
        agent_name="test_agent",
        started_at=now,
        completed_at=now,
        input_hash="abc123",
        final_state="COMPLETED",
        latency_ms=5,
    )
    d = record.to_dict()
    assert d["step_name"] == "test"
    assert d["input_hash"] == "abc123"
    assert "started_at" in d


def test_workflow_execution_log_to_dict() -> None:
    now = datetime.now(timezone.utc)
    log = WorkflowExecutionLog(
        workflow_id="wf-test",
        correlation_id="corr-test",
        started_at=now,
        completed_at=now,
        pattern="sequential",
        steps=(),
        final_state="COMPLETED",
    )
    d = log.to_dict()
    assert d["workflow_id"] == "wf-test"
    assert d["pattern"] == "sequential"
    assert d["total_latency_ms"] == 0
    assert d["failed_step_count"] == 0
