"""Small ADK-compatible runner wrapper for deterministic agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from backend.config.agent_model import AGENT_MODEL, get_model_for_tier


@dataclass(frozen=True)
class ADKRunnerConfig:
    """Static runtime identity and defaults for an agent runner."""

    runner_name: str
    default_model: str = AGENT_MODEL
    runtime_version: str = "local-adk-wrapper-v1"


@dataclass(frozen=True)
class ADKRunRequest:
    """Execution request for one agent run."""

    workflow_id: str
    correlation_id: str
    agent_name: str
    input_payload: dict[str, Any]
    session_id: str | None = None
    prompt_version_id: str | None = None
    model: str | None = None
    allowed_tools: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentExecutionContext:
    """Normalized execution context passed to a runtime agent."""

    workflow_id: str
    correlation_id: str
    session_id: str | None
    model: str
    allowed_tools: tuple[str, ...]
    prompt_version_id: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AgentExecutionResult:
    """Normalized raw result returned by a runtime agent."""

    output_payload: dict[str, Any]
    final_state: str = "COMPLETED"
    tool_calls: tuple[dict[str, Any], ...] = ()
    token_usage: dict[str, int] | None = None


@dataclass(frozen=True)
class ADKRunResult:
    """Runner-wrapped result with normalized timing metadata."""

    runner_name: str
    runtime_version: str
    agent_name: str
    workflow_id: str
    correlation_id: str
    session_id: str | None
    model: str
    prompt_version_id: str | None
    prompt_hash: str | None
    latency_ms: int
    output_payload: dict[str, Any]
    final_state: str
    tool_calls: tuple[dict[str, Any], ...]
    token_usage: dict[str, int] | None


class AgentRuntime(Protocol):
    """Small agent protocol used by the wrapper service."""

    def run(
        self,
        *,
        request: ADKRunRequest,
        context: AgentExecutionContext,
    ) -> AgentExecutionResult: ...


class ADKRunnerService:
    """Thin execution wrapper around a runtime agent implementation."""

    def __init__(self, config: ADKRunnerConfig) -> None:
        self._config = config

    @property
    def config(self) -> ADKRunnerConfig:
        return self._config

    def run(
        self,
        *,
        agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        model = request.model or self._config.default_model
        context = AgentExecutionContext(
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            model=model,
            allowed_tools=request.allowed_tools,
            prompt_version_id=request.prompt_version_id,
            metadata=dict(request.metadata),
        )
        started = perf_counter()
        result = agent.run(request=request, context=context)
        latency_ms = int((perf_counter() - started) * 1000)
        return ADKRunResult(
            runner_name=self._config.runner_name,
            runtime_version=self._config.runtime_version,
            agent_name=request.agent_name,
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            model=model,
            prompt_version_id=request.prompt_version_id,
            prompt_hash=None,
            latency_ms=latency_ms,
            output_payload=dict(result.output_payload),
            final_state=result.final_state,
            tool_calls=tuple(result.tool_calls),
            token_usage=None if result.token_usage is None else dict(result.token_usage),
        )
