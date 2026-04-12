"""Promotion evidence validation."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common import ValidationError
from backend.data.database import EvidenceBundleRecord

from .models import StrategyLifecycleState


PROMOTION_EVIDENCE_REQUIREMENTS: dict[StrategyLifecycleState, frozenset[str]] = {
    StrategyLifecycleState.BACKTEST_QUALIFIED: frozenset({"backtest_report"}),
    StrategyLifecycleState.ROBUSTNESS_QUALIFIED: frozenset({"robustness_report"}),
    StrategyLifecycleState.PAPER_APPROVED: frozenset({"paper_report"}),
    StrategyLifecycleState.LIVE_LIMITED: frozenset({"live_limited_report"}),
    StrategyLifecycleState.LIVE_PRODUCTION: frozenset({"live_production_report"}),
}


@dataclass(frozen=True)
class PromotionEvidenceValidation:
    target_state: StrategyLifecycleState
    required_bundle_types: tuple[str, ...]
    provided_bundle_types: tuple[str, ...]


class PromotionEvidenceValidator:
    """Validate that promotion evidence covers the target lifecycle gate."""

    def validate(
        self,
        *,
        target_state: StrategyLifecycleState,
        evidence_bundles: tuple[EvidenceBundleRecord, ...],
    ) -> PromotionEvidenceValidation:
        required_types = PROMOTION_EVIDENCE_REQUIREMENTS.get(target_state, frozenset())
        provided_types = {bundle.bundle_type for bundle in evidence_bundles}

        missing_types = sorted(required_types - provided_types)
        if missing_types:
            raise ValidationError(
                "promotion_evidence_missing",
                "Promotion evidence is incomplete for the requested lifecycle target.",
                details={"target_state": target_state.value, "missing_bundle_types": missing_types},
            )

        return PromotionEvidenceValidation(
            target_state=target_state,
            required_bundle_types=tuple(sorted(required_types)),
            provided_bundle_types=tuple(sorted(provided_types)),
        )
