from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.agents.runtime import LLMRuntimeError
from backend.agents.chat.ai_chat import (
    AIGatewayService,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)


def test_ai_chat_answer_quality_corpus(tmp_path) -> None:
    database_path = tmp_path / "agentic_answer_quality.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="corpus@example.com", username="corpus_user", password="password")

    fixture_path = Path("tests/fixtures/ai_chat_answer_quality_corpus.json")
    corpus = json.loads(fixture_path.read_text(encoding="utf-8"))

    conversation_service = ConversationService(AiChatRepository(database_path))
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    for case in corpus:
        thread = conversation_service.create_thread(
            user_id=1,
            current_route=case["route"],
            current_page_type=case["page_type"],
        )
        with patch("backend.agents.chat.ai_chat.ai_gateway.create_llm_runtime", side_effect=LLMRuntimeError("disabled for deterministic corpus")):
            metadata, chunks, _message_id = gateway.stream_response(
                ChatStreamRequest(
                    user_id=1,
                    thread_id=thread.thread_id,
                    prompt=case["prompt"],
                )
            )
        content = "".join(chunks)

        assert metadata["task_class"] == case["expected_task_class"], case["name"]
        assert metadata["response_style"] == case["expected_response_style"], case["name"]
        assert content.strip(), f"{case['name']} returned empty content"
        for phrase in case.get("expected_phrases", []):
            assert phrase in content, f"{case['name']} missing phrase {phrase}"
