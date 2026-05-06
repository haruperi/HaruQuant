"""Run the AI chat retention lifecycle job."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from data.database.migrations.runner import apply_pending_migrations
from data.database.repositories.ai_chat_repository import AiChatRepository
from services.conversation.retention import ConversationRetentionService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI chat archive/delete/purge lifecycle rules.")
    parser.add_argument(
        "--db",
        default=os.getenv("HARUQUANT_DB_PATH", "data/database/haruquant-dev.db"),
        help="SQLite database path.",
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum threads to process.")
    args = parser.parse_args()

    db_path = Path(args.db)
    apply_pending_migrations(db_path)
    decisions = ConversationRetentionService(AiChatRepository(db_path)).run_lifecycle(limit=args.limit)
    print(json.dumps([decision.__dict__ for decision in decisions], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
