"""Runtime permission checks for strategy lifecycle state."""

from __future__ import annotations

from typing import Literal, Optional

from data.database import GovernanceRepository
from data.database.sqlite.database_operations import DatabaseManager

from .catalog import governance_strategy_id


StrategyRuntimeContext = Literal["backtest", "optimization", "paper", "live", "live_production"]

_ALLOWED_STATES: dict[StrategyRuntimeContext, set[str]] = {
    "backtest": {
        "RESEARCH",
        "BACKTEST_QUALIFIED",
        "ROBUSTNESS_QUALIFIED",
        "PAPER_APPROVED",
        "LIVE_LIMITED",
        "LIVE_PRODUCTION",
    },
    "optimization": {
        "RESEARCH",
        "BACKTEST_QUALIFIED",
        "ROBUSTNESS_QUALIFIED",
        "PAPER_APPROVED",
        "LIVE_LIMITED",
        "LIVE_PRODUCTION",
    },
    "paper": {"PAPER_APPROVED", "LIVE_LIMITED", "LIVE_PRODUCTION"},
    "live": {"LIVE_LIMITED", "LIVE_PRODUCTION"},
    "live_production": {"LIVE_PRODUCTION"},
}


class StrategyPermissionError(PermissionError):
    """Raised when a strategy lifecycle state does not permit a runtime context."""


class StrategyRuntimePermissionService:
    """Authorize strategy execution contexts from governance lifecycle state."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        governance_repository: Optional[GovernanceRepository] = None,
    ) -> None:
        self.db = db_manager or DatabaseManager()
        self.governance = governance_repository or GovernanceRepository(self.db.db_path)

    def assert_strategy_allowed(
        self,
        *,
        strategy_id: int,
        context: StrategyRuntimeContext,
    ) -> None:
        strategy = self.db.get_strategy(strategy_id)
        if strategy is None:
            raise LookupError(f"Strategy {strategy_id} not found")
        gov_id = strategy.get("governance_strategy_id") or governance_strategy_id(
            int(strategy["user_id"]),
            strategy_id,
        )
        record = self.governance.get_strategy(str(gov_id))
        if record is None:
            raise StrategyPermissionError(
                f"Strategy {strategy_id} has no governance registration and cannot run in {context}."
            )

        state = record.current_lifecycle_state.upper()
        allowed = _ALLOWED_STATES[context]
        if state not in allowed:
            required = ", ".join(sorted(allowed))
            raise StrategyPermissionError(
                f"Strategy {strategy_id} is in lifecycle state '{state}'. "
                f"Context '{context}' requires one of: {required}."
            )


def assert_strategy_allowed(
    strategy_id: int,
    context: StrategyRuntimeContext,
    *,
    db_manager: Optional[DatabaseManager] = None,
    governance_repository: Optional[GovernanceRepository] = None,
) -> None:
    """Convenience wrapper for one-off runtime permission checks."""
    StrategyRuntimePermissionService(
        db_manager=db_manager,
        governance_repository=governance_repository,
    ).assert_strategy_allowed(strategy_id=strategy_id, context=context)
