"""Page operator specialist for turning intents into safe UI actions."""

from __future__ import annotations

import re
from typing import Any

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.ai_chat.page_action_planner import PageActionPlanner
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
    "risk_level": "<view_only | local_ui | backend_non_trading | trading_adjacent | prohibited>",
    "reasoning": "<why this action and parameters were chosen>"
  }
}

Rules:
- You may ONLY return an `action_id` that exactly matches one provided in the ALLOWED PAGE ACTIONS.
- If the requested action is not in the allowed list, set `action_plan` to null, set `confidence` to 100, and explain in `summary` that the page does not support it.
- If the required parameters for an action are missing from the user's prompt or context, set `action_plan` to null and ask for the parameters in `recommendation`.
- If you can infer a likely missing parameter from fuzzy wording, do NOT execute it directly.
  Instead return action_plan with that candidate so the system can ask the user to confirm first.
- `risk_level` must exactly match the risk level declared by the allowed action.
- For navigation requests, use `app_route_catalog` to infer likely paths from fuzzy names, misspellings, and natural language.
- Examples:
  - "go to chart page" -> navigate_app_page { "path": "/chart" }
  - "go to perfomance" -> navigate_app_page { "path": "/performance" }
  - "go home" -> navigate_app_page { "path": "/" }
- If several routes are plausible, do not guess. Ask a short disambiguation question with the top options.
- Never invent paths that are not listed in `app_route_catalog` unless the user explicitly supplied an absolute path beginning with "/".
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
        
        payload = page_context.payload.payload
        intelligence = payload.get("page_intelligence", {})
        allowed_actions = intelligence.get("actionAffordances", []) if isinstance(intelligence, dict) else []
        if not allowed_actions:
            allowed_actions = payload.get("page_actions", [])
        effective_prompt = self._confirmed_page_action_prompt(
            user_prompt=user_prompt,
            tool_context=tool_context or {},
        ) or user_prompt
        deterministic = PageActionPlanner().plan(
            user_prompt=effective_prompt,
            allowed_actions=allowed_actions if isinstance(allowed_actions, list) else [],
            page_type=page_context.payload.page_type,
            dom_snapshot=payload.get("dom") if isinstance(payload.get("dom"), dict) else None,
        )
        deterministic_payload = {
            "summary": deterministic.summary,
            "findings": list(deterministic.findings),
            "recommendation": deterministic.recommendation,
            "confidence": deterministic.confidence,
            "status": deterministic.audit_event.get("status"),
            "action_plan": deterministic.action_plan,
        }
        
        user_payload = {
            "task_class": task_class,
            "user_prompt": effective_prompt,
            "allowed_actions": allowed_actions,
            "app_route_catalog": PageActionPlanner.app_route_catalog(),
            "deterministic_result": deterministic_payload,
            "page_type": page_context.payload.page_type,
            "entity_refs": [ref.model_dump() for ref in page_context.payload.entity_refs],
        }
        dom_snapshot = payload.get("dom")
        if isinstance(dom_snapshot, dict):
            user_payload["visible_actionable_elements"] = (dom_snapshot.get("actionable_elements") or [])[:40]

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
            raw = self._call_llm_plan(user_payload=user_payload)
            no_actions = SpecialistAgentArtifact(
                agent_name=self.agent_name,
                task_class=task_class,
                summary="This page does not currently support automated actions.",
                findings=["No page actions are registered in the current context."],
                evidence=[f"page_type={page_context.payload.page_type}"],
                recommendation="You will need to perform this action manually.",
                confidence=100,
                action_plan=None,
            )
            return self._validated_artifact(raw=raw, task_class=task_class, fallback=no_actions)

        raw = self._call_llm_plan(user_payload=user_payload)
        if deterministic.action_plan is None and raw and isinstance(raw.get("action_plan"), dict):
            confirmation = self._confirmation_artifact_from_candidate(
                raw=raw,
                task_class=task_class,
                allowed_actions=allowed_actions if isinstance(allowed_actions, list) else [],
            )
            if confirmation is not None:
                return confirmation
        if raw is None:
            catalog_confirmation = self._route_catalog_confirmation_artifact(
                user_prompt=effective_prompt,
                task_class=task_class,
                deterministic_result=deterministic_payload,
                allowed_actions=allowed_actions if isinstance(allowed_actions, list) else [],
            )
            if catalog_confirmation is not None:
                return catalog_confirmation
            return SpecialistAgentArtifact(
                agent_name=self.agent_name,
                task_class=task_class,
                summary=deterministic.summary,
                findings=list(deterministic.findings),
                evidence=[*deterministic.evidence, f"audit_event={deterministic.audit_event['event_id']}"],
                recommendation=deterministic.recommendation,
                confidence=deterministic.confidence,
                action_plan=deterministic.action_plan,
            )
        if deterministic.action_plan and not raw.get("action_plan"):
            return SpecialistAgentArtifact(
                agent_name=self.agent_name,
                task_class=task_class,
                summary=deterministic.summary,
                findings=list(deterministic.findings),
                evidence=[*deterministic.evidence, f"audit_event={deterministic.audit_event['event_id']}"],
                recommendation=deterministic.recommendation,
                confidence=deterministic.confidence,
                action_plan=deterministic.action_plan,
            )
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
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=fallback)

    @staticmethod
    def _confirmed_page_action_prompt(*, user_prompt: str, tool_context: dict[str, object]) -> str | None:
        if user_prompt.strip().lower() not in {"yes", "y", "confirm", "confirmed", "correct", "do it", "proceed", "go ahead"}:
            return None
        recent_messages = tool_context.get("recent_messages")
        if not isinstance(recent_messages, list):
            return None
        for item in reversed(recent_messages):
            if not isinstance(item, dict) or item.get("role") != "assistant":
                continue
            content = str(item.get("content") or "")
            match = re.search(r"page_action_confirmation:\s*([^\s]+)\s+(\{.*?\})", content, flags=re.IGNORECASE)
            if not match:
                continue
            action_id = match.group(1)
            params = match.group(2)
            return f"confirmed page action {action_id} {params}"
        return None

    @staticmethod
    def _route_catalog_confirmation_artifact(
        *,
        user_prompt: str,
        task_class: str,
        deterministic_result: dict[str, Any],
        allowed_actions: list[dict[str, Any]],
    ) -> SpecialistAgentArtifact | None:
        if deterministic_result.get("status") != "needs_input":
            return None
        allowed_by_id = {str(action.get("id")): action for action in allowed_actions if action.get("id")}
        action = allowed_by_id.get("navigate_app_page") or allowed_by_id.get("navigate_performance_page")
        if not action:
            return None
        fuzzy = PageActionPlanner._infer_fuzzy_app_route(user_prompt.lower())
        if not fuzzy or fuzzy[1] < 0.72:
            return None
        route, confidence = fuzzy
        action_id = str(action.get("id"))
        risk_level = str(action.get("riskLevel") or action.get("risk_level") or "view_only")
        if risk_level != "view_only":
            return None
        parameters = {"path": route}
        if action_id == "navigate_performance_page" and route.startswith("/performance/"):
            parameters = {"path": route.removeprefix("/performance/")}
        summary = (
            f"Do you want me to navigate to `{parameters['path']}`? "
            f"page_action_confirmation: {action_id} {parameters}"
        )
        return SpecialistAgentArtifact(
            agent_name=PageOperatorAgent.agent_name,
            task_class=task_class,
            summary=summary,
            findings=["Route catalog inferred a likely navigation target after deterministic planning needed a path."],
            evidence=[f"candidate_action={action_id}", f"route_catalog_score={confidence:.2f}"],
            recommendation="Reply yes to confirm, or tell me the correct target.",
            confidence=max(72, min(88, int(confidence * 100))),
            action_plan=None,
        )

    @staticmethod
    def _confirmation_artifact_from_candidate(
        *,
        raw: dict[str, Any],
        task_class: str,
        allowed_actions: list[dict[str, Any]],
    ) -> SpecialistAgentArtifact | None:
        action_plan = raw.get("action_plan")
        if not isinstance(action_plan, dict):
            return None
        action_id = str(action_plan.get("action_id") or "")
        parameters = action_plan.get("parameters")
        risk_level = str(action_plan.get("risk_level") or "")
        allowed_by_id = {str(action.get("id")): action for action in allowed_actions if action.get("id")}
        allowed = allowed_by_id.get(action_id)
        if not allowed or not isinstance(parameters, dict):
            return None
        allowed_risk = str(allowed.get("riskLevel") or allowed.get("risk_level") or "")
        if risk_level != allowed_risk or risk_level not in {"view_only", "local_ui"}:
            return None
        target = parameters.get("path") or parameters.get("label") or parameters.get("selector") or parameters
        summary = (
            f"Do you want me to run `{action_id}` with `{parameters}`? "
            f"page_action_confirmation: {action_id} {parameters}"
        )
        if action_id in {"navigate_app_page", "navigate_performance_page"} and parameters.get("path"):
            summary = (
                f"Do you want me to navigate to `{parameters['path']}`? "
                f"page_action_confirmation: {action_id} {parameters}"
            )
        return SpecialistAgentArtifact(
            agent_name=PageOperatorAgent.agent_name,
            task_class=task_class,
            summary=summary,
            findings=["Fuzzy page-action inference needs user confirmation before execution."],
            evidence=[f"candidate_action={action_id}", f"candidate_target={target}"],
            recommendation="Reply yes to confirm, or tell me the correct target.",
            confidence=int(float(raw.get("confidence") or 82)),
            action_plan=None,
        )

    def _extra_validate(self, raw: dict[str, Any]) -> bool:
        """Ensure action_plan conforms if present."""
        action_plan = raw.get("action_plan")
        if action_plan is None:
            return True
        if not isinstance(action_plan, dict):
            return False
        if "action_id" not in action_plan or "risk_level" not in action_plan or "parameters" not in action_plan:
            return False
        if action_plan.get("risk_level") not in {"view_only", "local_ui", "backend_non_trading", "trading_adjacent", "prohibited"}:
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
