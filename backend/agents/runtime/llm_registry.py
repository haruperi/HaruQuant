"""LLM provider registry — auto-selects provider from model name or env var."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Type

from backend.agents.runtime.llm_runtime import LLMRuntime
from backend.common.logger import logger

# Provider registry — populated at import time
_PROVIDERS: Dict[str, Type[LLMRuntime]] = {}


def register_provider(name: str, runtime_class: Type[LLMRuntime]) -> None:
    """Register an LLM provider by name."""
    _PROVIDERS[name.lower()] = runtime_class
    logger.info(f"LLMRegistry: registered provider '{name}' → {runtime_class.__name__}")


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
    if model:
        model_lower = model.lower()
        if "gemini" in model_lower:
            cls = _PROVIDERS.get("gemini")
            if cls:
                return cls
        if any(x in model_lower for x in ("gpt-", "o1", "o3", "claude")):
            cls = _PROVIDERS.get("openai")
            if cls:
                return cls
        # Ollama models: llama3, qwen, mistral, etc.
        if any(x in model_lower for x in ("llama", "qwen", "mistral", "phi", "deepseek")):
            cls = _PROVIDERS.get("openai")  # Ollama uses OpenAI-compatible API
            if cls:
                return cls

    # 4. Fallback to first registered provider
    if _PROVIDERS:
        first_name = next(iter(_PROVIDERS))
        logger.warning(
            f"LLMRegistry: no provider matched for model='{model}', "
            f"falling back to '{first_name}'"
        )
        return _PROVIDERS[first_name]

    raise RuntimeError(
        "No LLM providers registered. Install and import a provider: "
        "pip install google-genai openai"
    )


def create_llm_runtime(
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> LLMRuntime:
    """Create an LLM runtime instance with auto-detected provider.

    Args:
        model: Model name (e.g., 'gemini-3.1-flash-lite-preview', 'gpt-4o-mini', 'llama3.1:70b')
        provider: Explicit provider name ('gemini', 'openai')
        **kwargs: Additional runtime config (timeout, temperature, etc.)

    Returns:
        Configured LLMRuntime instance
    """
    from backend.config.agent_model import AGENT_MODEL

    resolved_model = model or AGENT_MODEL
    provider_class = get_provider(model=resolved_model, provider=provider)
    return provider_class(model=resolved_model, **kwargs)


# Register providers at module import time
def _register_builtin_providers() -> None:
    """Register built-in LLM providers."""
    try:
        from backend.agents.runtime.gemini_runtime import GeminiRuntime, HAS_GENAI
        if HAS_GENAI:
            register_provider("gemini", GeminiRuntime)
    except ImportError:
        pass

    try:
        from backend.agents.runtime.openai_runtime import OpenAIRuntime, HAS_OPENAI
        if HAS_OPENAI:
            register_provider("openai", OpenAIRuntime)
    except ImportError:
        pass


_register_builtin_providers()
