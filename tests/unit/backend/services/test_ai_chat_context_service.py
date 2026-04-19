from __future__ import annotations

from backend.data.database import apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import PageContextAssembler
from backend.services.strategy.catalog import StrategyCatalogCreateRequest, StrategyCatalogService


def test_page_context_assembler_builds_dashboard_context(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="ctx@example.com", username="ctx_user", password="password")

    assembler = PageContextAssembler(db_manager=db)

    packet = assembler.assemble_context(route="/dashboard", user_id=1)

    assert packet.payload.page_type == "dashboard"
    assert packet.payload.authority.trust_level == "system_state"
    assert "active strategies" in packet.payload.summary.headline.lower()


def test_page_context_assembler_builds_strategy_detail_context(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="ctx2@example.com", username="ctx_user2", password="password")
    catalog = StrategyCatalogService(db_manager=db)
    strategy = catalog.create_strategy(
        StrategyCatalogCreateRequest(
            name="Context Alpha",
            description="route-aware strategy",
            category="mean_reversion",
            code="class ContextAlpha: pass\n",
        ),
        user_id=1,
    )

    assembler = PageContextAssembler(db_manager=db, strategy_catalog=catalog)
    packet = assembler.assemble_context(route=f"/strategies/{strategy['id']}", user_id=1)

    assert packet.payload.page_type == "strategy_detail"
    assert packet.payload.entity_refs[0].id == str(strategy["id"])
    assert packet.payload.payload["name"] == "Context Alpha"
