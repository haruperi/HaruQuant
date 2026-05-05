"""OpenAI-compatible LLM runtime — works with OpenAI, Ollama, vLLM, and any compatible API."""

from __future__ import annotations

import os
from typing import Any, Dict

from backend_retiring.agents.runtime.llm_runtime import LLMRuntime, LLMRuntimeError
from haruquant.utils import logger

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIRuntime(LLMRuntime):
    """LLM runtime for OpenAI and any OpenAI-compatible API.

    Supports:
    - OpenAI: gpt-4o, gpt-4o-mini, o1, o3-mini, etc.
    - Ollama: llama3.1:70b, qwen2.5-coder:32b, etc.
    - vLLM: Any model served via OpenAI-compatible endpoint
    - LM Studio, LocalAI, Together, Groq, etc.

    Configuration:
    - OPENAI_API_KEY: API key (required for OpenAI, optional for local)
    - OPENAI_BASE_URL: API endpoint (default: OpenAI's, set to Ollama's http://localhost:11434/v1 etc.)
    - AGENT_MODEL or OPENAI_MODEL: Model name
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "ollama")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Call OpenAI-compatible API and return normalized response."""
        if not HAS_OPENAI:
            raise LLMRuntimeError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        try:
            client_kwargs: Dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                client_kwargs["base_url"] = self._base_url

            client = OpenAI(**client_kwargs)

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            # Configure generation
            chat_kwargs: Dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
                "top_p": self._top_p,
                "max_tokens": self._max_output_tokens,
            }
            if self._json_mode:
                chat_kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**chat_kwargs)

            # Extract content
            choice = response.choices[0] if response.choices else None
            if choice is None or choice.message is None:
                raise LLMRuntimeError("OpenAI-compatible API returned empty response")

            content = choice.message.content or ""

            # Extract token usage
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else 0

            logger.info(
                f"OpenAIRuntime: model={self._model}, "
                f"prompt_tokens={prompt_tokens}, "
                f"completion_tokens={completion_tokens}, "
                f"total_tokens={total_tokens}"
            )

            return {
                "content": content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        except LLMRuntimeError:
            raise
        except Exception as exc:
            logger.error(f"OpenAIRuntime: API call failed: {exc}")
            raise LLMRuntimeError(f"OpenAI-compatible API call failed: {exc}") from exc
