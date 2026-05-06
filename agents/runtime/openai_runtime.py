"""OpenAI-based runtime for HaruQuant."""
from __future__ import annotations

from typing import Any, Dict
from .llm_runtime import LLMRuntime


class OpenAIRuntime(LLMRuntime):
    """Direct OpenAI SDK runtime."""

    def call(self, system_prompt: str, user_message: str, **kwargs: Any) -> Dict[str, Any]:
        # Minimal wrapper, ideally uses litellm internally or direct openai
        import litellm
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = litellm.completion(
            model=f"openai/{self.model}" if not self.model.startswith("openai/") else self.model,
            messages=messages,
            **{**self.config, **kwargs}
        )
        content = response.choices[0].message.content
        usage = response.get("usage", {})
        return {
            "content": content,
            "model": self.model,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }
