"""Strategy registry service."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils import ErrorDescriptor, ValidationError
from backend.data.database import GovernanceRepository, StrategyRecord

from .models import StrategyLifecycleState


_STRATEGY_ID_REQUIRED = ErrorDescriptor(
    code=4042,
    name="STRATEGY_ID_REQUIRED",
    message="Strategy registration requires strategy_id.",
    domain="strategy_governance",
)
_STRATEGY_NAME_REQUIRED = ErrorDescriptor(
    code=4043,
    name="STRATEGY_NAME_REQUIRED",
    message="Strategy registration requires strategy_name.",
    domain="strategy_governance",
)


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
            raise ValidationError(_STRATEGY_ID_REQUIRED)
        if not request.strategy_name:
            raise ValidationError(_STRATEGY_NAME_REQUIRED)

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

