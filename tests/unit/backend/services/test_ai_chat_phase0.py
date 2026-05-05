from __future__ import annotations

from backend.agents.chat.ai_chat import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AuthorityBand,
    ConversationMessageRecord,
    ConversationThreadRecord,
    MemorySummary,
    PageContextAssembler,
    PinnedFact,
)


def test_page_context_assembler_resolves_known_route():
    assembler = PageContextAssembler()

    packet = assembler.assemble_generic_context(
        route="/strategies/alpha",
        workflow_id="chat_request",
        correlation_id="corr_001",
        causation_id="evt_001",
    )

    assert packet.payload.page_type == "strategy_detail"
    assert "Strategy Detail" in packet.payload.summary.headline


def test_page_context_assembler_falls_back_to_generic():
    assembler = PageContextAssembler()

    packet = assembler.assemble_generic_context(
        route="/unmapped/route",
        workflow_id="chat_request",
        correlation_id="corr_002",
        causation_id="evt_002",
    )

    assert packet.payload.page_type == "generic"
    assert packet.payload.authority.trust_level == "fallback"


def test_phase0_policy_bands_do_not_allow_live_execution():
    assert ALLOWED_TIERS_BY_AUTHORITY_BAND[AuthorityBand.LIVE_EXECUTION_PROHIBITED] == ()
    assert all(
        "LIVE_ACTION" not in {tier.value for tier in tiers}
        for band, tiers in ALLOWED_TIERS_BY_AUTHORITY_BAND.items()
        if band is not AuthorityBand.PAPER_AUTOMATION
    )


def test_conversation_thread_record_accepts_memory_and_pinned_facts():
    thread = ConversationThreadRecord(
        thread_id="thread_001",
        user_id="user_001",
        title="Explain strategy drawdown",
        memory_summary=MemorySummary(
            summary_text="User is investigating a persistent drawdown in strategy alpha.",
            source_message_count=6,
        ),
        pinned_facts=[
            PinnedFact(key="preferred_asset", value="EURUSD", source="user_profile"),
        ],
    )

    message = ConversationMessageRecord(
        message_id="msg_001",
        thread_id=thread.thread_id,
        role="user",
        content="Why did this strategy underperform last week?",
        context_revision="ctx_001",
    )

    assert thread.status == "active"
    assert thread.memory_summary is not None
    assert thread.pinned_facts[0].key == "preferred_asset"
    assert message.role == "user"
