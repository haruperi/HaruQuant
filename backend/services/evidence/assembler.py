"""Lifecycle evidence bundle assembly."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.strategy_gov import StrategyLifecycleState

from .manifest import EvidenceArtifact, build_evidence_bundle_manifest


LIFECYCLE_EVIDENCE_BUNDLE_TYPES: dict[StrategyLifecycleState, str] = {
    StrategyLifecycleState.BACKTEST_QUALIFIED: "backtest_report",
    StrategyLifecycleState.ROBUSTNESS_QUALIFIED: "robustness_report",
    StrategyLifecycleState.PAPER_APPROVED: "paper_report",
    StrategyLifecycleState.LIVE_LIMITED: "live_limited_report",
    StrategyLifecycleState.LIVE_PRODUCTION: "live_production_report",
}


@dataclass(frozen=True)
class LifecycleEvidenceBundle:
    strategy_id: str
    lifecycle_state: StrategyLifecycleState
    manifest: dict[str, object]


def assemble_lifecycle_evidence_bundle(
    *,
    strategy_id: str,
    lifecycle_state: StrategyLifecycleState,
    artifacts: tuple[EvidenceArtifact, ...],
) -> LifecycleEvidenceBundle:
    """Assemble the evidence manifest for one lifecycle promotion stage."""

    bundle_type = LIFECYCLE_EVIDENCE_BUNDLE_TYPES.get(
        lifecycle_state,
        lifecycle_state.value.lower(),
    )
    manifest = build_evidence_bundle_manifest(
        bundle_type=bundle_type,
        strategy_id=strategy_id,
        lifecycle_state=lifecycle_state.value,
        artifacts=artifacts,
    )
    return LifecycleEvidenceBundle(
        strategy_id=strategy_id,
        lifecycle_state=lifecycle_state,
        manifest=manifest,
    )
