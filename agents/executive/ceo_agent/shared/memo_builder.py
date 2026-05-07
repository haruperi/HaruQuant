"""Executive memo assembly helpers."""

from __future__ import annotations

from typing import Any


def synthesize_evidence_summary(*, specialist_responses: dict[str, Any], evidence_refs: list[str]) -> dict[str, Any]:
    supporting: list[str] = []
    contradicting: list[str] = []
    weak: list[str] = []
    for name, response in specialist_responses.items():
        status = response.get("status") if isinstance(response, dict) else getattr(response, "status", None)
        if status in {"blocked", "rejected", "failed"}:
            contradicting.append(name)
        elif status:
            supporting.append(name)
        else:
            weak.append(name)
    return {
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,
        "weak_or_unstructured_evidence": weak,
        "evidence_refs": evidence_refs,
    }
