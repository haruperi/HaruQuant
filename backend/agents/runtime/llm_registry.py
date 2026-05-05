"""LLM provider registry — auto-selects provider from model name or env var.

Supports:
  - litellm: Universal proxy for ALL providers (Gemini, OpenAI, Ollama, etc.)
  - openai: Direct OpenAI SDK or any OpenAI-compatible endpoint (Ollama, vLLM)
  - google-adk: Google Gemini via ADK SDK
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Type

from backend.agents.runtime.llm_runtime import LLMRuntime
from services.utils.logger import logger

# Provider registry — populated at import time
_PROVIDERS: Dict[str, Type[LLMRuntime]] = {}


def register_provider(name: str, runtime_class: Type[LLMRuntime]) -> None:
    """Register an LLM provider by name."""
    _PROVIDERS[name.lower()] = runtime_class
    logger.info(f"LLMRegistry: registered provider '{name}' -> {runtime_class.__name__}")


def get_provider(model: Optional[str] = None, provider: Optional[str] = None) -> Type[LLMRuntime]:
    """Get the LLM provider class for the given model or explicit provider.

    Selection priority:
    1. Explicit `provider` argument
    2. LLM_PROVIDER env var
    3. Auto-detect from model name pattern
    4. Fallback to first registered provider
    """
    # 1. Explicit provider
    if provider:
        cls = _PROVIDERS.get(provider.lower())
        if cls:
            return cls
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Available: {list(_PROVIDERS.keys())}"
        )

    # 2. Environment variable
    env_provider = os.environ.get("LLM_PROVIDER", "").lower()
    if env_provider:
        cls = _PROVIDERS.get(env_provider)
        if cls:
            return cls
        logger.warning(
            f"LLMRegistry: unknown LLM_PROVIDER='{env_provider}', "
            f"falling back to auto-detect"
        )

    # 3. Auto-detect from model name
    # litellm is the universal proxy — prefer it for ALL models when registered
    if model:
        model_lower = model.lower()
        # If litellm is registered, use it for everything (it handles routing internally)
        litellm_cls = _PROVIDERS.get("litellm")
        if litellm_cls:
            return litellm_cls
        # Fallback: try openai for gpt/claude models
        if any(x in model_lower for x in ("gpt-", "o1", "o3", "claude", "gpt-5")):
            cls = _PROVIDERS.get("openai")
            if cls:
                return cls
        # Ollama models via openai-compatible API
        if any(x in model_lower for x in ("llama", "qwen", "mistral", "phi", "deepseek", "gemma", ":")):
            cls = _PROVIDERS.get("openai")
            if cls:
                return cls

    # 4. Fallback to first registered provider
    if _PROVIDERS:
        first_name = next(iter(_PROVIDERS))
        return _PROVIDERS[first_name]

    raise RuntimeError(
        "No LLM providers registered. Install at least one of: "
        "litellm, openai, google-adk"
    )


def create_llm_runtime(
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> LLMRuntime:
    """Create an LLM runtime instance with auto-detected provider.

    Args:
        model: Model name (e.g., gemini-3.1-flash-lite-preview, gpt-5.4, llama3.2)
        provider: Explicit provider name (litellm, openai, google-adk)
        **kwargs: Additional runtime config (timeout, temperature, etc.)

    Returns:
        Configured LLMRuntime instance
    """
    from backend.config.agent_model import AGENT_MODEL

    resolved_model = model or AGENT_MODEL
    provider_class = get_provider(model=resolved_model, provider=provider)
    return provider_class(model=resolved_model, **kwargs)


def _register_builtin_providers() -> None:
    """Register built-in LLM providers based on installed packages."""
    # Priority 1: litellm (universal proxy for ALL providers)
    try:
        import litellm  # noqa: F401
        from backend.agents.runtime.litellm_runtime import LiteLLMRuntime
        register_provider("litellm", LiteLLMRuntime)
    except ImportError:
        pass

    # Priority 2: openai (direct or Ollama-compatible)
    try:
        import openai  # noqa: F401
        from backend.agents.runtime.openai_runtime import OpenAIRuntime
        register_provider("openai", OpenAIRuntime)
    except ImportError:
        pass

    # Priority 3: google-adk (Gemini via ADK SDK)
    try:
        import google_adk  # noqa: F401
        from backend.agents.runtime.google_adk_runtime import GoogleADKRuntime
        register_provider("google-adk", GoogleADKRuntime)
    except ImportError:
        pass


_register_builtin_providers()
