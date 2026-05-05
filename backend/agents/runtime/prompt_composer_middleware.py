"""Prompt composing middleware for trust-layered model input."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from backend.agents.prompts import PromptComposer, PromptContext
from backend.agents.runtime.redaction import ContextRedactionMiddleware
from backend.agents.runtime.retrieval_guard import RetrievalSafetyReport, evaluate_retrieved_text
from backend.agents.runtime.runner import (
    ADKRunRequest,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
)
from haruquant.utils import logger
from backend.orchestration.context_engineering.budget import ContextBudget


class PromptComposingMiddleware:
    """Wrap an agent runtime with redaction and trust-layered prompt assembly."""

    def __init__(
        self,
        system_policy: Optional[str] = None,
        workflow_policy: Optional[str] = None,
        max_retrieved_length: int = 8000,
        max_tool_output_length: int = 12000,
        context_budget: ContextBudget | None = None,
        redactor: ContextRedactionMiddleware | None = None,
    ) -> None:
        self._system_policy = system_policy
        self._workflow_policy = workflow_policy
        self._max_retrieved_length = max_retrieved_length
        self._max_tool_output_length = max_tool_output_length
        self._context_budget = context_budget
        self._redactor = redactor or ContextRedactionMiddleware()

    def run(
        self,
        *,
        agent: AgentRuntime,
        instruction: str,
        request: ADKRunRequest,
        context: AgentExecutionContext,
        user_input: Optional[str] = None,
        retrieved_content: Optional[str] = None,
        tool_output: Optional[str] = None,
    ) -> AgentExecutionResult:
        """Compose a redacted trust-layered prompt and execute the agent."""
        redacted_payload = self._redactor.redact(request.input_payload)
        redacted_metadata = self._redactor.redact(dict(request.metadata))
        redacted_user_input = self._redact_text(user_input)
        redacted_retrieved = self._redact_text(retrieved_content)
        redacted_tool_output = self._redact_text(tool_output)

        safety_report: Optional[RetrievalSafetyReport] = None
        if redacted_retrieved:
            safety_report = evaluate_retrieved_text(redacted_retrieved)
            if not safety_report.safe:
                logger.warning(
                    "PromptComposingMiddleware: unsafe retrieved content, "
                    "severity=%s reasons=%s",
                    safety_report.severity,
                    ",".join(safety_report.reason_codes),
                )
                if self._should_block_retrieved_context(request.agent_name, safety_report):
                    return AgentExecutionResult(
                        output_payload={
                            "error": "Retrieved context blocked by prompt-injection guard",
                            "severity": safety_report.severity,
                            "reason_codes": list(safety_report.reason_codes),
                            "contract_type": request.input_payload.get("contract_type", "unknown"),
                            "schema_version": request.input_payload.get("schema_version", "1.0.0"),
                        },
                        final_state="RETRIEVAL_BLOCKED",
                    )
                redacted_retrieved = (
                    "[SAFETY WARNING: This content was flagged as potentially unsafe. "
                    f"Reasons: {', '.join(safety_report.reason_codes)}]\n\n"
                    f"{redacted_retrieved}"
                )
            if len(redacted_retrieved) > self._max_retrieved_length:
                redacted_retrieved = redacted_retrieved[: self._max_retrieved_length] + "\n\n... [truncated]"

        if redacted_tool_output and len(redacted_tool_output) > self._max_tool_output_length:
            redacted_tool_output = redacted_tool_output[: self._max_tool_output_length] + "\n\n... [truncated]"

        prompt_context = PromptContext(
            system_policy=self._system_policy,
            workflow_policy=self._workflow_policy,
            user_input=redacted_user_input,
            retrieved_content=redacted_retrieved,
            tool_output=redacted_tool_output,
            prior_steps=redacted_metadata.payload.get("prior_steps"),
            refinement_feedback=self._extract_refinement_feedback(redacted_metadata.payload),
        )
        composed_prompt = PromptComposer.compose(
            instruction,
            prompt_context,
            context_budget=self._context_budget,
        )
        logger.debug(
            "PromptComposingMiddleware: composed prompt chars=%s preview=%s",
            len(composed_prompt),
            composed_prompt[:500],
        )

        augmented_request = replace(
            request,
            input_payload={
                **redacted_payload.payload,
                "_system_prompt": composed_prompt,
            },
            metadata=redacted_metadata.payload,
        )
        return agent.run(request=augmented_request, context=context)

    def _redact_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._redactor.redact({"value": value}).payload.get("value")

    @staticmethod
    def _extract_refinement_feedback(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "refinement_iteration" not in metadata:
            return None
        return {
            "refinement_iteration": metadata.get("refinement_iteration"),
            "previous_score": metadata.get("previous_score"),
            "improvement_actions": metadata.get("improvement_actions", []),
            "focus_areas": metadata.get("focus_areas", []),
        }

    @staticmethod
    def _should_block_retrieved_context(
        agent_name: str,
        report: RetrievalSafetyReport,
    ) -> bool:
        high_risk_agents = {
            "execution_agent",
            "risk_governor_agent",
            "compliance_agent",
            "orchestrator_agent",
        }
        return agent_name in high_risk_agents
