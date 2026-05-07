"""Real agentic firm example: chatbot routed through the CEO.

Usage:
    python scripts/examples/agentic_ai/09_ceo_chat_bridge.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from services.ceo_gateway import CEOChatGateway
from services.context.service import ContextAssembler
from services.conversation.service import ConversationService
from services.schemas.chat import ChatTurnRequest


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<30s} {value}")


def example_database_path() -> Path:
    root = Path(PROJECT_ROOT) / ".tmp_agentic_examples" / "ceo_chat_bridge"
    root.mkdir(parents=True, exist_ok=True)
    return root / "ceo_chat_bridge.db"


def main() -> None:
    print()
    print("#" * 78)
    print("#  Chatbot -> CEO Agent Bridge")
    print("#" * 78)

    database_path = example_database_path()
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    if not db.get_user(user_id=1):
        db.create_user(
            email="ceo-chat-bridge@example.com",
            username="ceo_chat_bridge",
            password="password",
        )

    user_id = "1"
    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=user_id,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    gateway = CEOChatGateway(
        conversation_service=conversation_service,
        context_assembler=ContextAssembler(),
    )

    print_header("01: Chat Request")
    request = ChatTurnRequest(
        prompt="Create and backtest a EURUSD H1 mean reversion strategy.",
        attached_tools=["strategy_parameters", "backtest_summary"],
        context_route="/dashboard",
        context_page_title="Dashboard",
        context_symbol="EURUSD",
        context_timeframe="H1",
    )
    print_kv("Prompt", request.prompt)
    print_kv("Attached tools", request.attached_tools)

    events = list(gateway.stream_turn(thread_id=thread.thread_id, user_id=user_id, request=request))
    content = "".join(str(data.get("delta", "")) for event, data in events if event == "token")
    done_payload = next(data for event, data in reversed(events) if event == "done")
    metadata = done_payload["metadata"]
    message_id = done_payload["message_id"]

    print_header("02: CEO Response")
    print(content)

    print_header("03: Firm Metadata Stored on Chat Message")
    print_kv("Message ID", message_id)
    print_kv("Answer mode", metadata["answer_mode"])
    print_kv("Planner source", metadata["planner"]["planner_source"])
    print_kv("Planner intent", metadata["planner"]["intent"])
    print_kv("Tools used", metadata["tools_used"])
    print_kv("Specialists used", metadata["specialist_agents_used"])
    print_kv("CEO memo", metadata["ceo_memo"])

    refreshed = conversation_service.get_thread(user_id=user_id, thread_id=thread.thread_id)
    print_header("04: Chat Thread")
    print_kv("Messages", [{"role": msg.role, "id": msg.message_id} for msg in refreshed.messages])
    print_kv("Assistant metadata answer mode", refreshed.messages[-1].metadata["answer_mode"])

    print()
    print("#" * 78)
    print("#  CEO chat bridge example complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

