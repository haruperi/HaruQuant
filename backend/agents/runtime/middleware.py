"""Middleware pipeline for ADKRunnerService.

Each middleware component handles a single cross-cutting concern
(redaction, retrieval guard, prompt composition, tool policy,
output validation) and can be added, removed, reordered, or
replaced independently.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from backend.agents.prompts import PromptComposer, PromptContext
from backend.config.agent_model import AGENT_MODEL
from backend.orchestration.context_engineering.budget import ContextBudget

from .output_validation import CanonicalOutputValidator, ContractValidationError
from .prompt_registry_service import PromptRegistryService, PromptResolutionError
from .prompts import PromptRegistryRecord
from .redaction import ContextRedactionMiddleware, RedactedContext
from .retrieval_guard import RetrievalSafetyReport, evaluate_retrieved_text
from .tool_validation import ToolValidator, ToolValidationError, register_mcp_schemas
from .runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerConfig,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
)
from .tool_policy import ToolAllowlistMiddleware, ToolPolicyError


# ─────────────────────────────────────────────────────────────────────
# Middleware Protocol
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MiddlewareContext:
    """Context passed through the middleware pipeline."""
    request: ADKRunRequest
    config: ADKRunnerConfig
    prompt_record: PromptRegistryRecord | None = None
    redacted_paths: tuple[str, ...] = ()
    retrieval_report: RetrievalSafetyReport | None = None


class NextMiddleware(Protocol):
    """Callable that invokes the next middleware in the pipeline."""
    def __call__(self, ctx: MiddlewareContext) -> ADKRunResult: ...


class MiddlewareProtocol(Protocol):
    """Interface for a single middleware component."""
    def process(
        self,
        ctx: MiddlewareContext,
        next_fn: NextMiddleware,
    ) -> ADKRunResult: ...


# ─────────────────────────────────────────────────────────────────────
# Middleware Pipeline
# ─────────────────────────────────────────────────────────────────────

class MiddlewarePipeline:
    """Composable middleware pipeline.

    Middleware are executed in registration order. Each middleware
    can:
    - Modify the request before calling next_fn
    - Short-circuit and return early (e.g., retrieval guard blocks)
    - Modify the result after next_fn returns (e.g., add metadata)

    Usage:
        pipeline = MiddlewarePipeline()
        pipeline.add(ContextRedactionMiddleware())
        pipeline.add(RetrievalGuardMiddleware())
        pipeline.add(PromptCompositionMiddleware())
        result = pipeline.run(agent, request, config)
    """

    def __init__(self) -> None:
        self._middleware: list[MiddlewareProtocol] = []

    def add(self, middleware: MiddlewareProtocol) -> "MiddlewarePipeline":
        """Add middleware to the pipeline (appended to end)."""
        self._middleware.append(middleware)
        return self

    def run(
        self,
        agent: AgentRuntime,
        request: ADKRunRequest,
        config: ADKRunnerConfig,
        prompt_record: PromptRegistryRecord | None = None,
    ) -> ADKRunResult:
        """Execute the middleware pipeline and return ADKRunResult."""
        ctx = MiddlewareContext(
            request=request,
            config=config,
            prompt_record=prompt_record,
        )

        # Build the innermost function: agent execution
        def _make_agent_fn() -> NextMiddleware:
            def _agent_fn(inner_ctx: MiddlewareContext) -> ADKRunResult:
                return _execute_agent(
                    agent=agent,
                    ctx=inner_ctx,
                )
            return _agent_fn

        # Wrap middleware in reverse order so first-added runs first
        next_fn = _make_agent_fn()
        for mw in reversed(self._middleware):
            next_fn = self._make_middleware_fn(mw, next_fn)

        return next_fn(ctx)

    @staticmethod
    def _make_middleware_fn(
        mw: MiddlewareProtocol,
        next_fn: NextMiddleware,
    ) -> NextMiddleware:
        def _wrapped(ctx: MiddlewareContext) -> ADKRunResult:
            return mw.process(ctx, next_fn)
        return _wrapped


# ─────────────────────────────────────────────────────────────────────
# Context Redaction Middleware
# ─────────────────────────────────────────────────────────────────────

class ContextRedactionMiddlewareComponent(MiddlewareProtocol):
    """Redacts sensitive fields from request payload and metadata."""

    def __init__(self, redactor: ContextRedactionMiddleware | None = None) -> None:
        self._redactor = redactor or ContextRedactionMiddleware()

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        redacted_payload = self._redactor.redact(ctx.request.input_payload)
        redacted_metadata = self._redactor.redact(dict(ctx.request.metadata))
        all_redacted = redacted_payload.redacted_paths + redacted_metadata.redacted_paths

        new_request = _replace_request_fields(
            ctx.request,
            input_payload=redacted_payload.payload,
            metadata=redacted_metadata.payload,
        )
        new_ctx = MiddlewareContext(
            request=new_request,
            config=ctx.config,
            prompt_record=ctx.prompt_record,
            redacted_paths=all_redacted,
            retrieval_report=ctx.retrieval_report,
        )
        return next_fn(new_ctx)


# ─────────────────────────────────────────────────────────────────────
# Retrieval Guard Middleware
# ─────────────────────────────────────────────────────────────────────

_HIGH_RISK_AGENTS = frozenset({
    "execution_agent",
    "risk_governor_agent",
    "compliance_agent",
    "orchestrator_agent",
})


class RetrievalGuardMiddleware(MiddlewareProtocol):
    """Blocks unsafe retrieved content from reaching high-risk agents."""

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        metadata = ctx.request.metadata
        retrieved_content = metadata.get("retrieved_content")
        if not isinstance(retrieved_content, str) or not retrieved_content:
            return next_fn(ctx)

        report = evaluate_retrieved_text(retrieved_content)
        if report.safe:
            return next_fn(MiddlewareContext(
                request=ctx.request,
                config=ctx.config,
                prompt_record=ctx.prompt_record,
                redacted_paths=ctx.redacted_paths,
                retrieval_report=report,
            ))

        # Check if this agent is high-risk
        if ctx.request.agent_name not in _HIGH_RISK_AGENTS:
            return next_fn(MiddlewareContext(
                request=ctx.request,
                config=ctx.config,
                prompt_record=ctx.prompt_record,
                redacted_paths=ctx.redacted_paths,
                retrieval_report=report,
            ))

        # Block: return error result without calling next_fn
        return _error_result(
            ctx=ctx,
            model=ctx.request.model or ctx.config.default_model,
            latency_ms=0,
            final_state="RETRIEVAL_BLOCKED",
            output_payload={
                "error": "Retrieved context blocked by prompt-injection guard",
                "contract_type": ctx.request.input_payload.get("contract_type", "unknown"),
                "schema_version": ctx.request.input_payload.get("schema_version", "1.0.0"),
                "severity": report.severity,
                "reason_codes": list(report.reason_codes),
            },
            retrieval_report=report,
        )


# ─────────────────────────────────────────────────────────────────────
# Prompt Composition Middleware
# ─────────────────────────────────────────────────────────────────────

class PromptCompositionMiddleware(MiddlewareProtocol):
    """Resolves prompt from registry, composes trust-layered prompt."""

    def __init__(
        self,
        prompt_registry: PromptRegistryService | None = None,
    ) -> None:
        self._prompt_registry = prompt_registry

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        request = ctx.request
        config = ctx.config
        prompt_record = ctx.prompt_record

        # Resolve prompt from registry if not already set
        if prompt_record is None and self._prompt_registry is not None:
            try:
                if request.prompt_version_id:
                    prompt_record = self._prompt_registry.get_version(
                        agent_name=request.agent_name,
                        prompt_version_id=request.prompt_version_id,
                    )
                else:
                    environment = str(request.metadata.get("environment", config.environment))
                    prompt_record = self._prompt_registry.get_active_version(
                        agent_name=request.agent_name,
                        environment=environment,
                    )
            except PromptResolutionError:
                pass

        # Build instruction text
        instruction = _instruction_text(prompt_record, request.input_payload, request.metadata)

        if not instruction:
            # No prompt composition needed
            return next_fn(MiddlewareContext(
                request=request,
                config=config,
                prompt_record=prompt_record,
                redacted_paths=ctx.redacted_paths,
                retrieval_report=ctx.retrieval_report,
            ))

        # Compose trust-layered prompt
        metadata = request.metadata
        prompt_context = PromptContext(
            system_policy=config.system_policy or _metadata_text(metadata, "system_policy"),
            workflow_policy=config.workflow_policy or _metadata_text(metadata, "workflow_policy"),
            user_input=_metadata_text(metadata, "user_input") or _json_payload(request.input_payload),
            retrieved_content=_metadata_text(metadata, "retrieved_content"),
            tool_output=_metadata_text(metadata, "tool_output"),
            prior_steps=metadata.get("prior_steps") if isinstance(metadata.get("prior_steps"), dict) else None,
            refinement_feedback=_extract_refinement_feedback(metadata),
        )

        context_budget = None
        if config.context_max_tokens is not None:
            context_budget = ContextBudget(
                max_tokens=config.context_max_tokens,
                reserved_tokens=config.context_reserved_tokens,
            )

        composed_prompt = PromptComposer.compose(
            instruction,
            prompt_context,
            context_budget=context_budget,
        )

        # Inject composed prompt into request payload
        new_payload = dict(request.input_payload)
        new_payload["_system_prompt"] = composed_prompt

        if ctx.retrieval_report is not None:
            new_payload["_retrieval_safety"] = _retrieval_report_payload(ctx.retrieval_report)

        new_request = _replace_request_fields(
            request,
            input_payload=new_payload,
            prompt_version_id=prompt_record.prompt_version_id if prompt_record else request.prompt_version_id,
        )

        return next_fn(MiddlewareContext(
            request=new_request,
            config=config,
            prompt_record=prompt_record,
            redacted_paths=ctx.redacted_paths,
            retrieval_report=ctx.retrieval_report,
        ))


# ─────────────────────────────────────────────────────────────────────
# Tool Validation Middleware (pre-execution)
# ─────────────────────────────────────────────────────────────────────

class ToolValidationMiddleware(MiddlewareProtocol):
    """Validates tool call parameters BEFORE execution.

    Catches missing required parameters and type mismatches
    before any tool is actually invoked.
    """

    def __init__(self, validator: ToolValidator | None = None) -> None:
        self._validator = validator or ToolValidator()
        register_mcp_schemas(self._validator)

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        # Extract tool calls from the request (if any are pre-specified)
        tool_calls = ctx.request.metadata.get("tool_calls", [])
        for tc in tool_calls:
            try:
                self._validator.validate(tc)
            except ToolValidationError as exc:
                return _error_result(
                    ctx=ctx,
                    model=ctx.request.model or ctx.config.default_model,
                    latency_ms=0,
                    final_state="TOOL_VALIDATION_FAILED",
                    output_payload={
                        "error": f"Pre-execution tool validation failed: {exc}",
                        "contract_type": ctx.request.input_payload.get("contract_type", "unknown"),
                        "schema_version": ctx.request.input_payload.get("schema_version", "1.0.0"),
                    },
                    redacted_paths=ctx.redacted_paths,
                    retrieval_report=ctx.retrieval_report,
                )

        return next_fn(ctx)


# ─────────────────────────────────────────────────────────────────────
# Tool Policy Middleware (post-execution)
# ─────────────────────────────────────────────────────────────────────

class ToolPolicyMiddleware(MiddlewareProtocol):
    """Enforces tool allowlist policy and output size limits on agent tool calls."""

    def __init__(
        self,
        tool_policy: ToolAllowlistMiddleware | None = None,
        max_output_tokens: int = 4096,
    ) -> None:
        self._tool_policy = tool_policy or ToolAllowlistMiddleware()
        self._max_output_tokens = max_output_tokens

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        result = next_fn(ctx)

        # Check tool calls in result
        tool_calls = tuple(result.tool_calls)
        if not tool_calls:
            return result

        requested_tools = tuple(
            str(call.get("tool_name") or call.get("name") or call.get("action") or "")
            for call in tool_calls
            if call.get("tool_name") or call.get("name") or call.get("action")
        )
        if not requested_tools:
            return result

        try:
            self._tool_policy.enforce(
                allowed_tools=ctx.request.allowed_tools,
                requested_tools=requested_tools,
            )
        except ToolPolicyError as exc:
            return _error_result(
                ctx=ctx,
                model=ctx.request.model or ctx.config.default_model,
                latency_ms=0,
                final_state="TOOL_POLICY_VIOLATION",
                output_payload={
                    "error": str(exc),
                    "contract_type": ctx.request.input_payload.get("contract_type", "unknown"),
                    "schema_version": ctx.request.input_payload.get("schema_version", "1.0.0"),
                },
                tool_calls=tool_calls,
                token_usage=result.token_usage,
                redacted_paths=ctx.redacted_paths,
                retrieval_report=ctx.retrieval_report,
            )

        # Truncate oversized tool outputs in the result payload
        truncated_payload = self._truncate_tool_outputs(result.output_payload)
        if truncated_payload is not result.output_payload:
            return _replace_result_output(result, truncated_payload)

        return result

    def _truncate_tool_outputs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively truncate string values that exceed token budget."""
        return _truncate_strings_in_dict(payload, self._max_output_tokens * 4)


