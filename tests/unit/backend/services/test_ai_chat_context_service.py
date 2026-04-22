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


def test_page_context_assembler_treats_root_route_as_dashboard(tmp_path) -> None:
    database_path = tmp_path / "agentic_root.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="root@example.com", username="root_user", password="password")

    assembler = PageContextAssembler(db_manager=db)
    packet = assembler.assemble_context(route="/", user_id=1)

    assert packet.payload.page_type == "dashboard"
    assert packet.payload.authority.trust_level == "system_state"


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


def test_page_context_assembler_builds_live_context_with_chart_focus(tmp_path) -> None:
    database_path = tmp_path / "agentic_live_ctx.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="livectx@example.com", username="live_ctx_user", password="password")
    session_id = db.create_live_session(
        user_id=1,
        session_name="London Open",
        mode="paper",
    )

    assembler = PageContextAssembler(db_manager=db)
    packet = assembler.assemble_context(
        route="/live",
        user_id=1,
        page_title="Live Command Center",
        page_state={"session_id": session_id, "symbol": "XAUUSD", "timeframe": "M15"},
    )

    assert packet.payload.page_type == "live_trading"
    assert packet.payload.authority.trust_level == "system_state"
    assert packet.payload.payload["session_id"] == session_id
    assert packet.payload.payload["symbol"] == "XAUUSD"
    assert packet.payload.payload["timeframe"] == "M15"
    assert "chart focus" in packet.payload.summary.headline.lower()


def test_page_context_assembler_uses_dom_fallback_for_generic_pages(tmp_path) -> None:
    database_path = tmp_path / "agentic_dom_ctx.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="domctx@example.com", username="dom_ctx_user", password="password")

    assembler = PageContextAssembler(db_manager=db)
    packet = assembler.assemble_context(
        route="/documentation/order-types",
        user_id=1,
        page_title="Documentation",
        page_state={
            "dom": {
                "title": "Documentation",
                "headings": ["Documentation", "Order Types"],
                "text_excerpt": "This page explains order types and execution constraints.",
                "semantic_blocks": [
                    {
                        "id": "doc:order-types",
                        "blockType": "text",
                        "title": "Order Types",
                        "summary": "Order types and execution constraints.",
                    }
                ],
            }
        },
    )

    assert packet.payload.page_type == "generic"
    assert packet.payload.page_title == "Documentation"
    assert "captured current ui context" in packet.payload.summary.headline.lower()
    assert packet.payload.payload["dom"]["headings"][1] == "Order Types"
    assert packet.payload.payload["dom"]["semantic_blocks"][0]["title"] == "Order Types"
