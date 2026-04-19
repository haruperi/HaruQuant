"""SSE streaming utilities for the HaruQuant AI chat gateway."""

from __future__ import annotations

import json
from typing import Iterable


class ChatStreamManager:
    """Render gateway events as Server-Sent Events."""

    @staticmethod
    def encode(event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def token_events(self, chunks: Iterable[str]) -> Iterable[str]:
        for chunk in chunks:
            yield self.encode("token", {"delta": chunk})

    def meta_event(self, payload: dict[str, object]) -> str:
        return self.encode("meta", payload)

    def done_event(self, payload: dict[str, object]) -> str:
        return self.encode("done", payload)

    def error_event(self, message: str) -> str:
        return self.encode("error", {"message": message})
