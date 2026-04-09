"""Strategy promotion persistence."""

from __future__ import annotations

from dataclasses import dataclass

from apps.core import generate_id
from backend.db import GovernanceRepository, StrategyPromotionRecord, StrategyRecord

from .models import StrategyLifecycleState


@dataclass(frozen=True)
class PromotionPersistenceRequest:
    strategy_id: str
    from_state: StrategyLifecycleState
    to_state: StrategyLifecycleState
    evidence_bundle_id: str
    approver_1_id: str
    effective_at: str
    approver_2_id: str | None = None
    rationale: str | None = None


@dataclass(frozen=True)
class PromotionPersistenceResult:
    promotion: StrategyPromotionRecord
    strategy: StrategyRecord


class StrategyPromotionPersistenceService:
    """Persist promotion history and update the current strategy lifecycle state."""

    def __init__(self, repository: GovernanceRepository) -> None:
        self._repository = repository

    def persist(self, request: PromotionPersistenceRequest) -> PromotionPersistenceResult:
        promotion = self._repository.create_promotion(
            promotion_id=generate_id("promotion"),
            strategy_id=request.strategy_id,
            from_state=request.from_state.value,
            to_state=request.to_state.value,
            evidence_bundle_id=request.evidence_bundle_id,
            approver_1_id=request.approver_1_id,
            approver_2_id=request.approver_2_id,
            effective_at=request.effective_at,
            rationale=request.rationale,
        )
        strategy = self._repository.update_strategy_lifecycle_state(
            strategy_id=request.strategy_id,
            lifecycle_state=request.to_state.value,
        )
        return PromotionPersistenceResult(
            promotion=promotion,
            strategy=strategy,
        )
