from __future__ import annotations

from pathlib import Path

from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from services.strategy.governance import StrategyLifecycleState, StrategyRegistrationRequest, StrategyRegistryService, StrategyRetirementService


def test_strategy_retirement_service_updates_state_and_preserves_record(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = GovernanceRepository(database_path)
    StrategyRegistryService(repository).register(
        StrategyRegistrationRequest(
            strategy_id="strat_001",
            strategy_name="FX Momentum",
            strategy_family="momentum",
            code_hash="code_hash_001",
            parameter_hash="param_hash_001",
            lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
        )
    )

    result = StrategyRetirementService(repository).retire(strategy_id="strat_001")

    assert result.strategy.current_lifecycle_state == "RETIRED"
    assert result.preserved is True
