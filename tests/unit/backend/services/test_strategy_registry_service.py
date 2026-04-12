from __future__ import annotations

from pathlib import Path

import pytest

from backend.data.database import GovernanceRepository, apply_pending_migrations
from backend.services import (
    StrategyLifecycleState,
    StrategyRegistrationRequest,
    StrategyRegistryService,
)


def test_strategy_registry_service_persists_strategy_lifecycle_entry(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = StrategyRegistryService(GovernanceRepository(database_path))

    record = service.register(
        StrategyRegistrationRequest(
            strategy_id="strat_001",
            strategy_name="FX Momentum",
            strategy_family="momentum",
            code_hash="code_hash_001",
            parameter_hash="param_hash_001",
            lifecycle_state=StrategyLifecycleState.RESEARCH,
            owner_id="owner_001",
        )
    )

    fetched = service.get("strat_001")

    assert record.strategy_id == "strat_001"
    assert fetched is not None
    assert fetched.current_lifecycle_state == "RESEARCH"


def test_strategy_registry_service_requires_identity_fields(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = StrategyRegistryService(GovernanceRepository(database_path))

    with pytest.raises(Exception):
        service.register(
            StrategyRegistrationRequest(
                strategy_id="",
                strategy_name="FX Momentum",
                strategy_family="momentum",
                code_hash="code_hash_001",
                parameter_hash="param_hash_001",
            )
        )
