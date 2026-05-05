"""LiteLLM runtime — universal proxy for ALL LLM providers.

Supports via litellm.completion():
  - Gemini: gemini-3.1-pro-preview, gemini-3.1-flash-lite-preview
  - OpenAI: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano
  - Ollama (local): llama3.2, qwen2.5-coder, gemma4, qwen3.5, phi4-mini-reasoning

Uses API keys from env vars or backend/config/environments/.env:
  - GOOGLE_API_KEY for Gemini models
  - OPENAI_API_KEY for OpenAI models
  - OLLAMA_BASE_URL for local Ollama (default: http://localhost:11434/v1)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from backend.agents.runtime.llm_runtime import LLMRuntime, LLMRuntimeError
from services.utils.logger import logger

try:
    import litellm
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False


class LiteLLMRuntime(LLMRuntime):
    """Universal LLM runtime via LiteLLM proxy.

    Automatically routes to the correct provider based on model name.
    All credentials loaded from env vars or .env file.
    """

    def __init__(
        self,
        *,
        model: str = "gemini-3.1-flash-lite-preview",
        api_key: str | None = None,
        api_base: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self._api_key = api_key
        self._api_base = api_base

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Call LLM via LiteLLM and return normalized response."""
        if not HAS_LITELLM:
            raise LLMRuntimeError("litellm package not installed. pip install litellm")

        try:
            # Build model string for litellm routing
            model_name = self._resolve_model_name(self._model)

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            # Configure generation
            call_kwargs: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": self._temperature,
                "top_p": self._top_p,
                "max_tokens": self._max_output_tokens,
            }

            # Set API key if provided
            if self._api_key:
                call_kwargs["api_key"] = self._api_key

            # Set API base URL (for Ollama/local models)
            if self._api_base:
                call_kwargs["api_base"] = self._api_base

            # JSON mode for structured output
            if self._json_mode:
                call_kwargs["response_format"] = {"type": "json_object"}

            # Call LiteLLM
            response = litellm.completion(**call_kwargs)

            # Extract content
            choice = response.choices[0] if response.choices else None
            if choice is None or choice.message is None:
                raise LLMRuntimeError("LiteLLM returned empty response")

            content = choice.message.content or ""

            # Extract token usage
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else 0

            logger.info(
                f"LiteLLMRuntime: model={model_name}, "
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
            logger.error(f"LiteLLMRuntime: API call failed: {exc}")
            raise LLMRuntimeError(f"LiteLLM call failed: {exc}") from exc

    @staticmethod
    def _resolve_model_name(model: str) -> str:
        """Convert model name to litellm format.

        litellm uses specific prefixes for routing:
          - Gemini: "gemini/..." or "vertex_ai/..."
          - OpenAI: "gpt-..." or "openai/..."
          - Ollama: "ollama/..." or just the model name
        """
        model_lower = model.lower()

        # Gemini models
        if "gemini" in model_lower:
            if "/" not in model:
                return f"gemini/{model}"
            return model

        # OpenAI models
        if any(x in model_lower for x in ("gpt-", "o1", "o3", "claude")):
            if "/" not in model:
                return f"openai/{model}"
            return model

        # Ollama models (llama3.2, qwen2.5-coder:7b, gemma4, etc.)
        if any(x in model_lower for x in ("llama", "qwen", "gemma", "phi", "mistral", "deepseek")):
            # Check if Ollama is running locally
            ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            if not model.startswith("ollama/"):
                return f"ollama/{model}"
            return model

        # Default: return as-is (litellm will try to figure it out)
        return model
