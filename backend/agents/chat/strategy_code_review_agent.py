"""Strategy code review specialist for validating and improving HaruQuant scripts."""

from __future__ import annotations

from typing import Any

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class StrategyCodeReviewAgent(SpecialistAgentBase):
    """LLM-backed strategy code review specialist.

    Performs deep technical review of HaruQuant strategy scripts.
    Checks for logic errors, performance bottlenecks, and adherence to the 
    HaruQuant Strategy API (on_init, on_bar, get_signal).
    """

    agent_name = "strategy_code_review_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Strategy Code Reviewer.
Your goal is to ensure HaruQuant strategy scripts are robust, efficient, and technically sound.

Output schema (JSON only):
{
  "summary": "<one sentence overview of the code quality>",
  "findings": [
    "FACT: <neutral observation about the code implementation>",
    "INTERPRETATION: <how this implementation affects strategy behavior>",
    "RISK: <a technical or logical risk, e.g., 'look-ahead bias', 'unhandled division by zero', 'excessive latency'>"
  ],
  "evidence": ["line_number: issue", ...],
  "recommendation": "<primary technical improvement, e.g., 'vectorize the cross-over logic', 'add stop-loss validation'>",
  "confidence": <integer 0-100>,
  "suggested_diff": "<optional git-style diff for a critical fix>"
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- Check specifically for: look-ahead bias, hardcoded magic numbers without parameters, and proper handling of indicators.
- If the strategy script is missing from context, set confidence to 0 and ask for the code.
- maximum 6 findings (2 sets of Fact/Interpretation/Risk).
"""

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        # Code might be in the page_context or passed via user_prompt (not available here)
        # or extracted from previous specialist artifacts (not available here yet).
        # We assume for now it's in the page_context metadata or we look for it in the tool_context.
        
        script = tool_context.get("strategy_script") or page_context.payload.payload.get("strategy_script")
        
        if not script:
            return None

        # Deterministic fallback
        deterministic = SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="Strategy code is available for technical review.",
            findings=["Analyzing strategy script for HaruQuant API compliance and logical robustness."],
            evidence=["script_available"],
            recommendation="Review the entry/exit logic carefully for potential look-ahead bias.",
            confidence=80,
        )

        user_payload = {
            "task_class": task_class,
            "strategy_script": script,
            "strategy_id": tool_context.get("strategy_id"),
        }

        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)
