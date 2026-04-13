"""Prompt composing middleware — injects trust-layered prompts into agent execution."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Dict, Optional

from backend.agents.prompts import PromptComposer, PromptContext
from backend.agents.runtime.retrieval_guard import (
    RetrievalSafetyReport,
    evaluate_retrieved_text,
)
from backend.agents.runtime.runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
)
from backend.common.logger import logger


class PromptComposingMiddleware:
    """Wraps an agent runtime to compose prompts with strict trust hierarchy.

    Before calling the underlying LLM, this middleware:
    1. Retrieves the agent's instruction string
    2. Checks retrieved content for prompt injection
    3. Composes the full prompt with trust-layered sections:
       [SYSTEM POLICY] → [WORKFLOW POLICY] → [AGENT INSTRUCTION] →
       [USER REQUEST] → [RETRIEVED CONTEXT] → [TOOL OUTPUT]
    4. Logs the composed prompt (truncated for safety)

    Usage:
        middleware = PromptComposingMiddleware(
            system_policy="NEVER emit execution instructions.",
        )
        result = middleware.run(
            agent=actual_agent_runtime,
            instruction=agent_instruction,
            request=request,
            context=context,
            user_input="What's the best trade?",
            retrieved_content="Market data from API...",
        )
    """

    def __init__(
        self,
        system_policy: Optional[str] = None,
        workflow_policy: Optional[str] = None,
        max_retrieved_length: int = 8000,
        max_tool_output_length: int = 12000,
    ) -> None:
        self._system_policy = system_policy
        self._workflow_policy = workflow_policy
        self._max_retrieved_length = max_retrieved_length
        self._max_tool_output_length = max_tool_output_length

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
        """Compose the trust-layered prompt and execute the agent."""
        # Step 1: Evaluate retrieved content safety
        safety_report: Optional[RetrievalSafetyReport] = None
        if retrieved_content:
            safety_report = evaluate_retrieved_text(retrieved_content)
            if not safety_report.safe:
                logger.warning(
                    f"PromptComposingMiddleware: Retrieved content flagged as unsafe. "
                    f"Reasons: {', '.join(safety_report.reason_codes)}"
                )
                # Still include but mark as unsafe
                retrieved_content = (
                    f"[SAFETY WARNING: This content was flagged as potentially unsafe. "
                    f"Reasons: {', '.join(safety_report.reason_codes)}]\n\n"
                    f"{retrieved_content}"
                )
            # Truncate to configured max length
            if len(retrieved_content) > self._max_retrieved_length:
                retrieved_content = retrieved_content[:self._max_retrieved_length] + "\n\n... [truncated]"

        # Truncate tool output
        if tool_output and len(tool_output) > self._max_tool_output_length:
            tool_output = tool_output[:self._max_tool_output_length] + "\n\n... [truncated]"

        # Step 2: Build prompt context
        prompt_context = PromptContext(
            system_policy=self._system_policy,
            workflow_policy=self._workflow_policy,
            user_input=user_input,
            retrieved_content=retrieved_content,
            tool_output=tool_output,
            prior_steps=request.metadata.get("prior_steps"),
            refinement_feedback=self._extract_refinement_feedback(request.metadata),
        )

        # Step 3: Compose the full prompt
        composed_prompt = PromptComposer.compose(instruction, prompt_context)

        # Step 4: Log composed prompt (truncated for safety)
        log_preview = composed_prompt[:500]
        if len(composed_prompt) > 500:
            log_preview += "... [truncated]"
        logger.debug(
            f"PromptComposingMiddleware: Composed prompt ({len(composed_prompt)} chars). "
            f"Preview: {log_preview}"
        )

        # Step 5: Inject composed prompt into request
        augmented_request = replace(request, input_payload={
            **request.input_payload,
            "_system_prompt": composed_prompt,
        })

        # Step 6: Execute agent with composed prompt
        result = agent.run(request=augmented_request, context=context)

        # Step 7: Attach safety report to result metadata if available
        if safety_report:
            # Safety info is logged; result stands as-is
            pass

        return result

    @staticmethod
    def _extract_refinement_feedback(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract refinement feedback from request metadata if present."""
        if "refinement_iteration" not in metadata:
            return None
        return {
            "refinement_iteration": metadata.get("refinement_iteration"),
            "previous_score": metadata.get("previous_score"),
            "improvement_actions": metadata.get("improvement_actions", []),
            "focus_areas": metadata.get("focus_areas", []),
        }
