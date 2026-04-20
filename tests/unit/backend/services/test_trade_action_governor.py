from __future__ import annotations

from backend.data.database import AiChatRepository, GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import ConversationService
from backend.services.approval import ApprovalVoteRequest, ApprovalVoteService
from backend.services.trade_action_governor import TradeActionGovernor


def test_trade_action_governor_executes_approved_order_draft_in_paper_mode(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase10_governor.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="phase10@example.com", username="phase10_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/live", current_page_type="live_trading")
    draft = service.create_action_draft(
        user_id=1,
        thread_id=thread.thread_id,
        request_id="req_order_001",
        draft_type="order_draft",
        title="EURUSD buy order draft",
        description="Prepare a paper EURUSD buy order.",
        payload={
            "symbol": "EURUSD",
            "direction": "buy",
            "size": {"units": 1000},
            "stop_loss_logic": {"type": "fixed_percent", "value": 0.01},
            "take_profit_logic": {"type": "fixed_percent", "value": 0.02},
        },
        risk_precheck_status="passed",
        risk_precheck_notes="Awaiting approval.",
    )
    requested = service.request_action_draft_approval(user_id=1, draft_id=draft.draft_id)
    ApprovalVoteService(GovernanceRepository(database_path)).vote(
        ApprovalVoteRequest(
            approval_id=requested.approval_id or "",
            approver_role="approver",
            approver_id="approver_001",
            decision="APPROVE",
            rationale="Approved for bounded paper execution.",
        )
    )

    result = TradeActionGovernor(str(database_path)).execute_paper_action_draft(
        user_id=1,
        draft_id=draft.draft_id,
    )

    assert result.execution_intent_id.startswith("exec_")
    assert result.receipt_id.startswith("rcpt_")
    assert result.approval_state.eligible is True
    assert result.action_draft.side_effect_status == "paper_execution_acknowledged"
    assert result.action_draft.execution_receipt_id == result.receipt_id
