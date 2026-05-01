"""Page operator specialist for turning intents into safe UI actions."""

from __future__ import annotations

from typing import Any

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class PageOperatorAgent(SpecialistAgentBase):
    """LLM-backed page operator specialist.

    Reads allowed page_actions from the page context and maps a user goal
    to a valid PageActionPlan. Gracefully refuses if the action is
    missing, unsupported, or inherently unsafe.
    """

    agent_name = "page_operator_agent"

    SYSTEM_PROMPT = """You are HaruQuant's UI Operator specialist.
Your job is to map the user's UI request to one of the ALLOWED PAGE ACTIONS provided in the context.

Output schema (JSON only, no markdown):
{
  "summary": "<one sentence about what you are planning to do or why you cannot>",
  "findings": ["<specific finding about the request and allowed actions>"],
  "evidence": ["<specific evidence from context>"],
  "recommendation": "<next steps for the user>",
  "confidence": <integer 0-100>,
  "action_plan": {
    "action_id": "<string matching an allowed action, or null if impossible>",
    "parameters": { "<key>": "<value>" },
    "risk_level": "<view_only | local_ui | backend_safe | backend_risk>",
    "reasoning": "<why this action and parameters were chosen>"
  }
}

Rules:
- You may ONLY return an `action_id` that exactly matches one provided in the ALLOWED PAGE ACTIONS.
- If the requested action is not in the allowed list, set `action_plan` to null, set `confidence` to 100, and explain in `summary` that the page does not support it.
- If the required parameters for an action are missing from the user's prompt or context, set `action_plan` to null and ask for the parameters in `recommendation`.
- `risk_level` must exactly match the risk level declared by the allowed action.
"""

    _REQUIRED_KEYS = ("summary", "findings", "evidence", "recommendation", "confidence", "action_plan")

    def analyze(
        self,
        *,
        task_class: str,
        user_prompt: str,
        page_context: Any,
        tool_results: list[ToolExecutionResult] | None = None,
        tool_context: dict[str, object] | None = None,
    ) -> SpecialistAgentArtifact | None:
        
        intelligence = page_context.payload.payload.get("page_intelligence", {})
        allowed_actions = intelligence.get("actionAffordances", [])
        
        user_payload = {
            "task_class": task_class,
            "user_prompt": user_prompt,
            "allowed_actions": allowed_actions,
            "page_type": page_context.payload.page_type,
            "entity_refs": [ref.model_dump() for ref in page_context.payload.entity_refs],
        }

        # Fallback in case of failure or empty response
        fallback = SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="I cannot perform UI actions at this moment.",
            findings=["Page operator fallback triggered."],
            evidence=["page_actions_unavailable"],
            recommendation="Please perform the action manually.",
            confidence=0,
            action_plan=None,
        )

        if not allowed_actions:
            # If the page explicitly registered 0 actions, don't waste LLM tokens.
            return SpecialistAgentArtifact(
                agent_name=self.agent_name,
                task_class=task_class,
                summary="This page does not currently support automated actions.",
                findings=["No page actions are registered in the current context."],
                evidence=[f"page_type={page_context.payload.page_type}"],
                recommendation="You will need to perform this action manually.",
                confidence=100,
                action_plan=None,
            )

        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=fallback)

    def _extra_validate(self, raw: dict[str, Any]) -> bool:
        """Ensure action_plan conforms if present."""
        action_plan = raw.get("action_plan")
        if action_plan is None:
            return True
        if not isinstance(action_plan, dict):
            return False
        if "action_id" not in action_plan or "risk_level" not in action_plan or "parameters" not in action_plan:
            return False
        if action_plan.get("risk_level") not in {"view_only", "local_ui", "backend_safe", "backend_risk"}:
            return False
        return True

    def _validated_artifact(
        self,
        *,
        raw: dict[str, Any] | None,
        task_class: str,
        fallback: SpecialistAgentArtifact | None,
    ) -> SpecialistAgentArtifact | None:
        artifact = super()._validated_artifact(raw=raw, task_class=task_class, fallback=fallback)
        if artifact is not None and artifact is not fallback and raw:
            artifact.action_plan = raw.get("action_plan")
        return artifact
