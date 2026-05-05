from __future__ import annotations

import pytest

from backend.data.database import EvidenceBundleRecord
from services.strategy.governance import PromotionEvidenceValidator, StrategyLifecycleState


def test_promotion_evidence_validator_accepts_required_bundle_type() -> None:
    result = PromotionEvidenceValidator().validate(
        target_state=StrategyLifecycleState.PAPER_APPROVED,
        evidence_bundles=(
            EvidenceBundleRecord(
                evidence_bundle_id="evidence_001",
                workflow_id="wf_001",
                bundle_type="paper_report",
                summary="paper evidence",
                content_ref=None,
                content_hash="hash_001",
                freshness_status="fresh",
                created_at="2026-04-09T10:00:00Z",
            ),
        ),
    )

    assert result.target_state is StrategyLifecycleState.PAPER_APPROVED
    assert result.required_bundle_types == ("paper_report",)


def test_promotion_evidence_validator_rejects_missing_required_bundle_type() -> None:
    with pytest.raises(Exception):
        PromotionEvidenceValidator().validate(
            target_state=StrategyLifecycleState.LIVE_LIMITED,
            evidence_bundles=(
                EvidenceBundleRecord(
                    evidence_bundle_id="evidence_001",
                    workflow_id="wf_001",
                    bundle_type="paper_report",
                    summary="paper evidence",
                    content_ref=None,
                    content_hash="hash_001",
                    freshness_status="fresh",
                    created_at="2026-04-09T10:00:00Z",
                ),
            ),
        )
