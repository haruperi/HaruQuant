"""Small ADK-compatible runner wrapper for deterministic agent execution.

Data classes and protocols are defined here. The ADKRunnerService
implementation delegates to the middleware pipeline in middleware.py.
"""

from __future__ import annotations

from services.utils.logger import logger
from dataclasses import dataclass, field
import hashlib
from time import perf_counter
from typing import Any, Protocol

from backend.agents.prompts import PromptComposer, PromptContext
from backend.config.agent_model import AGENT_MODEL
from backend.orchestration.context_engineering.budget import ContextBudget

from .output_validation import CanonicalOutputValidator, ContractValidationError
from .prompt_registry_service import PromptRegistryService, PromptResolutionError
from .prompts import PromptRegistryRecord
from .redaction import ContextRedactionMiddleware
from .retrieval_guard import RetrievalSafetyReport, evaluate_retrieved_text
from .tool_policy import ToolAllowlistMiddleware, ToolPolicyError


@dataclass(frozen=True)
class ADKRunnerConfig:
    """Static runtime identity and defaults for an agent runner."""

    runner_name: str
    default_model: str = AGENT_MODEL
    runtime_version: str = "local-adk-wrapper-v1"
    environment: str = "paper"
    system_policy: str | None = None
    workflow_policy: str | None = None
    context_max_tokens: int | None = None
    context_reserved_tokens: int = 512


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
    """Runner-wrapped result with normalized timing and safety metadata."""

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
    repair_attempted: bool = False
    repair_succeeded: bool = False
    validation_error: str | None = None
    redacted_paths: tuple[str, ...] = ()
    retrieval_safety: dict[str, Any] | None = None


class AgentRuntime(Protocol):
    """Small agent protocol used by the wrapper service."""

    def run(
        self,
        *,
        request: ADKRunRequest,
        context: AgentExecutionContext,
    ) -> AgentExecutionResult: ...


# Re-export ADKRunnerService from middleware for backward compatibility
from .middleware import (
    ADKRunnerService,
    MiddlewarePipeline,
    MiddlewareProtocol,
    MiddlewareContext,
    NextMiddleware,
    ContextRedactionMiddlewareComponent,
    RetrievalGuardMiddleware,
    PromptCompositionMiddleware,
    ToolPolicyMiddleware,
    OutputValidationMiddleware,
)

__all__ = [
    "ADKRunnerConfig",
    "ADKRunRequest",
    "AgentExecutionContext",
    "AgentExecutionResult",
    "ADKRunResult",
    "AgentRuntime",
    "ADKRunnerService",
    "MiddlewarePipeline",
    "MiddlewareProtocol",
    "MiddlewareContext",
    "NextMiddleware",
    "ContextRedactionMiddlewareComponent",
    "RetrievalGuardMiddleware",
    "PromptCompositionMiddleware",
    "ToolPolicyMiddleware",
    "OutputValidationMiddleware",
]
