"""Runtime observability helpers for trajectory log persistence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from apps.core.ids import generate_prefixed_id
from backend.contracts.serialization import canonical_json_dumps
from backend.db import ResearchAuditRepository, TrajectoryLogRecord
from .evaluator import hash_schema_name
from .runner import ADKRunRequest, ADKRunResult


@dataclass(frozen=True)
class RuntimeTrajectoryLog:
    """Runtime-facing trajectory log model persisted to the audit store."""

    workflow_id: str
    correlation_id: str
    agent_name: str
    phase: str
    iteration_no: int
    input_schema: str
    input_payload: dict[str, Any]
    output_schema: str
    output_payload: dict[str, Any]
    latency_ms: int
    final_state: str
    log_id: str | None = None
    tool_calls: tuple[dict[str, Any], ...] = ()
    observation_payload_ref: str | None = None
    evaluation_output_ref: str | None = None
    token_usage: dict[str, int] | None = None
    signature: str | None = None
    artifact_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.workflow_id:
            raise ValueError("workflow_id must be non-empty")
        if not self.correlation_id:
            raise ValueError("correlation_id must be non-empty")
        if not self.agent_name:
            raise ValueError("agent_name must be non-empty")
        if not self.phase:
            raise ValueError("phase must be non-empty")
        if self.iteration_no < 0:
            raise ValueError("iteration_no must be zero or greater")
        if not self.input_schema:
            raise ValueError("input_schema must be non-empty")
        if not self.output_schema:
            raise ValueError("output_schema must be non-empty")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be zero or greater")
        if not self.final_state:
            raise ValueError("final_state must be non-empty")

    @property
    def resolved_log_id(self) -> str:
        return self.log_id or generate_prefixed_id("log")

    @property
    def input_hash(self) -> str:
        return _hash_schema_payload(self.input_schema, self.input_payload)

    @property
    def output_hash(self) -> str:
        return _hash_schema_payload(self.output_schema, self.output_payload)

    @property
    def input_schema_hash(self) -> str:
        return hash_schema_name(self.input_schema)

    @property
    def output_schema_hash(self) -> str:
        return hash_schema_name(self.output_schema)

    @property
    def tool_calls_json(self) -> str:
        return canonical_json_dumps(list(self.tool_calls))

    @property
    def token_usage_json(self) -> str | None:
        if self.token_usage is None:
            return None
        return canonical_json_dumps(self.token_usage)


class RuntimeTrajectoryLogService:
    """Thin service that persists runtime trajectory logs."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def persist(self, log: RuntimeTrajectoryLog) -> TrajectoryLogRecord:
        return self._repository.add_trajectory_log(
            log_id=log.resolved_log_id,
            workflow_id=log.workflow_id,
            correlation_id=log.correlation_id,
            agent_name=log.agent_name,
            phase=log.phase,
            iteration_no=log.iteration_no,
            input_schema=log.input_schema,
            input_hash=log.input_hash,
            output_schema=log.output_schema,
            output_hash=log.output_hash,
            tool_calls_json=log.tool_calls_json,
            observation_payload_ref=log.observation_payload_ref,
            evaluation_output_ref=log.evaluation_output_ref,
            latency_ms=log.latency_ms,
            token_usage_json=log.token_usage_json,
            final_state=log.final_state,
            signature=log.signature,
            artifact_ref=log.artifact_ref,
        )


def build_run_trajectory_log(
    *,
    request: ADKRunRequest,
    result: ADKRunResult,
    phase: str,
    iteration_no: int,
    input_schema: str,
    output_schema: str,
    observation_payload_ref: str | None = None,
    evaluation_output_ref: str | None = None,
    signature: str | None = None,
    artifact_ref: str | None = None,
) -> RuntimeTrajectoryLog:
    """Build a trajectory log from one normalized request/result pair."""

    if request.workflow_id != result.workflow_id:
        raise ValueError("request and result workflow_id must match")
    if request.correlation_id != result.correlation_id:
        raise ValueError("request and result correlation_id must match")

    return RuntimeTrajectoryLog(
        workflow_id=result.workflow_id,
        correlation_id=result.correlation_id,
        agent_name=result.agent_name,
        phase=phase,
        iteration_no=iteration_no,
        input_schema=input_schema,
        input_payload=dict(request.input_payload),
        output_schema=output_schema,
        output_payload=dict(result.output_payload),
        tool_calls=tuple(result.tool_calls),
        observation_payload_ref=observation_payload_ref,
        evaluation_output_ref=evaluation_output_ref,
        latency_ms=result.latency_ms,
        token_usage=None if result.token_usage is None else dict(result.token_usage),
        final_state=result.final_state,
        signature=signature,
        artifact_ref=artifact_ref,
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_dumps(payload).encode("utf-8")).hexdigest()


def _hash_schema_payload(schema_name: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json_dumps(
            {
                "schema_name": schema_name,
                "payload_hash": _hash_payload(payload),
            }
        ).encode("utf-8")
    ).hexdigest()
