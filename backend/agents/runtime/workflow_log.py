"""Workflow execution log for observability and debugging.

Records every workflow step's inputs, outputs, timings, and status
so developers can trace execution, inspect failures, and replay
workflow runs for debugging.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WorkflowStepRecord:
    """Record of a single workflow step execution."""
    step_name: str
    agent_name: str
    started_at: datetime
    completed_at: datetime
    input_hash: str  # SHA-256 of input payload
    output_hash: Optional[str] = None
    final_state: str = "COMPLETED"
    latency_ms: int = 0
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    repair_attempted: bool = False
    repair_succeeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "final_state": self.final_state,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "error": self.error,
            "repair_attempted": self.repair_attempted,
            "repair_succeeded": self.repair_succeeded,
        }


@dataclass(frozen=True)
class WorkflowExecutionLog:
    """Complete execution log for a workflow run.

    Produced by every workflow execution. Queryable by workflow_id
    for debugging, replay, and audit.
    """
    workflow_id: str
    correlation_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pattern: str = "unknown"  # sequential | routing | parallel | evaluator_optimizer | orchestrator_workers
    steps: tuple[WorkflowStepRecord, ...] = ()
    final_state: str = "IN_PROGRESS"

    @property
    def total_latency_ms(self) -> int:
        return sum(s.latency_ms for s in self.steps)

    @property
    def total_tokens(self) -> int:
        total = 0
        for s in self.steps:
            if s.token_usage:
                total += s.token_usage.get("total_tokens", 0)
        return total

    @property
    def failed_steps(self) -> tuple[WorkflowStepRecord, ...]:
        return tuple(s for s in self.steps if s.final_state != "COMPLETED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "correlation_id": self.correlation_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pattern": self.pattern,
            "steps": [s.to_dict() for s in self.steps],
            "final_state": self.final_state,
            "total_latency_ms": self.total_latency_ms,
            "total_tokens": self.total_tokens,
            "failed_step_count": len(self.failed_steps),
        }


class WorkflowLogCollector:
    """Collects step records during workflow execution.

    Used internally by workflow runners to build a complete
    WorkflowExecutionLog as steps execute.
    """

    def __init__(
        self,
        workflow_id: str,
        correlation_id: str,
        pattern: str = "unknown",
    ) -> None:
        self._workflow_id = workflow_id
        self._correlation_id = correlation_id
        self._pattern = pattern
        self._started_at = datetime.now(timezone.utc)
        self._steps: List[WorkflowStepRecord] = []

    def record_step(
        self,
        step_name: str,
        agent_name: str,
        started_at: datetime,
        completed_at: datetime,
        input_payload: Dict[str, Any],
        output_payload: Optional[Dict[str, Any]],
        final_state: str,
        latency_ms: int,
        token_usage: Optional[Dict[str, int]] = None,
        error: Optional[str] = None,
        repair_attempted: bool = False,
        repair_succeeded: bool = False,
    ) -> None:
        """Record a completed step execution."""
        self._steps.append(WorkflowStepRecord(
            step_name=step_name,
            agent_name=agent_name,
            started_at=started_at,
            completed_at=completed_at,
            input_hash=_hash_dict(input_payload),
            output_hash=_hash_dict(output_payload) if output_payload else None,
            final_state=final_state,
            latency_ms=latency_ms,
            token_usage=token_usage,
            error=error,
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
        ))

    def finalize(self, final_state: str = "COMPLETED") -> WorkflowExecutionLog:
        """Produce the final WorkflowExecutionLog."""
        return WorkflowExecutionLog(
            workflow_id=self._workflow_id,
            correlation_id=self._correlation_id,
            started_at=self._started_at,
            completed_at=datetime.now(timezone.utc),
            pattern=self._pattern,
            steps=tuple(self._steps),
            final_state=final_state,
        )


def _hash_dict(data: Optional[Dict[str, Any]]) -> Optional[str]:
    if data is None:
        return None
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
