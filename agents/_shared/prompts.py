"""Shared prompt composition primitives for HaruQuant agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CoT_SEPARATOR = "\n\nReasoning scratchpad is private; final answers must show conclusions and evidence only.\n\n"


@dataclass(frozen=True)
class PromptContext:
    system_policy: str | None = None
    workflow_policy: str | None = None
    user_input: str | None = None
    retrieved_content: str | None = None
    tool_output: str | None = None
    prior_steps: dict[str, Any] = field(default_factory=dict)
    refinement_feedback: dict[str, Any] = field(default_factory=dict)


def _format_section(label: str, value: Any) -> str:
    if value is None or value == "" or value == {}:
        return ""
    return f"[{label}]\n{value}".strip()


class PromptComposer:
    """Compose prompts in a fixed trust order."""

    @staticmethod
    def compose(agent_instruction: str, context: PromptContext | None = None) -> str:
        context = context or PromptContext()
        sections = [
            _format_section("SYSTEM POLICY", context.system_policy),
            _format_section("WORKFLOW POLICY", context.workflow_policy),
            _format_section("AGENT INSTRUCTION", agent_instruction),
            _format_section("PRIOR WORKFLOW STEPS", context.prior_steps),
            _format_section("USER REQUEST", context.user_input),
            _format_section("RETRIEVED CONTEXT - UNVERIFIED", context.retrieved_content),
            _format_section("TOOL OUTPUT - RAW DATA", context.tool_output),
            _format_section("REFINEMENT FEEDBACK", context.refinement_feedback),
        ]
        return "\n\n".join(section for section in sections if section)


def assemble_agent_prompt(agent_instruction: str, **context: Any) -> str:
    """Convenience wrapper for examples and lightweight prompt tests."""

    return PromptComposer.compose(agent_instruction, PromptContext(**context))


__all__ = [
    "CoT_SEPARATOR",
    "PromptComposer",
    "PromptContext",
    "assemble_agent_prompt",
]