def _truncate_strings_in_dict(d: dict[str, Any], max_chars: int) -> dict[str, Any]:
    """Truncate all string values in a dict to max_chars."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(value, str) and len(value) > max_chars:
            result[key] = value[:max_chars] + "\n...[tool output truncated]"
        elif isinstance(value, dict):
            result[key] = _truncate_strings_in_dict(value, max_chars)
        elif isinstance(value, list):
            result[key] = [
                _truncate_strings_in_dict(item, max_chars) if isinstance(item, dict)
                else (item[:max_chars] + "\n...[truncated]" if isinstance(item, str) and len(item) > max_chars else item)
                for item in value
            ]
        else:
            result[key] = value
    return result


# ─────────────────────────────────────────────────────────────────────
# Output Validation Middleware
# ─────────────────────────────────────────────────────────────────────

class OutputValidationMiddleware(MiddlewareProtocol):
    """Validates agent output against schema registry with retry/repair."""

    def __init__(
        self,
        output_validator: CanonicalOutputValidator | None = None,
    ) -> None:
        self._output_validator = output_validator

    def process(self, ctx: MiddlewareContext, next_fn: NextMiddleware) -> ADKRunResult:
        result = next_fn(ctx)

        if self._output_validator is None:
            return result

        output_payload = dict(result.output_payload)
        repair_attempted = False
        repair_succeeded = False

        try:
            _, repair_attempts_list = self._output_validator.validate_with_retry(output_payload)
            repair_attempted = bool(repair_attempts_list)
            repair_succeeded = any(attempt.succeeded for attempt in repair_attempts_list)
            if repair_succeeded:
                output_payload = [a for a in repair_attempts_list if a.succeeded][-1].repaired_payload
        except ContractValidationError as exc:
            return _error_result(
                ctx=ctx,
                model=ctx.request.model or ctx.config.default_model,
                latency_ms=0,
                final_state="VALIDATION_FAILED",
                output_payload={
                    "error": "Output validation failed",
                    "validation_error": str(exc),
                    "invalid_output_hash": _hash_payload(output_payload),
                    "contract_type": output_payload.get(
                        "contract_type",
                        ctx.request.input_payload.get("contract_type", "unknown"),
                    ),
                    "schema_version": output_payload.get(
                        "schema_version",
                        ctx.request.input_payload.get("schema_version", "1.0.0"),
                    ),
                },
                tool_calls=tuple(result.tool_calls),
                token_usage=result.token_usage,
                repair_attempted=repair_attempted,
                repair_succeeded=repair_succeeded,
                validation_error=str(exc),
                redacted_paths=ctx.redacted_paths,
                retrieval_report=ctx.retrieval_report,
            )

        # Return successful result with repair metadata
        return _success_result(
            ctx=ctx,
            result=result,
            output_payload=output_payload,
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
        )


# ─────────────────────────────────────────────────────────────────────
# ADKRunnerService (backward-compatible facade)
# ─────────────────────────────────────────────────────────────────────

class ADKRunnerService:
    """Execution wrapper for agent runtimes.

    Delegates to a composable middleware pipeline while maintaining
    full backward compatibility with the previous monolithic API.
    """

    def __init__(
        self,
        config: ADKRunnerConfig,
        output_validator: CanonicalOutputValidator | None = None,
        prompt_registry: PromptRegistryService | None = None,
        redactor: ContextRedactionMiddleware | None = None,
        tool_policy: ToolAllowlistMiddleware | None = None,
    ) -> None:
        self._config = config
        self._pipeline = MiddlewarePipeline()
        self._pipeline.add(ContextRedactionMiddlewareComponent(redactor))
        self._pipeline.add(RetrievalGuardMiddleware())
        self._pipeline.add(PromptCompositionMiddleware(prompt_registry))
        self._pipeline.add(ToolValidationMiddleware())
        self._pipeline.add(ToolPolicyMiddleware(tool_policy))
        self._pipeline.add(OutputValidationMiddleware(output_validator))

    @property
    def config(self) -> ADKRunnerConfig:
        return self._config

    @property
    def pipeline(self) -> MiddlewarePipeline:
        """Expose the pipeline for inspection or extension."""
        return self._pipeline

    def run(
        self,
        *,
        agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        """Execute agent through the middleware pipeline."""
        return self._pipeline.run(agent, request, self._config)


# ─────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────

import json as _json_module
from dataclasses import replace as _replace


def _replace_request_fields(request: ADKRunRequest, **updates: Any) -> ADKRunRequest:
    """Replace fields on an ADKRunRequest."""
    return _replace(request, **updates)


def _execute_agent(
    *,
    agent: AgentRuntime,
    ctx: MiddlewareContext,
) -> ADKRunResult:
    """Innermost pipeline function: execute the agent."""
    request = ctx.request
    config = ctx.config
    model = request.model or config.default_model

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

    prompt_record = ctx.prompt_record
    prompt_hash = None
    if prompt_record is not None:
        prompt_hash = prompt_record.content_hash
    else:
        prompt = request.input_payload.get("_system_prompt")
        if isinstance(prompt, str) and prompt:
            prompt_hash = _hash_payload_str(prompt)

    return ADKRunResult(
        runner_name=config.runner_name,
        runtime_version=config.runtime_version,
        agent_name=request.agent_name,
        workflow_id=request.workflow_id,
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        model=model,
        prompt_version_id=request.prompt_version_id,
        prompt_hash=prompt_hash,
        latency_ms=latency_ms,
        output_payload=dict(result.output_payload),
        final_state=result.final_state,
        tool_calls=tuple(result.tool_calls),
        token_usage=None if result.token_usage is None else dict(result.token_usage),
        repair_attempted=False,
        repair_succeeded=False,
        redacted_paths=ctx.redacted_paths,
        retrieval_safety=_retrieval_report_payload(ctx.retrieval_report),
    )


def _error_result(
    *,
    ctx: MiddlewareContext,
    model: str,
    latency_ms: int,
    final_state: str,
    output_payload: dict[str, Any],
    tool_calls: tuple[dict[str, Any], ...] = (),
    token_usage: dict[str, int] | None = None,
    repair_attempted: bool = False,
    repair_succeeded: bool = False,
    validation_error: str | None = None,
    redacted_paths: tuple[str, ...] = (),
    retrieval_report: RetrievalSafetyReport | None = None,
) -> ADKRunResult:
    prompt_record = ctx.prompt_record
    request = ctx.request
    return ADKRunResult(
        runner_name=ctx.config.runner_name,
        runtime_version=ctx.config.runtime_version,
        agent_name=request.agent_name,
        workflow_id=request.workflow_id,
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        model=model,
        prompt_version_id=prompt_record.prompt_version_id if prompt_record else request.prompt_version_id,
        prompt_hash=prompt_record.content_hash if prompt_record else None,
        latency_ms=latency_ms,
        output_payload=output_payload,
        final_state=final_state,
        tool_calls=tool_calls,
        token_usage=None if token_usage is None else dict(token_usage),
        repair_attempted=repair_attempted,
        repair_succeeded=repair_succeeded,
        validation_error=validation_error,
        redacted_paths=redacted_paths or ctx.redacted_paths,
        retrieval_safety=_retrieval_report_payload(retrieval_report),
    )


def _success_result(
    *,
    ctx: MiddlewareContext,
    result: AgentExecutionResult,
    output_payload: dict[str, Any],
    repair_attempted: bool,
    repair_succeeded: bool,
) -> ADKRunResult:
    request = ctx.request
    config = ctx.config
    prompt_record = ctx.prompt_record
    model = request.model or config.default_model

    prompt_hash = None
    if prompt_record is not None:
        prompt_hash = prompt_record.content_hash
    else:
        prompt = request.input_payload.get("_system_prompt")
        if isinstance(prompt, str) and prompt:
            prompt_hash = _hash_payload_str(prompt)

    return ADKRunResult(
        runner_name=config.runner_name,
        runtime_version=config.runtime_version,
        agent_name=request.agent_name,
        workflow_id=request.workflow_id,
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        model=model,
        prompt_version_id=request.prompt_version_id,
        prompt_hash=prompt_hash,
        latency_ms=result.output_payload.get("_latency_ms", 0),
        output_payload=output_payload,
        final_state=result.final_state,
        tool_calls=tuple(result.tool_calls),
        token_usage=None if result.token_usage is None else dict(result.token_usage),
        repair_attempted=repair_attempted,
        repair_succeeded=repair_succeeded,
        redacted_paths=ctx.redacted_paths,
        retrieval_safety=_retrieval_report_payload(ctx.retrieval_report),
    )


def _instruction_text(
    prompt_record: PromptRegistryRecord | None,
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    if prompt_record is not None:
        return prompt_record.instruction_text
    value = metadata.get("agent_instruction") or payload.get("_system_prompt")
    return value if isinstance(value, str) else ""


def _extract_refinement_feedback(metadata: dict[str, Any]) -> dict[str, Any] | None:
    if "refinement_iteration" not in metadata:
        return None
    return {
        "refinement_iteration": metadata.get("refinement_iteration"),
        "previous_score": metadata.get("previous_score"),
        "improvement_actions": metadata.get("improvement_actions", []),
        "focus_areas": metadata.get("focus_areas", []),
    }


def _metadata_text(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) and value else None


def _json_payload(payload: dict[str, Any]) -> str:
    return _json_module.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _retrieval_report_payload(report: RetrievalSafetyReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "safe": report.safe,
        "severity": report.severity,
        "reason_codes": list(report.reason_codes),
        "matched_markers": list(report.matched_markers),
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _json_module.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _replace_result_output(result: ADKRunResult, new_payload: dict[str, Any]) -> ADKRunResult:
    """Create a new ADKRunResult with a replaced output_payload."""
    from dataclasses import replace
    return replace(result, output_payload=new_payload)


def _hash_payload_str(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
