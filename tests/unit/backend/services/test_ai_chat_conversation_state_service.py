from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    ConversationThreadRecord,
    ConversationService,
    ConversationStateService,
    PageContextAssembler,
)
from backend.contracts.page_context_packet.model import EntityRef


def test_conversation_state_service_builds_resolved_references_from_thread_and_page(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_state.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1)
    service.add_message(
        user_id=1,
        thread_id=thread.thread_id,
        role="user",
        content="Please review backtest 41 before we inspect backtest 42 on EURUSD 1H.",
    )
    refreshed = service.get_thread(user_id=1, thread_id=thread.thread_id)
    page_context = PageContextAssembler(db_manager=db).assemble_generic_context(
        route="/backtests/42",
        workflow_id="wf_1",
        correlation_id="corr_1",
        causation_id="cause_1",
        entity_refs=[EntityRef(type="backtest", id="42", label="Backtest 42")],
    )

    state = ConversationStateService().build_state(
        thread=refreshed,
        page_context=page_context,
        latest_prompt="Compare this run to the previous one",
    )

    assert state.resolved_references["backtest_id"] == "42"
    assert state.resolved_references["previous_backtest_id"] == "41"
    assert state.resolved_references["symbol"] == "EURUSD"
    assert state.resolved_references["timeframe"] == "1H"
    assert state.active_topic == "comparison"


def test_conversation_state_service_enriches_tool_context_for_previous_run_reference() -> None:
    state_service = ConversationStateService()
    state = state_service.build_state(
        thread=ConversationThreadRecord(
            thread_id="thread_1",
            user_id="1",
            title="Compare runs",
        ),
        page_context=PageContextAssembler().assemble_generic_context(
            route="/unknown",
            workflow_id="wf_1",
            correlation_id="corr_1",
            causation_id="cause_1",
        ),
        latest_prompt="",
    )
    state = state.model_copy(
        update={
            "resolved_references": {
                "backtest_id": "42",
                "previous_backtest_id": "41",
                "strategy_id": "9",
            }
        }
    )

    enriched = state_service.enrich_tool_context(
        context={"route": "/unknown", "page_type": "generic", "query": "Compare this run to the previous one"},
        prompt="Compare this run to the previous one",
        state=state,
    )

    assert enriched["backtest_id"] == "42"
    assert enriched["comparison_backtest_id"] == "41"
    assert enriched["strategy_id"] == "9"
