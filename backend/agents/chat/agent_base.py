"""Shared base class for LLM-backed chat specialist agents."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.runtime import LLMRuntimeError, create_llm_runtime
from services.utils.logger import logger
from backend.config.agent_model import get_model_for_tier
from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class SpecialistAgentBase:
    """Foundation for bounded LLM specialist agents.

    Subclasses implement:
    - ``SYSTEM_PROMPT`` — the task-specific LLM instruction.
    - ``agent_name`` — used in ``SpecialistAgentArtifact``.
    - ``_build_user_payload()`` — extracts relevant tool data for the LLM.
    - ``_deterministic_artifact()`` — fallback when LLM is unavailable or invalid.
    - Optional ``_extra_validate()`` — agent-specific extra field checks.
    """

    # Override in subclass
    SYSTEM_PROMPT: str = ""
    agent_name: str = "specialist_agent"

    # Schema keys the LLM response must include (validated before use)
    _REQUIRED_KEYS: tuple[str, ...] = ("summary", "findings", "evidence", "recommendation", "confidence")

    def _call_llm_plan(
        self,
        *,
        user_payload: dict[str, Any],
        model: str | None = None,
        max_output_tokens: int = 600,
    ) -> dict[str, Any] | None:
        """Call the fast LLM with this agent's system prompt.

        Returns the parsed JSON dict or None on any failure.
        Never raises — failures are silently absorbed and trigger the
        deterministic fallback path.
        """
        effective_model = model or get_model_for_tier("fast")
        try:
            runtime = create_llm_runtime(
                model=effective_model,
                json_mode=True,
                temperature=0.0,
                max_output_tokens=max_output_tokens,
            )
            result = runtime._call_llm(
                self.SYSTEM_PROMPT,
                json.dumps(user_payload, ensure_ascii=False, default=str),
            )
            content = result.get("content", "")
            if not content:
                return None
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                return None
            if parsed.get("_parse_error"):
                return None
            return parsed
        except (LLMRuntimeError, json.JSONDecodeError, Exception):
            logger.debug(f"{self.agent_name}: LLM plan call failed — using deterministic fallback")
            return None

    def _validated_artifact(
        self,
        *,
        raw: dict[str, Any] | None,
        task_class: str,
        fallback: SpecialistAgentArtifact | None,
    ) -> SpecialistAgentArtifact | None:
        """Validate the raw LLM output and build a SpecialistAgentArtifact.

        Returns the fallback if raw is None or fails validation.
        """
        if raw is None:
            return fallback

        # Required keys present?
        for key in self._REQUIRED_KEYS:
            if key not in raw:
                logger.debug(f"{self.agent_name}: LLM output missing key '{key}' — using fallback")
                return fallback

        # Type checks
        summary = raw.get("summary")
        findings = raw.get("findings")
        evidence = raw.get("evidence")
        recommendation = raw.get("recommendation")
        confidence = raw.get("confidence")

        if not isinstance(summary, str) or not summary.strip():
            return fallback
        if not isinstance(findings, list) or not findings or len(findings) > 8:
            return fallback
        if not isinstance(evidence, list):
            return fallback
        if not isinstance(recommendation, str) or not recommendation.strip():
            return fallback
        if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 100):
            return fallback

        # Validate individual finding strings
        validated_findings = [str(f) for f in findings if isinstance(f, str) and f.strip()]
        if not validated_findings:
            return fallback

        validated_evidence = [str(e) for e in evidence if isinstance(e, str) and e.strip()]
        sources = [str(s) for s in (raw.get("sources") or []) if isinstance(s, str) and s.strip()]
        missing_data = [str(m) for m in (raw.get("missing_data") or []) if isinstance(m, str) and m.strip()]

        # Agent-specific extra validation (subclass can override)
        if not self._extra_validate(raw):
            return fallback

        artifact = SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=summary.strip(),
            findings=validated_findings,
            evidence=validated_evidence or [f"agent={self.agent_name}"],
            sources=sources,
            recommendation=recommendation.strip(),
            confidence=int(float(confidence)),
        )
        if missing_data:
            # Inject missing_data as a note in sources for transparency
            artifact = SpecialistAgentArtifact(
                agent_name=artifact.agent_name,
                task_class=artifact.task_class,
                summary=artifact.summary,
                findings=artifact.findings,
                evidence=artifact.evidence,
                sources=list(dict.fromkeys([*artifact.sources, *[f"missing:{m}" for m in missing_data[:3]]])),
                recommendation=artifact.recommendation,
                confidence=artifact.confidence,
            )
        return artifact

    def _extra_validate(self, raw: dict[str, Any]) -> bool:  # noqa: ARG002
        """Subclass hook for extra field validation. Return False to reject."""
        return True

    # ── Tool result helpers ──────────────────────────────────────────────────

    @staticmethod
    def _get_result(tool_results: list[ToolExecutionResult], tool_name: str) -> ToolExecutionResult | None:
        for result in tool_results:
            if result.tool_name == tool_name and result.success:
                return result
        return None

    @staticmethod
    def _headline_metrics(metrics: dict[str, object], limit: int = 6) -> list[str]:
        if not isinstance(metrics, dict):
            return []
        return [f"{key}={value}" for key, value in list(metrics.items())[:limit]]


__all__ = ["SpecialistAgentBase"]
