"""ReAct agent runtime — Thought → Action → Observation → Final Answer loop."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional, Protocol

from backend.agents.react.react_prompt import REACT_SYSTEM_INSTRUCTION, REACT_STEP_SEPARATOR
from backend.agents.runtime.llm_runtime import LLMRuntime, LLMRuntimeError
from backend.agents.runtime.runner import (
    ADKRunRequest,
    AgentExecutionContext,
    AgentExecutionResult,
)
from backend.common.logger import logger


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────

class ToolCallable(Protocol):
    """A tool that can be called by the ReAct loop."""
    def __call__(self, **kwargs: Any) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class ReActStep:
    """One step in the ReAct loop."""
    thought: str = ""
    action_name: str = ""
    action_args: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    is_final: bool = False
    final_json: str = ""


# ──────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────

# Regex patterns to parse LLM output
_THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?:\nAction:|\nFinal:|$)", re.DOTALL)
_ACTION_RE = re.compile(r"Action:\s*(\w+)\((.*?)\)", re.DOTALL)
_FINAL_RE = re.compile(r"Final:\s*(.+)$", re.DOTALL)


def parse_react_output(text: str) -> ReActStep:
    """Parse LLM output into a ReAct step."""
    text = text.strip()

    # Extract thought
    thought_match = _THOUGHT_RE.search(text)
    thought = thought_match.group(1).strip() if thought_match else ""

    # Check for Final
    final_match = _FINAL_RE.search(text)
    if final_match:
        return ReActStep(
            thought=thought,
            is_final=True,
            final_json=final_match.group(1).strip(),
        )

    # Check for Action
    action_match = _ACTION_RE.search(text)
    if action_match:
        action_name = action_match.group(1)
        args_str = action_match.group(2).strip()
        try:
            action_args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            action_args = {"_raw_args": args_str}
        return ReActStep(
            thought=thought,
            action_name=action_name,
            action_args=action_args,
        )

    # Fallback: treat entire text as thought
    return ReActStep(thought=text)


# ──────────────────────────────────────────────────────────────
# ReAct Agent Runtime
# ──────────────────────────────────────────────────────────────

class ReActAgentRuntime:
    """ReAct-style agent runtime: Thought → Action → Observation → Final.

    Wraps an LLMRuntime and a tool registry to implement the
    tool-aware reasoning loop described in Playbook §4.

    Usage:
        tools = {"get_price": lambda symbol: {"price": 1.0850}}
        react = ReActAgentRuntime(llm_runtime, tools, max_steps=10)
        result = react.run(request=request, context=context)
    """

    def __init__(
        self,
        llm_runtime: LLMRuntime,
        tools: Optional[Dict[str, ToolCallable]] = None,
        max_steps: int = 10,
        step_timeout_seconds: float = 30.0,
    ) -> None:
        self._llm = llm_runtime
        self._tools = tools or {}
        self._max_steps = max(max_steps, 1)
        self._step_timeout = step_timeout_seconds
        self._step_log: List[ReActStep] = []

    @property
    def step_log(self) -> List[ReActStep]:
        """Return the log of all ReAct steps for this run."""
        return list(self._step_log)

    def run(
        self,
        *,
        request: ADKRunRequest,
        context: AgentExecutionContext,
    ) -> AgentExecutionResult:
        """Execute the ReAct loop until Final or max steps."""
        self._step_log.clear()

        # Build the ReAct system prompt with tool descriptions
        tool_desc = self._build_tool_descriptions()
        system_prompt = (
            f"{REACT_SYSTEM_INSTRUCTION}\n\n"
            f"AVAILABLE TOOLS:\n{tool_desc}\n\n"
            f"TASK INPUT:\n{json.dumps(request.input_payload, ensure_ascii=False)}"
        )

        conversation: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        total_prompt_tokens = 0
        total_completion_tokens = 0

        for step_num in range(self._max_steps):
            # Build user message for this step
            if step_num == 0:
                user_message = json.dumps(request.input_payload, ensure_ascii=False)
            else:
                # Build conversation context for the user message
                user_message = "\n".join(
                    f"{'Assistant' if i % 2 == 0 else 'Observation'}: {c.get('content', '')}"
                    for i, c in enumerate(conversation[1:])
                ) if len(conversation) > 1 else json.dumps(request.input_payload, ensure_ascii=False)

            # Update the request with our custom system prompt
            augmented_request = ADKRunRequest(
                workflow_id=request.workflow_id,
                correlation_id=request.correlation_id,
                agent_name=request.agent_name,
                input_payload={
                    **request.input_payload,
                    "_system_prompt": REACT_SYSTEM_INSTRUCTION + "\n\nAVAILABLE TOOLS:\n" + self._build_tool_descriptions(),
                },
            )

            # Call LLM — use _call_llm directly for raw text output
            try:
                llm_response = self._llm._call_llm(
                    system_prompt=augmented_request.input_payload["_system_prompt"],
                    user_message=user_message,
                )
            except LLMRuntimeError as exc:
                logger.error(f"ReActAgentRuntime: LLM call failed at step {step_num}: {exc}")
                return AgentExecutionResult(
                    output_payload={
                        "error": f"LLM call failed at step {step_num}: {exc}",
                        "contract_type": request.input_payload.get("contract_type", "unknown"),
                        "schema_version": "1.0.0",
                    },
                    final_state="ERROR",
                    tool_calls=tuple({"step": s, "thought": s.thought, "action": s.action_name} for s in self._step_log),
                    token_usage=None,
                )

            # Parse LLM output
            content = llm_response.get("content", "")

            step = parse_react_output(content)
            if not step.thought:
                step = replace(step, thought=f"Step {step_num + 1}")
            self._step_log.append(step)

            # Track tokens
            total_prompt_tokens += llm_response.get("prompt_tokens", 0)
            total_completion_tokens += llm_response.get("completion_tokens", 0)

            if step.is_final:
                # Parse final JSON
                try:
                    final_payload = json.loads(step.final_json)
                except json.JSONDecodeError:
                    final_payload = {
                        "_raw_final": step.final_json,
                        "contract_type": request.input_payload.get("contract_type", "unknown"),
                        "schema_version": "1.0.0",
                        "_parse_error": "Final output was not valid JSON",
                    }

                logger.info(
                    f"ReActAgentRuntime: Final answer reached at step {step_num + 1}, "
                    f"total_tokens={total_prompt_tokens + total_completion_tokens}"
                )

                return AgentExecutionResult(
                    output_payload=final_payload,
                    final_state="COMPLETED",
                    tool_calls=tuple({
                        "step": i + 1,
                        "thought": s.thought,
                        "action": s.action_name,
                        "observation": s.observation,
                    } for i, s in enumerate(self._step_log)),
                    token_usage={
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_prompt_tokens + total_completion_tokens,
                    },
                )

            # Execute action
            observation = self._execute_action(step)
            self._step_log[-1] = replace(self._step_log[-1], observation=observation)

            # Append observation to conversation for next LLM call
            conversation.append({
                "role": "assistant",
                "content": f"Thought: {step.thought}\nAction: {step.action_name}({json.dumps(step.action_args)})",
            })
            conversation.append({
                "role": "user",
                "content": f"Observation: {observation}",
            })

        # Max steps reached — produce best-effort final
        logger.warning(
            f"ReActAgentRuntime: Max steps ({self._max_steps}) reached without Final. "
            f"Producing best-effort answer."
        )

        return AgentExecutionResult(
            output_payload={
                "error": f"Max steps ({self._max_steps}) reached without Final answer",
                "contract_type": request.input_payload.get("contract_type", "unknown"),
                "schema_version": "1.0.0",
                "_step_log": [{
                    "thought": s.thought,
                    "action": s.action_name,
                    "observation": s.observation,
                } for s in self._step_log],
            },
            final_state="COMPLETED",
            tool_calls=tuple({
                "step": i + 1,
                "thought": s.thought,
                "action": s.action_name,
                "observation": s.observation,
            } for i, s in enumerate(self._step_log)),
            token_usage={
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            },
        )

    def _build_tool_descriptions(self) -> str:
        """Build a text description of all available tools."""
        if not self._tools:
            return "(No tools available)"
        lines = []
        for name, func in self._tools.items():
            doc = func.__doc__ or "No description available."
            lines.append(f"- {name}: {doc.strip()}")
        return "\n".join(lines)

    def _execute_action(self, step: ReActStep) -> str:
        """Execute a tool action and return the observation."""
        if not step.action_name:
            return "Error: No action specified."

        tool = self._tools.get(step.action_name)
        if tool is None:
            available = ", ".join(self._tools.keys())
            return f"Error: Unknown tool '{step.action_name}'. Available: {available}"

        try:
            result = tool(**step.action_args)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return f"Error executing {step.action_name}: {exc}"
