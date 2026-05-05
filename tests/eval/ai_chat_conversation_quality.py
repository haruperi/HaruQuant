from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

from backend_retiring.agents.runtime import LLMRuntimeError
from data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from backend_retiring.agents.chat.ai_chat import (
    AIGatewayService,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)
from backend_retiring.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class CorpusKnowledgeToolExecutor:
    def execute(self, *, user_id, requested_tools, context, authority_band="read_only", permission_tier="T1_READ_ONLY"):
        if "internal_knowledge" not in requested_tools:
            return ([], tuple())
        return (
            [
                ToolExecutionResult(
                    tool_name="internal_knowledge",
                    payload={
                        "query": context.get("query"),
                        "matches": [
                            {
                                "content": "The rollout plan defines phased release rings, rollback checks, and operator sign-off before promotion.",
                                "relevance_score": 0.94,
                                "citation": "AI_Chatbot_Implementation_Plan.md",
                                "chunk": "chunk_01",
                                "filename": "AI_Chatbot_Implementation_Plan.md",
                            },
                            {
                                "content": "The support SOP requires incident triage, escalation, and verification of grounded tool behavior before closing the case.",
                                "relevance_score": 0.88,
                                "citation": "AI_Chatbot_Support_SOP.md",
                                "chunk": "chunk_02",
                                "filename": "AI_Chatbot_Support_SOP.md",
                            },
                        ],
                        "message": "Found 2 relevant excerpts from internal knowledge.",
                    },
                    latency_ms=10,
                    success=True,
                )
            ],
            tuple(),
        )


@dataclass(frozen=True)
class ConversationCaseResult:
    name: str
    passed: bool
    failures: list[str]
    metadata: dict[str, Any]
    content: str


@dataclass(frozen=True)
class ConversationQualityReport:
    total_cases: int
    passed_cases: int
    failed_cases: list[ConversationCaseResult]

    @property
    def overall_pass(self) -> bool:
        return not self.failed_cases


class ConversationQualityEvaluator:
    def __init__(self, fixture_path: str | Path = "tests/fixtures/ai_chat_conversational_corpus.json") -> None:
        self.fixture_path = Path(fixture_path)

    def evaluate(self, tmp_path: Path) -> ConversationQualityReport:
        database_path = tmp_path / "ai_chat_conversation_quality.db"
        db = DatabaseManager(db_path=str(database_path))
        db.initialize_database()
        apply_pending_migrations(database_path, default_migrations_dir())
        db.create_user(email="conversation-quality@example.com", username="conversation_quality", password="password")

        corpus = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        conversation_service = ConversationService(AiChatRepository(database_path))
        gateway = AIGatewayService(
            conversation_service=conversation_service,
            context_assembler=PageContextAssembler(db_manager=db),
            tool_executor=CorpusKnowledgeToolExecutor(),
        )

        results: list[ConversationCaseResult] = []
        for case in corpus:
            thread = conversation_service.create_thread(
                user_id=1,
                current_route=case["route"],
                current_page_type=case["page_type"],
            )
            for message in case.get("history", []):
                conversation_service.add_message(
                    user_id=1,
                    thread_id=thread.thread_id,
                    role="user",
                    content=message,
                )
            with patch("backend_retiring.agents.chat.ai_chat.ai_gateway.create_llm_runtime", side_effect=LLMRuntimeError("disabled for deterministic eval")):
                metadata, chunks, _message_id = gateway.stream_response(
                    ChatStreamRequest(
                        user_id=1,
                        thread_id=thread.thread_id,
                        prompt=case["prompt"],
                    )
                )
            content = "".join(chunks)
            failures = self._validate_case(case=case, metadata=metadata, content=content)
            results.append(
                ConversationCaseResult(
                    name=case["name"],
                    passed=not failures,
                    failures=failures,
                    metadata=metadata,
                    content=content,
                )
            )

        failed_cases = [result for result in results if not result.passed]
        return ConversationQualityReport(
            total_cases=len(results),
            passed_cases=len(results) - len(failed_cases),
            failed_cases=failed_cases,
        )

    @staticmethod
    def _validate_case(*, case: dict[str, Any], metadata: dict[str, Any], content: str) -> list[str]:
        failures: list[str] = []
        if metadata.get("task_class") != case["expected_task_class"]:
            failures.append(f"task_class={metadata.get('task_class')} expected={case['expected_task_class']}")
        if metadata.get("response_style") != case["expected_response_style"]:
            failures.append(f"response_style={metadata.get('response_style')} expected={case['expected_response_style']}")
        if metadata.get("answer_mode") != case["expected_answer_mode"]:
            failures.append(f"answer_mode={metadata.get('answer_mode')} expected={case['expected_answer_mode']}")
        expected_generation_source = case.get("expected_generation_source")
        if expected_generation_source and metadata.get("generation_source") != expected_generation_source:
            failures.append(
                f"generation_source={metadata.get('generation_source')} expected={expected_generation_source}"
            )

        tools_used = metadata.get("tools_used") or []
        for tool_name in case.get("expected_tools_used", []):
            if tool_name not in tools_used:
                failures.append(f"missing_tool={tool_name}")

        specialists_used = metadata.get("specialist_agents_used") or []
        for agent_name in case.get("expected_specialists_used", []):
            if agent_name not in specialists_used:
                failures.append(f"missing_specialist={agent_name}")

        for phrase in case.get("expected_phrases", []):
            if phrase not in content:
                failures.append(f"missing_phrase={phrase}")
        for phrase in case.get("forbidden_phrases", []):
            if phrase in content:
                failures.append(f"forbidden_phrase_present={phrase}")

        if not content.strip():
            failures.append("empty_content")
        return failures


def test_ai_chat_conversation_quality(tmp_path) -> None:
    report = ConversationQualityEvaluator().evaluate(tmp_path)

    assert report.total_cases > 0
    assert report.overall_pass, [f"{case.name}: {case.failures}" for case in report.failed_cases]
