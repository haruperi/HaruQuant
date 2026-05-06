"""LiteLLM-based universal runtime for HaruQuant."""
from __future__ import annotations

import os
from typing import Any, Dict

from haruquant.utils import logger
from .llm_runtime import LLMRuntime, LLMRuntimeError


class LiteLLMRuntime(LLMRuntime):
    """Universal runtime using LiteLLM to support 100+ providers."""

    def call(self, system_prompt: str, user_message: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            import litellm
            
            # Use LiteLLM completion
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            # Combine config with call-time kwargs
            call_kwargs = {**self.config, **kwargs}
            
            # Ensure provider prefix for LiteLLM
            model_name = self.model
            if "gemini" in model_name.lower() and "/" not in model_name:
                model_name = f"gemini/{model_name}"
            elif "gpt" in model_name.lower() and "/" not in model_name:
                model_name = f"openai/{model_name}"
            
            response = litellm.completion(
                model=model_name,
                messages=messages,
                **call_kwargs
            )
            
            # Standardize output
            content = response.choices[0].message.content
            usage = response.get("usage", {})
            
            return {
                "content": content,
                "model": self.model,
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        except ImportError:
            raise LLMRuntimeError("litellm is not installed.")
        except Exception as exc:
            logger.error(f"LiteLLM call failed: {exc}")
            raise LLMRuntimeError(str(exc)) from exc
