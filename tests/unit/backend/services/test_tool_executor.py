from __future__ import annotations

from data.database import apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import StrategyCatalogCreateRequest, StrategyCatalogService
from backend_retiring.agents.chat.ai_chat.tool_executor import ToolExecutor


def test_tool_executor_runs_allowlisted_strategy_tool(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(str(database_path), default_migrations_dir())
    db.create_user(email="tools@example.com", username="tools_user", password="password")
    catalog = StrategyCatalogService(db_manager=db)
    strategy = catalog.create_strategy(
        StrategyCatalogCreateRequest(
            name="Tool Alpha",
            code="class ToolAlpha: pass\n",
            category="momentum",
            parameters={"fast": 20, "slow": 50},
        ),
        user_id=1,
    )

    executor = ToolExecutor(db_manager=db)
    results, denied = executor.execute(
        user_id=1,
        requested_tools=("strategy_parameters", "not_allowed"),
        context={"strategy_id": strategy["id"]},
    )

    assert denied == ("not_allowed",)
    assert results[0].tool_name == "strategy_parameters"
    assert results[0].success is True
    assert results[0].payload["strategy_found"] is True
    assert results[0].payload["parameters"] == {"fast": 20, "slow": 50}
