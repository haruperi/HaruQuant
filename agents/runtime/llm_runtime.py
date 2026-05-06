"""Base LLM runtime abstraction for HaruQuant."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMRuntimeError(Exception):
    """Raised when an LLM call fails."""
    pass


class LLMRuntime(ABC):
    """Base class for all LLM providers."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.config = kwargs

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__.replace("Runtime", "").lower()

    @abstractmethod
    def call(self, system_prompt: str, user_message: str, **kwargs: Any) -> Dict[str, Any]:
        """Call the LLM with the given prompt."""
        pass
