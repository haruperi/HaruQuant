"""Report construction helpers for Research Department agents."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agents._shared.base_contracts import ConfidenceLevel, EvidenceItem
from .constants import DEPARTMENT_NAME, RESEARCH_AGENT_VERSION
from .contracts import ResearchReportArtifact, ValidationStatus
from .evidence import evidence_item_to_ref


def build_research_report(
    *,
    agent_name: str,
    report_type: str,
    symbol: str | None,
    timeframes: list[str],
    data_window: str,
    research_question: str | None,
    evidence: list[EvidenceItem],
    risks: list[str] | None = None,
    recommended_next_steps: list[str] | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    validation_status: ValidationStatus = ValidationStatus.NEEDS_MORE_EVIDENCE,
) -> ResearchReportArtifact:
    refs = [evidence_item_to_ref(item, agent_name) for item in evidence]
    return ResearchReportArtifact(
        report_id=str(uuid4()),
        report_type=report_type,
        agent_name=agent_name,
        department=DEPARTMENT_NAME,
        agent_version=RESEARCH_AGENT_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        research_question=research_question,
        symbol=symbol,
        timeframes=timeframes,
        data_window=data_window,
        data_sources=sorted({item.source for item in evidence}),
        evidence_refs=[ref.evidence_id for ref in refs],
        supporting_evidence=refs,
        risks=risks or [],
        recommended_next_steps=recommended_next_steps or [],
        confidence=confidence,
        validation_status=validation_status,
        audit={"agent_name": agent_name, "evidence_count": len(evidence)},
    )
