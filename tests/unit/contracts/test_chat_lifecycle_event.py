from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend_retiring.contracts.chat_lifecycle_event.model import (
    ChatLifecycleEvent,
    ChatLifecycleEventPayload,
)


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "backend_retiring" / "contracts" / "chat_lifecycle_event" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_chat_lifecycle_event_accepts_valid_example():
    contract = ChatLifecycleEvent.model_validate(_load_example("valid", "request_received.json"))

    assert contract.contract_type == "ChatLifecycleEvent"
    assert contract.payload.event_type == "chat.request.received"
    assert contract.payload.page_type == "strategy_detail"


def test_chat_lifecycle_event_rejects_invalid_event_type():
    with pytest.raises(ValidationError):
        ChatLifecycleEvent.model_validate(_load_example("invalid", "bad_event_type.json"))


def test_chat_lifecycle_event_payload_requires_request_id():
    with pytest.raises(ValidationError):
        ChatLifecycleEventPayload(
            event_type="chat.error",
            request_id="",
            thread_id="thread_001",
            details={},
        )
