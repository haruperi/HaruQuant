"""Strategy registry service."""

from __future__ import annotations

from dataclasses import dataclass

from apps.core import ValidationError
from backend.db import GovernanceRepository, StrategyRecord

from .models import StrategyLifecycleState


@dataclass(frozen=True)
class StrategyRegistrationRequest:
    strategy_id: str
    strategy_name: str
    strategy_family: str
    code_hash: str
    parameter_hash: str
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.RESEARCH
    owner_id: str | None = None


class StrategyRegistryService:
    """Register and read strategy lifecycle entries."""

    def __init__(self, repository: GovernanceRepository) -> None:
        self._repository = repository

    def register(self, request: StrategyRegistrationRequest) -> StrategyRecord:
        if not request.strategy_id:
            raise ValidationError("strategy_id_required", "Strategy registration requires strategy_id.")
        if not request.strategy_name:
            raise ValidationError("strategy_name_required", "Strategy registration requires strategy_name.")

        return self._repository.create_strategy(
            strategy_id=request.strategy_id,
            strategy_name=request.strategy_name,
            strategy_family=request.strategy_family,
            current_lifecycle_state=request.lifecycle_state.value,
            code_hash=request.code_hash,
            parameter_hash=request.parameter_hash,
            owner_id=request.owner_id,
        )

    def get(self, strategy_id: str) -> StrategyRecord | None:
        return self._repository.get_strategy(strategy_id)

