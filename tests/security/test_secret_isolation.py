from __future__ import annotations

from pathlib import Path

from backend.common.redaction import REDACTED
from backend.agents.runtime import ContextRedactionMiddleware


_FORBIDDEN_UI_MARKERS = (
    "approval_token",
    '"token":',
    '"api_key":',
    "Bearer ",
    "password=",
    "secret=",
)


def test_secrets_never_enter_model_context() -> None:
    middleware = ContextRedactionMiddleware()
    redacted = middleware.redact(
        {
            "market_context": "EURUSD breakout setup",
            "approval_token": "approval-secret-001",
            "connection": {
                "api_key": "super-secret-key",
                "note": "Bearer top-secret-jwt",
            },
        }
    )

    assert redacted.payload["approval_token"] == REDACTED
    assert redacted.payload["connection"]["api_key"] == REDACTED
    assert redacted.payload["connection"]["note"] == f"Bearer {REDACTED}"
    assert "approval_token" in redacted.redacted_paths


def test_operator_ui_payload_sources_do_not_expose_secret_markers() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    operator_ui_dir = repo_root / "ui" / "src" / "components" / "operator"

    scanned_files = tuple(sorted(operator_ui_dir.rglob("*.ts*")))
    assert scanned_files

    for file_path in scanned_files:
        contents = file_path.read_text(encoding="utf-8")
        for marker in _FORBIDDEN_UI_MARKERS:
            assert marker not in contents, f"forbidden secret marker {marker!r} found in {file_path.name}"

