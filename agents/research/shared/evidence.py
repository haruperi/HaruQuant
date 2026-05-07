"""Evidence helpers for Research Department agents."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from agents._shared.base_contracts import ConfidenceLevel, EvidenceItem
from .contracts import ResearchEvidenceRef, SourceType


def make_evidence_id(agent_name: str, source: str, claim: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"haruquant:{agent_name}:{source}:{claim}"))


def evidence_item_to_ref(item: EvidenceItem, agent_name: str) -> ResearchEvidenceRef:
    value = item.value if isinstance(item.value, dict) else {}
    return ResearchEvidenceRef(
        evidence_id=value.get("evidence_id") or make_evidence_id(agent_name, item.source, item.description),
        source_type=SourceType(value.get("source_type", SourceType.COMPUTED.value)),
        source_name=item.source,
        claim_supported=item.description,
        evidence_summary=item.description,
        confidence=item.confidence if isinstance(item.confidence, ConfidenceLevel) else ConfidenceLevel.MEDIUM,
        reliability_score=float(value.get("reliability_score", 0.75)),
        freshness_score=float(value.get("freshness_score", 0.75)),
    )
