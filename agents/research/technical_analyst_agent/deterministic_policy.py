"""Deterministic policy for the Technical Analyst Agent."""

from __future__ import annotations

from agents._shared.base_contracts import AgentDecision, EvidenceItem, LLMAnalysis
from agents.research.shared.research_agent import make_research_decision

from .service import CONFIG


def make_final_decision(evidence: list[EvidenceItem], llm_analysis: LLMAnalysis | None) -> AgentDecision:
    return make_research_decision(config=CONFIG, evidence=evidence, llm_analysis=llm_analysis)
