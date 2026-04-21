"""Final responder that synthesizes specialist artifacts into one reply."""

from __future__ import annotations

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class FinalResponderAgent:
    agent_name = "final_responder_agent"

    def compose(
        self,
        *,
        user_prompt: str,
        task_class: str,
        page_context,
        tool_results: list[ToolExecutionResult],
        specialist_artifacts: list[SpecialistAgentArtifact],
        default_text: str,
    ) -> str:
        if not specialist_artifacts:
            return default_text

        lead = page_context.payload.summary.headline.rstrip(".")
        summaries = " ".join(artifact.summary for artifact in specialist_artifacts[:2])
        findings = " ".join(artifact.findings[0] for artifact in specialist_artifacts if artifact.findings)
        evidence = []
        for artifact in specialist_artifacts:
            evidence.extend(artifact.evidence[:2])
        evidence_text = "; ".join(evidence[:3])
        recommendations = [artifact.recommendation for artifact in specialist_artifacts if artifact.recommendation]
        recommendation = recommendations[0] if recommendations else None

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
        return " ".join(
            part for part in (
                default_text,
                evidence_text and f"Specialist evidence: {evidence_text}.",
            )
            if part
        )
