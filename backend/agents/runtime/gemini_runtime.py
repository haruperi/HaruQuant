"""Gemini LLM runtime — calls Google Gemini API."""

from __future__ import annotations

import os
from typing import Any, Dict

from backend.agents.runtime.llm_runtime import LLMRuntime, LLMRuntimeError
from haruquant.utils import logger

try:
    import google.genai as genai
    HAS_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai  # type: ignore[import-not-found]
        HAS_GENAI = True
    except ImportError:
        HAS_GENAI = False


class GeminiRuntime(LLMRuntime):
    """LLM runtime for Google Gemini models.

    Supports:
    - gemini-3.1-flash-lite-preview (default)
    - gemini-3.1-pro
    - gemini-2.5-flash
    - Any Gemini model available via the GenAI SDK

    API key from GOOGLE_API_KEY env var.
    """

    def __init__(
        self,
        *,
        model: str = "gemini-3.1-flash-lite-preview",
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not self._api_key:
            logger.warning(
                "GeminiRuntime: GOOGLE_API_KEY not set. "
                "Calls will fail until a valid API key is provided."
            )

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """Call Gemini API and return normalized response."""
        if not HAS_GENAI:
            raise LLMRuntimeError(
                "google-genai package not installed. "
                "Install with: pip install google-genai"
            )
        if not self._api_key:
            raise LLMRuntimeError(
                "Gemini API key not configured. Set GOOGLE_API_KEY env var."
            )

        try:
            client = genai.Client(api_key=self._api_key)

            # Configure generation
            config_kwargs = {
                "temperature": self._temperature,
                "top_p": self._top_p,
                "max_output_tokens": self._max_output_tokens,
            }
            if self._json_mode:
                config_kwargs["response_mime_type"] = "application/json"

            # Build content — system prompt as system_instruction, user message as content
            response = client.models.generate_content(
                model=self._model,
                contents=user_message,
                config={
                    **config_kwargs,
                    "system_instruction": system_prompt,
                },
            )

            # Extract text content
            content = response.text or ""

            # Extract token usage
            usage_metadata = getattr(response, "usage_metadata", None)
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            if usage_metadata:
                prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
                completion_tokens = getattr(usage_metadata, "candidates_token_count", 0)
                total_tokens = getattr(usage_metadata, "total_token_count", 0)

            logger.info(
                f"GeminiRuntime: model={self._model}, "
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

        except Exception as exc:
            logger.error(f"GeminiRuntime: API call failed: {exc}")
            raise LLMRuntimeError(f"Gemini API call failed: {exc}") from exc
