"""Trajectory-level evaluation — step-by-step pass/fail tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from backend_retiring.agents.runtime.workflow_log import WorkflowExecutionLog


@dataclass(frozen=True)
class TrajectoryEvalResult:
    workflow_id: str
    total_steps: int
    passed_steps: int
    failed_steps: list[str]
    total_cost: float
    total_latency_ms: int
    overall_pass: bool


class TrajectoryEvaluator:
    """Evaluates workflow execution at the trajectory level.

    Checks each step's final_state and produces an overall
    pass/fail assessment with step-level detail.
    """

    def evaluate(
        self,
        workflow_log: WorkflowExecutionLog,
        expected_steps: list[str],
    ) -> TrajectoryEvalResult:
        """Evaluate a workflow log against expected steps."""
        passed = 0
        failed: list[str] = []

        for step_name in expected_steps:
            step_record = self._find_step(workflow_log, step_name)
            if step_record and step_record.final_state == "COMPLETED":
                passed += 1
            else:
                failed.append(step_name)

        return TrajectoryEvalResult(
            workflow_id=workflow_log.workflow_id,
            total_steps=len(expected_steps),
            passed_steps=passed,
            failed_steps=failed,
            total_cost=0.0,  # Would integrate with CostTracker
            total_latency_ms=workflow_log.total_latency_ms,
            overall_pass=len(failed) == 0,
        )

    @staticmethod
    def _find_step(log: WorkflowExecutionLog, step_name: str):
        """Find a step record by name."""
        for step in log.steps:
            if step.step_name == step_name:
                return step
        return None


def test_trajectory_eval_all_pass() -> None:
    """All steps completed should produce overall pass."""
    from datetime import datetime, timezone
    from backend_retiring.agents.runtime.workflow_log import WorkflowLogCollector, WorkflowExecutionLog

    now = datetime.now(timezone.utc)
    collector = WorkflowLogCollector("wf-001", "corr-001", "sequential")
    for name in ["research", "strategy", "compliance"]:
        collector.record_step(
            step_name=name, agent_name=f"{name}_agent",
            started_at=now, completed_at=now,
            input_payload={}, output_payload={"ok": True},
            final_state="COMPLETED", latency_ms=10,
        )
    log = collector.finalize("COMPLETED")

    evaluator = TrajectoryEvaluator()
    result = evaluator.evaluate(log, ["research", "strategy", "compliance"])

    assert result.overall_pass is True
    assert result.passed_steps == 3
    assert len(result.failed_steps) == 0


def test_trajectory_eval_partial_failure() -> None:
    """Failed steps should be tracked."""
    from datetime import datetime, timezone
    from backend_retiring.agents.runtime.workflow_log import WorkflowLogCollector

    now = datetime.now(timezone.utc)
    collector = WorkflowLogCollector("wf-002", "corr-002", "sequential")
    collector.record_step(
        step_name="research", agent_name="research_agent",
        started_at=now, completed_at=now,
        input_payload={}, output_payload={"ok": True},
        final_state="COMPLETED", latency_ms=10,
    )
    collector.record_step(
        step_name="strategy", agent_name="strategy_agent",
        started_at=now, completed_at=now,
        input_payload={}, output_payload={"error": "fail"},
        final_state="FAILED", latency_ms=5,
    )
    log = collector.finalize("FAILED")

    evaluator = TrajectoryEvaluator()
    result = evaluator.evaluate(log, ["research", "strategy", "compliance"])

    assert result.overall_pass is False
    assert result.passed_steps == 1
    assert "strategy" in result.failed_steps
    assert "compliance" in result.failed_steps
