from __future__ import annotations

from pathlib import Path

from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.agents.strategy_creator_agent import StrategyCreatorAgent
from backend.services.strategy import StrategyCatalogService, StrategyStorage
from backend.services.strategy.design import StrategyBlueprintMaterializationService


COMPLETE_RSI_IDEA = (
    "Create an RSI mean reversion strategy for EURUSD H1. "
    "Enter long when RSI is below 30, exit when RSI recovers above 50, "
    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
)

COMPLETE_SUPERTREND_IDEA = (
    "Create a SuperTrend strategy for EURUSD H1 and also create the indicator. "
    "Enter long when SuperTrend flips bullish, exit when SuperTrend flips bearish, "
    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
)


def _agent(tmp_path: Path) -> StrategyCreatorAgent:
    db_path = tmp_path / "strategy_creator.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    user_id = db.create_user(
        email="creator@example.com",
        username="creator_user",
        password="password",
        full_name="Creator User",
    )
    assert user_id == 1
    catalog = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=GovernanceRepository(db.db_path),
    )
    return StrategyCreatorAgent(
        db_manager=db,
        materializer=StrategyBlueprintMaterializationService(catalog_service=catalog),
        indicator_base_dir=tmp_path / "indicators",
    )


def test_strategy_creator_generates_artifact_without_persistence(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea=COMPLETE_RSI_IDEA,
        full_permissions=False,
    )

    assert result.needs_confirmation is True
    assert result.rendered_code == ""
    assert result.materialized is False

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_RSI_IDEA}]},
        full_permissions=False,
    )

    assert result.needs_clarification is False
    assert result.needs_confirmation is False
    assert result.blueprint.payload.asset_scope.assets == ["EURUSD"]
    assert result.blueprint.payload.asset_scope.timeframe == "H1"
    assert result.code_valid is True
    assert result.materialized is False
    assert result.artifact is not None
    assert result.artifact["required_data_fields"] == ["open", "high", "low", "close", "volume", "rsi"]
    assert result.artifact["known_failure_modes"]
    assert "Full Permissions" in result.permission_note


def test_strategy_creator_materializes_with_full_permissions(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_RSI_IDEA}]},
        full_permissions=True,
    )

    assert result.materialized is True
    assert result.strategy is not None
    assert result.strategy["id"] == 1
    assert Path(str(result.strategy["active_file_path"])).exists()
    assert result.blueprint_artifact_path is not None
    assert Path(result.blueprint_artifact_path).exists()
    assert result.metadata_artifact_path is not None
    assert Path(result.metadata_artifact_path).exists()


def test_strategy_creator_asks_for_missing_inputs_before_generation(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Create a mean reversion strategy.",
        full_permissions=True,
    )

    assert result.needs_clarification is True
    assert result.blueprint is None
    assert result.rendered_code == ""
    assert result.materialized is False
    assert "instrument_or_market" in result.missing_inputs
    assert "timeframe" in result.missing_inputs
    assert "risk_rule" in result.missing_inputs
    assert result.clarification_question is not None


def test_strategy_creator_asks_permission_for_missing_indicator(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea=(
            "Create a SuperTrend strategy for EURUSD H1. Enter long when SuperTrend flips bullish, "
            "exit when SuperTrend flips bearish, use a 50 pip stop loss and 100 pip take profit, "
            "and risk 1% position size per trade."
        ),
        full_permissions=True,
    )

    assert result.needs_clarification is True
    assert "indicator_creation_permission" in result.missing_inputs
    assert result.materialized is False


def test_strategy_creator_creates_missing_indicator_with_permission(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_SUPERTREND_IDEA}]},
        full_permissions=True,
    )

    indicator_path = tmp_path / "indicators" / "custom" / "supertrend.py"
    init_path = tmp_path / "indicators" / "custom" / "__init__.py"

    assert result.needs_clarification is False
    assert result.materialized is True
    assert result.indicator_artifacts
    assert result.indicator_artifacts[0]["materialized"] is True
    assert indicator_path.exists()
    assert "def supertrend" in indicator_path.read_text(encoding="utf-8")
    assert "from backend.services.indicators.custom.supertrend import supertrend" in init_path.read_text(encoding="utf-8")
    assert result.artifact is not None
    assert result.artifact["indicator_dependencies"][0]["available"] is False
