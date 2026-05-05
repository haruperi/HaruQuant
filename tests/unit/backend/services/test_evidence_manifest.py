from __future__ import annotations

from haruquant.strategy import EvidenceArtifact, build_evidence_bundle_manifest


def test_build_evidence_bundle_manifest_produces_stable_content_shape() -> None:
    manifest = build_evidence_bundle_manifest(
        bundle_type="paper_report",
        strategy_id="strat_001",
        lifecycle_state="PAPER_APPROVED",
        artifacts=(
            EvidenceArtifact(
                artifact_type="equity_curve",
                artifact_ref="memory://equity",
                artifact_hash="hash_equity",
            ),
            EvidenceArtifact(
                artifact_type="summary_report",
                artifact_ref="memory://summary",
                artifact_hash="hash_summary",
            ),
        ),
    )

    assert manifest["bundle_type"] == "paper_report"
    assert manifest["strategy_id"] == "strat_001"
    assert manifest["artifact_count"] == 2
    assert [item["artifact_type"] for item in manifest["artifacts"]] == [
        "equity_curve",
        "summary_report",
    ]
