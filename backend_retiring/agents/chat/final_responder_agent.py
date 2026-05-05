"""Final responder that synthesizes specialist artifacts into one reply."""

from __future__ import annotations

import json
from typing import Any

from backend_retiring.agents.runtime import LLMRuntimeError, create_llm_runtime
from haruquant.utils import logger
from backend_retiring.config.agent_model import get_model_for_tier
from backend_retiring.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend_retiring.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class FinalResponderAgent:
    """Composes final conversational answers from specialist artifacts.

    If any specialist artifact has high confidence, uses a fast LLM to synthesize
    a coherent, natural response. Otherwise falls back to deterministic templating.
    """

    agent_name = "final_responder_agent"

    SYSTEM_PROMPT = """You are the HaruQuant AI Copilot final response composer.
Given the specialist findings below, write one high-quality, professional trading-assistant answer.

Response Structure:
1. One concise summary paragraph.
2. An analysis section that synthesizes specialist FACTs and INTERPRETATIONs.
3. A safety section that highlights specific RISK findings.
4. One clear, concrete "Next Step".

Rules:
- 2-4 short paragraphs maximum.
- Do NOT use headers like "Summary:" or "Analysis:". Use natural transitions.
- Maintain a strictly professional, evidence-led tone.
- Distinguish clearly between facts (what we see) and interpretation (what we think).
- Highlight specific metrics and evidence from the specialists.
- End with one concrete next action.
- Do not claim any action was executed.
"""

    def compose(
        self,
        *,
        user_prompt: str,
        task_class: str,
        page_context: Any,
        tool_results: list[ToolExecutionResult],
        specialist_artifacts: list[SpecialistAgentArtifact],
        default_text: str,
    ) -> str:
        if not specialist_artifacts:
            return default_text

        # Check if we should use LLM based on confidence
        if any(artifact.confidence >= 70 for artifact in specialist_artifacts):
            user_payload = self._build_user_payload(
                user_prompt=user_prompt,
                task_class=task_class,
                specialist_artifacts=specialist_artifacts,
                default_text=default_text,
            )
            llm_response = self._call_llm_compose(user_payload=user_payload)
            if llm_response:
                return llm_response

        # Deterministic fallback path
        return self._deterministic_compose(
            task_class=task_class,
            page_context=page_context,
            specialist_artifacts=specialist_artifacts,
            default_text=default_text,
        )

    def _call_llm_compose(self, *, user_payload: dict[str, Any]) -> str | None:
        """Call the fast LLM to compose the final response."""
        try:
            runtime = create_llm_runtime(
                model=get_model_for_tier("fast"),
                json_mode=False,
                temperature=0.2,
                max_output_tokens=800,
            )
            result = runtime._call_llm(
                self.SYSTEM_PROMPT,
                json.dumps(user_payload, ensure_ascii=False, default=str),
            )
            content = str(result.get("content", "")).strip()
            if content:
                return content
            return None
        except (LLMRuntimeError, Exception):
            logger.debug(f"{self.agent_name}: LLM composition failed — using deterministic fallback")
            return None

    @staticmethod
    def _build_user_payload(
        *,
        user_prompt: str,
        task_class: str,
        specialist_artifacts: list[SpecialistAgentArtifact],
        default_text: str,
    ) -> dict[str, Any]:
        return {
            "user_prompt": user_prompt,
            "task_class": task_class,
            "specialist_artifacts": [
                {
                    "agent": artifact.agent_name,
                    "summary": artifact.summary,
                    "findings": artifact.findings,
                    "evidence": artifact.evidence,
                    "sources": artifact.sources,
                    "recommendation": artifact.recommendation,
                }
                for artifact in specialist_artifacts
            ],
            "default_fallback_text": default_text,
        }

    @staticmethod
    def _deterministic_compose(
        *,
        task_class: str,
        page_context: Any,
        specialist_artifacts: list[SpecialistAgentArtifact],
        default_text: str,
    ) -> str:
        lead = page_context.payload.summary.headline.rstrip(".")
        summaries = " ".join(artifact.summary for artifact in specialist_artifacts[:2])
        findings_list = []
        for artifact in specialist_artifacts:
            for f in artifact.findings:
                clean_f = f.replace("FACT:", "").replace("INTERPRETATION:", "").replace("RISK:", "").strip()
                findings_list.append(clean_f)
        findings = " ".join(findings_list[:3])
        
        evidence = []
        for artifact in specialist_artifacts:
            evidence.extend(artifact.evidence[:2])
        evidence_text = "; ".join(evidence[:3])
        
        sources = []
        for artifact in specialist_artifacts:
            sources.extend(artifact.sources[:2])
        source_text = ", ".join(dict.fromkeys(sources))
        
        recommendations = [artifact.recommendation for artifact in specialist_artifacts if artifact.recommendation]
        recommendation = recommendations[0] if recommendations else None

        if task_class == "strategy_creation":
            return " ".join(
                part for part in (
                    summaries,
                    findings and f"Key logic drivers: {findings}",
                    recommendation,
                )
                if part
            )
        if task_class == "knowledge_dialogue":
            return " ".join(
                part for part in (
                    summaries,
                    findings and f"The most relevant documentation says {findings}",
                    source_text and f"Relevant sources: {source_text}.",
                    recommendation,
                    default_text,
                )
                if part
            )
        if task_class == "comparison":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    summaries,
                    findings and f"The strongest comparison evidence is {findings}",
                    evidence_text and f"Evidence in scope: {evidence_text}.",
                    default_text,
                    recommendation,
                )
                if part
            )
        if task_class == "risk_explanation":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    summaries,
                    findings and f"Current risk evidence points to {findings}",
                    evidence_text and f"Grounding: {evidence_text}.",
                    default_text,
                    recommendation,
                )
                if part
            )
        if task_class == "diagnostic":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    summaries,
                    findings and f"The clearest diagnostic signal is {findings}",
                    evidence_text and f"Evidence in scope: {evidence_text}.",
                    default_text,
                    recommendation,
                )
                if part
            )
        if task_class == "page_operation":
            return " ".join(
                part for part in (
                    summaries,
                    recommendation,
                )
                if part
            )
        return " ".join(
            part for part in (
                default_text,
                evidence_text and f"Specialist evidence: {evidence_text}.",
            )
            if part
        )
