from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.auth_utils import get_user_id_from_token
from backend.api.main import app
from backend.api.routes.ai_chat import get_page_context_assembler
from backend.data.database import apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import PageContextAssembler


def test_ai_chat_context_endpoint_returns_route_aware_packet(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="api-ctx@example.com", username="api_ctx_user", password="password")

    app.dependency_overrides[get_page_context_assembler] = lambda: PageContextAssembler(db_manager=db)
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    response = client.get("/api/ai-chat/context", params={"route": "/dashboard"})

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["page_type"] == "dashboard"
    assert payload["authority"]["trust_level"] == "system_state"

    app.dependency_overrides.clear()
