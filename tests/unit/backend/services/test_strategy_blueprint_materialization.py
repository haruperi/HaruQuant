from __future__ import annotations

import json
from pathlib import Path

from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import StrategyCatalogService, StrategyStorage
from haruquant.strategy import (
    StrategyBlueprintMaterializationRequest,
    StrategyBlueprintMaterializationService,
)
from haruquant.strategy import StrategyBlueprintValidator


def _service(tmp_path: Path) -> StrategyBlueprintMaterializationService:
    db_path = tmp_path / "haruquant.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    user_id = db.create_user(
        email="blueprint@example.com",
        username="blueprint_user",
        password="password",
        full_name="Blueprint User",
    )
    assert user_id == 1

    catalog = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=GovernanceRepository(db.db_path),
    )
    return StrategyBlueprintMaterializationService(catalog_service=catalog)


def test_materialize_blueprint_registers_catalog_and_governance(tmp_path: Path) -> None:
    validator = StrategyBlueprintValidator()
    blueprint = validator.validate(
        {
            "payload": {
                "source_idea": "Build an HRP portfolio over large-cap tech and rebalance weekly.",
                "strategy_name": "Large Cap HRP Allocation",
                "strategy_type": "portfolio",
                "entry_logic": [
                    "Rebalance into the current HRP weight vector at the scheduled rebalance date."
                ],
                "exit_logic": [
                    "Exit and recompute weights on the next rebalance date."
                ],
                "portfolio_construction": {
                    "method": "HRP",
                    "rebalance_frequency": "Weekly",
                    "objective": "Risk-balanced diversified allocation",
                },
            }
        }
    ).blueprint
    service = _service(tmp_path)

    result = service.materialize(
        StrategyBlueprintMaterializationRequest(
            blueprint=blueprint,
            user_id=1,
        )
    )

    strategy = result.strategy
    assert strategy["id"] == 1
    assert strategy["active_version"] == "1.0.0"
    assert strategy["governance_strategy_id"] == "strategy:1:1"
    assert strategy["lifecycle_state"] == "RESEARCH"
    assert strategy["strategy_family"] == "portfolio"
    assert Path(strategy["active_file_path"]).exists()
    assert Path(result.blueprint_artifact_path).exists()
    assert Path(result.metadata_artifact_path).exists()

    blueprint_payload = json.loads(Path(result.blueprint_artifact_path).read_text(encoding="utf-8"))
    assert blueprint_payload["contract_type"] == "StrategyBlueprint"
    assert blueprint_payload["payload"]["portfolio_construction"]["method"] == "HRP"

    metadata = json.loads(Path(result.metadata_artifact_path).read_text(encoding="utf-8"))
    assert metadata["blueprintArtifactPath"] == result.blueprint_artifact_path
    assert metadata["blueprintSummary"]["strategy_type"] == "portfolio"
    assert metadata["backtestReadiness"] == "ready"


def test_materialize_ml_blueprint_persists_model_metadata(tmp_path: Path) -> None:
    validator = StrategyBlueprintValidator()
    blueprint = validator.validate(
        {
            "payload": {
                "source_idea": "Use a decision tree classifier to predict next-day direction.",
                "strategy_name": "Decision Tree Direction Forecast",
                "strategy_type": "ml",
                "entry_logic": [
                    "Enter LONG when the model predicts the next-day return class is positive."
                ],
                "exit_logic": [
                    "Exit LONG when the model prediction flips negative."
                ],
            }
        }
    ).blueprint
    service = _service(tmp_path)

    result = service.materialize(
        StrategyBlueprintMaterializationRequest(
            blueprint=blueprint,
            user_id=1,
        )
    )

    metadata = json.loads(Path(result.metadata_artifact_path).read_text(encoding="utf-8"))
    assert metadata["variables"]["model_type"] == "DecisionTreeClassifier"
    assert metadata["parameterTypes"]["model_spec"] == "dict"
