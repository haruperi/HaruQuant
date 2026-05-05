"""Strategy retirement flow."""

from __future__ import annotations

from dataclasses import dataclass

from data.database import GovernanceRepository, StrategyRecord

from .models import StrategyLifecycleState


@dataclass(frozen=True)
class StrategyRetirementResult:
    strategy: StrategyRecord
    preserved: bool


class StrategyRetirementService:
    """Retire a strategy while preserving its registry metadata."""

    def __init__(self, repository: GovernanceRepository) -> None:
        self._repository = repository

    def retire(self, *, strategy_id: str) -> StrategyRetirementResult:
        strategy = self._repository.update_strategy_lifecycle_state(
            strategy_id=strategy_id,
            lifecycle_state=StrategyLifecycleState.RETIRED.value,
        )
        return StrategyRetirementResult(
            strategy=strategy,
            preserved=True,
        )
