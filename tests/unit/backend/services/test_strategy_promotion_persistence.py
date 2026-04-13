from __future__ import annotations

from pathlib import Path

from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.services import (
    PromotionPersistenceRequest,
    StrategyLifecycleState,
    StrategyPromotionPersistenceService,
    StrategyRegistrationRequest,
    StrategyRegistryService,
)


def test_strategy_promotion_persistence_records_history_and_updates_state(tmp_path) -> None:
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
            lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
        )
    )

    result = StrategyPromotionPersistenceService(repository).persist(
        PromotionPersistenceRequest(
            strategy_id="strat_001",
            from_state=StrategyLifecycleState.PAPER_APPROVED,
            to_state=StrategyLifecycleState.LIVE_LIMITED,
            evidence_bundle_id="evidence_001",
            approver_1_id="risk_manager_001",
            approver_2_id="compliance_001",
            effective_at="2026-04-09T12:00:00Z",
            rationale="Promotion approved after paper validation.",
        )
    )

    assert result.promotion.strategy_id == "strat_001"
    assert result.promotion.to_state == "LIVE_LIMITED"
    assert result.strategy.current_lifecycle_state == "LIVE_LIMITED"
