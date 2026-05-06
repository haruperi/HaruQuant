"""Middleware for HaruQuant agent runtime."""
from __future__ import annotations

from typing import Any, Dict


class PromptComposingMiddleware:
    """Middleware to compose and refine prompts before sending to LLM."""
    
    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    def process_request(self, request: Any, context: Any) -> Any:
        # Minimal implementation for example compatibility
        return request
