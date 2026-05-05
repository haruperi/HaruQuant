"""Abstract LLM runtime base class — provider-agnostic AgentRuntime."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from haruquant.utils import logger
from backend.agents.runtime.runner import (
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
    ADKRunRequest,
)


class LLMRuntimeError(Exception):
    """Raised when an LLM provider call fails."""


class LLMRuntime(ABC):
    """Abstract base class for LLM provider runtimes.

    Implements the AgentRuntime protocol. Subclasses for each provider
    (Gemini, OpenAI, Ollama, etc.) call their respective APIs and
    normalize responses to AgentExecutionResult.
    """

    def __init__(
        self,
        *,
        model: str,
        timeout_seconds: float = 60.0,
        max_output_tokens: int = 4096,
        temperature: float = 0.2,
        top_p: float = 0.95,
        top_k: int = 40,
        json_mode: bool = True,
    ) -> None:
        self._model = model
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature
        self._top_p = top_p
        self._top_k = top_k
        self._json_mode = json_mode

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        """Human-readable provider name (e.g., 'gemini', 'openai', 'ollama')."""
        return self.__class__.__name__.replace("Runtime", "").lower()

    @abstractmethod
    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Call the LLM provider and return a normalized response dict.

        Returns:
            {
                "content": str,           # The generated text (JSON string)
                "prompt_tokens": int,     # Input token count
                "completion_tokens": int, # Output token count
                "total_tokens": int,      # Total token count
            }

        Raises:
            LLMRuntimeError: On API failure, timeout, or content safety block.
        """

    def run(
        self,
        *,
        request: ADKRunRequest,
        context: AgentExecutionContext,
    ) -> AgentExecutionResult:
        """Execute one agent run through the LLM provider.

        Builds system prompt from the agent's instruction + context,
        sends the request payload as user message, and returns
        AgentExecutionResult with parsed output.
        """
        system_prompt = request.input_payload.get(
            "_system_prompt",
            "You are a helpful AI assistant. Respond with valid JSON only.",
        )
        user_message = json.dumps(request.input_payload, ensure_ascii=False)

        try:
            response = self._call_llm(system_prompt, user_message)
        except LLMRuntimeError:
            return AgentExecutionResult(
                output_payload={
                    "error": "LLM provider call failed",
                    "contract_type": request.input_payload.get("contract_type", "unknown"),
                    "schema_version": "1.0.0",
                },
                final_state="ERROR",
                tool_calls=(),
                token_usage=None,
            )

        # Parse JSON output
        content = response.get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # If the model didn't return valid JSON, wrap it
            parsed = {
                "_raw_text": content,
                "contract_type": request.input_payload.get("contract_type", "unknown"),
                "schema_version": "1.0.0",
                "_parse_error": "Model output was not valid JSON",
            }

        token_usage = {
            "prompt_tokens": response.get("prompt_tokens", 0),
            "completion_tokens": response.get("completion_tokens", 0),
            "total_tokens": response.get("total_tokens", 0),
        }

        return AgentExecutionResult(
            output_payload=parsed,
            final_state="COMPLETED",
            tool_calls=(),
            token_usage=token_usage,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"model={self._model!r}, "
            f"timeout={self._timeout}s, "
            f"json_mode={self._json_mode})"
        )
