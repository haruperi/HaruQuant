"""Small ADK-compatible runner wrapper for deterministic agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
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


class ADKRunnerService:
    """Execution wrapper for agent runtimes.

    The runner is the mandatory enforcement point for prompt resolution,
    context redaction, prompt composition, tool allowlists, and output
    validation/repair.
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
        self._output_validator = output_validator
        self._prompt_registry = prompt_registry
        self._redactor = redactor or ContextRedactionMiddleware()
        self._tool_policy = tool_policy or ToolAllowlistMiddleware()

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
        prompt_record = self._resolve_prompt_record(request)
        redacted_payload = self._redactor.redact(request.input_payload)
        redacted_metadata = self._redactor.redact(dict(request.metadata))
        redacted_paths = redacted_payload.redacted_paths + redacted_metadata.redacted_paths

        retrieval_report = self._evaluate_retrieved_context(redacted_metadata.payload)
        if self._should_block_retrieved_context(request.agent_name, retrieval_report):
            return self._error_result(
                request=request,
                model=model,
                prompt_record=prompt_record,
                latency_ms=0,
                output_payload={
                    "error": "Retrieved context blocked by prompt-injection guard",
                    "contract_type": request.input_payload.get("contract_type", "unknown"),
                    "schema_version": request.input_payload.get("schema_version", "1.0.0"),
                    "severity": retrieval_report.severity if retrieval_report else "none",
                    "reason_codes": list(retrieval_report.reason_codes) if retrieval_report else [],
                },
                final_state="RETRIEVAL_BLOCKED",
                redacted_paths=redacted_paths,
                retrieval_report=retrieval_report,
            )

        augmented_request = self._build_augmented_request(
            request=request,
            redacted_payload=redacted_payload.payload,
            redacted_metadata=redacted_metadata.payload,
            prompt_record=prompt_record,
            retrieval_report=retrieval_report,
        )
        context = AgentExecutionContext(
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            model=model,
            allowed_tools=request.allowed_tools,
            prompt_version_id=augmented_request.prompt_version_id,
            metadata=dict(augmented_request.metadata),
        )

        started = perf_counter()
        result = agent.run(request=augmented_request, context=context)
        latency_ms = int((perf_counter() - started) * 1000)

        tool_policy_error = self._validate_tool_calls(
            allowed_tools=request.allowed_tools,
            tool_calls=tuple(result.tool_calls),
        )
        if tool_policy_error is not None:
            return self._error_result(
                request=request,
                model=model,
                prompt_record=prompt_record,
                latency_ms=latency_ms,
                output_payload={
                    "error": str(tool_policy_error),
                    "contract_type": request.input_payload.get("contract_type", "unknown"),
                    "schema_version": request.input_payload.get("schema_version", "1.0.0"),
                },
                final_state="TOOL_POLICY_VIOLATION",
                tool_calls=tuple(result.tool_calls),
                token_usage=result.token_usage,
                redacted_paths=redacted_paths,
                retrieval_report=retrieval_report,
            )

        output_payload = dict(result.output_payload)
        repair_attempted = False
        repair_succeeded = False

        if self._output_validator is not None:
            try:
                _, repair_attempts = self._output_validator.validate_with_retry(output_payload)
                repair_attempted = bool(repair_attempts)
                repair_succeeded = any(attempt.succeeded for attempt in repair_attempts)
                if repair_succeeded:
                    output_payload = [attempt for attempt in repair_attempts if attempt.succeeded][-1].repaired_payload
            except ContractValidationError as exc:
                validation_error = str(exc)
                return self._error_result(
                    request=request,
                    model=model,
                    prompt_record=prompt_record,
                    latency_ms=latency_ms,
                    output_payload={
                        "error": "Output validation failed",
                        "validation_error": validation_error,
                        "invalid_output_hash": self._hash_payload(output_payload),
                        "contract_type": output_payload.get(
                            "contract_type",
                            request.input_payload.get("contract_type", "unknown"),
                        ),
                        "schema_version": output_payload.get(
                            "schema_version",
                            request.input_payload.get("schema_version", "1.0.0"),
                        ),
                    },
                    final_state="VALIDATION_FAILED",
                    tool_calls=tuple(result.tool_calls),
                    token_usage=result.token_usage,
                    repair_attempted=repair_attempted,
                    repair_succeeded=repair_succeeded,
                    validation_error=validation_error,
                    redacted_paths=redacted_paths,
                    retrieval_report=retrieval_report,
                )

        return ADKRunResult(
            runner_name=self._config.runner_name,
            runtime_version=self._config.runtime_version,
            agent_name=request.agent_name,
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            model=model,
            prompt_version_id=augmented_request.prompt_version_id,
            prompt_hash=self._result_prompt_hash(prompt_record, augmented_request),
            latency_ms=latency_ms,
            output_payload=output_payload,
            final_state=result.final_state,
            tool_calls=tuple(result.tool_calls),
            token_usage=None if result.token_usage is None else dict(result.token_usage),
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
            redacted_paths=redacted_paths,
            retrieval_safety=self._retrieval_report_payload(retrieval_report),
        )

    def _resolve_prompt_record(self, request: ADKRunRequest) -> PromptRegistryRecord | None:
        if self._prompt_registry is None:
            return None
        try:
            if request.prompt_version_id:
                return self._prompt_registry.get_version(
                    agent_name=request.agent_name,
                    prompt_version_id=request.prompt_version_id,
                )
            environment = str(request.metadata.get("environment", self._config.environment))
            return self._prompt_registry.get_active_version(
                agent_name=request.agent_name,
                environment=environment,
            )
        except PromptResolutionError:
            return None

    def _build_augmented_request(
        self,
        *,
        request: ADKRunRequest,
        redacted_payload: dict[str, Any],
        redacted_metadata: dict[str, Any],
        prompt_record: PromptRegistryRecord | None,
        retrieval_report: RetrievalSafetyReport | None,
    ) -> ADKRunRequest:
        instruction = self._instruction_text(prompt_record, redacted_payload, redacted_metadata)
        payload = dict(redacted_payload)
        if instruction:
            prompt_context = PromptContext(
                system_policy=self._config.system_policy or self._metadata_text(redacted_metadata, "system_policy"),
                workflow_policy=self._config.workflow_policy or self._metadata_text(redacted_metadata, "workflow_policy"),
                user_input=self._metadata_text(redacted_metadata, "user_input") or self._json_payload(redacted_payload),
                retrieved_content=self._metadata_text(redacted_metadata, "retrieved_content"),
                tool_output=self._metadata_text(redacted_metadata, "tool_output"),
                prior_steps=redacted_metadata.get("prior_steps") if isinstance(redacted_metadata.get("prior_steps"), dict) else None,
                refinement_feedback=self._extract_refinement_feedback(redacted_metadata),
            )
            context_budget = (
                ContextBudget(
                    max_tokens=self._config.context_max_tokens,
                    reserved_tokens=self._config.context_reserved_tokens,
                )
                if self._config.context_max_tokens is not None
                else None
            )
            payload["_system_prompt"] = PromptComposer.compose(
                instruction,
                prompt_context,
                context_budget=context_budget,
            )
        if retrieval_report is not None:
            payload["_retrieval_safety"] = self._retrieval_report_payload(retrieval_report)

        return replace(
            request,
            input_payload=payload,
            prompt_version_id=prompt_record.prompt_version_id if prompt_record is not None else request.prompt_version_id,
            metadata=redacted_metadata,
        )

    @staticmethod
    def _instruction_text(
        prompt_record: PromptRegistryRecord | None,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        if prompt_record is not None:
            return prompt_record.instruction_text
        value = metadata.get("agent_instruction") or payload.get("_system_prompt")
        return value if isinstance(value, str) else ""

    @staticmethod
    def _extract_refinement_feedback(metadata: dict[str, Any]) -> dict[str, Any] | None:
        if "refinement_iteration" not in metadata:
            return None
        return {
            "refinement_iteration": metadata.get("refinement_iteration"),
            "previous_score": metadata.get("previous_score"),
            "improvement_actions": metadata.get("improvement_actions", []),
            "focus_areas": metadata.get("focus_areas", []),
        }

    @staticmethod
    def _metadata_text(metadata: dict[str, Any], key: str) -> str | None:
        value = metadata.get(key)
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _json_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    @staticmethod
    def _evaluate_retrieved_context(metadata: dict[str, Any]) -> RetrievalSafetyReport | None:
        retrieved_content = metadata.get("retrieved_content")
        if not isinstance(retrieved_content, str) or not retrieved_content:
            return None
        return evaluate_retrieved_text(retrieved_content)

    @staticmethod
    def _should_block_retrieved_context(
        agent_name: str,
        report: RetrievalSafetyReport | None,
    ) -> bool:
        if report is None or report.safe:
            return False
        high_risk_agents = {
            "execution_agent",
            "risk_governor_agent",
            "compliance_agent",
            "orchestrator_agent",
        }
        return agent_name in high_risk_agents

    def _validate_tool_calls(
        self,
        *,
        allowed_tools: tuple[str, ...],
        tool_calls: tuple[dict[str, Any], ...],
    ) -> ToolPolicyError | None:
        requested_tools = tuple(
            str(call.get("tool_name") or call.get("name") or call.get("action") or "")
            for call in tool_calls
            if call.get("tool_name") or call.get("name") or call.get("action")
        )
        if not requested_tools:
            return None
        try:
            self._tool_policy.enforce(
                allowed_tools=allowed_tools,
                requested_tools=requested_tools,
            )
        except ToolPolicyError as exc:
            return exc
        return None

    def _error_result(
        self,
        *,
        request: ADKRunRequest,
        model: str,
        prompt_record: PromptRegistryRecord | None,
        latency_ms: int,
        output_payload: dict[str, Any],
        final_state: str,
        tool_calls: tuple[dict[str, Any], ...] = (),
        token_usage: dict[str, int] | None = None,
        repair_attempted: bool = False,
        repair_succeeded: bool = False,
        validation_error: str | None = None,
        redacted_paths: tuple[str, ...] = (),
        retrieval_report: RetrievalSafetyReport | None = None,
    ) -> ADKRunResult:
        return ADKRunResult(
            runner_name=self._config.runner_name,
            runtime_version=self._config.runtime_version,
            agent_name=request.agent_name,
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            model=model,
            prompt_version_id=prompt_record.prompt_version_id if prompt_record is not None else request.prompt_version_id,
            prompt_hash=prompt_record.content_hash if prompt_record is not None else None,
            latency_ms=latency_ms,
            output_payload=output_payload,
            final_state=final_state,
            tool_calls=tool_calls,
            token_usage=None if token_usage is None else dict(token_usage),
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
            validation_error=validation_error,
            redacted_paths=redacted_paths,
            retrieval_safety=self._retrieval_report_payload(retrieval_report),
        )

    @staticmethod
    def _retrieval_report_payload(report: RetrievalSafetyReport | None) -> dict[str, Any] | None:
        if report is None:
            return None
        return {
            "safe": report.safe,
            "severity": report.severity,
            "reason_codes": list(report.reason_codes),
            "matched_markers": list(report.matched_markers),
        }

    @staticmethod
    def _result_prompt_hash(
        prompt_record: PromptRegistryRecord | None,
        request: ADKRunRequest,
    ) -> str | None:
        if prompt_record is not None:
            return prompt_record.content_hash
        prompt = request.input_payload.get("_system_prompt")
        if not isinstance(prompt, str) or not prompt:
            return None
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
