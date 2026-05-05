from __future__ import annotations

from services.strategy.evidence import EvidenceArtifact, assemble_lifecycle_evidence_bundle
from services.strategy.governance import StrategyLifecycleState


def test_assemble_lifecycle_evidence_bundle_uses_target_state_bundle_type() -> None:
    bundle = assemble_lifecycle_evidence_bundle(
        strategy_id="strat_001",
        lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
        artifacts=(
            EvidenceArtifact(
                artifact_type="paper_report",
                artifact_ref="memory://paper",
                artifact_hash="hash_paper",
            ),
        ),
    )

    assert bundle.strategy_id == "strat_001"
    assert bundle.lifecycle_state is StrategyLifecycleState.PAPER_APPROVED
    assert bundle.manifest["bundle_type"] == "paper_report"
    assert bundle.manifest["artifact_count"] == 1
