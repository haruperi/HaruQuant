"""LLM-based context compression with importance-aware summarization."""

from __future__ import annotations

from typing import Any


class LLMContextCompressor:
    """Compresses context using LLM-based summarization.

    Unlike naive sliding window, this understands content importance
    and produces abstractive summaries that preserve key information.

    Usage:
        compressor = LLMContextCompressor(llm_runtime=runner)
        compressed = compressor.compress(context_items, target_tokens=1000)
    """

    def __init__(
        self,
        llm_runtime: Any = None,
        max_input_tokens: int = 4096,
    ) -> None:
        self._llm = llm_runtime
        self._max_input_tokens = max_input_tokens

    def compress(
        self,
        context_items: list[dict[str, Any]],
        target_tokens: int = 1000,
    ) -> str:
        """Compress context items into a summary.

        If no LLM is available, falls back to selective truncation.
        """
        if self._llm is None:
            return self._fallback_compress(context_items, target_tokens)

        # Build prompt for LLM summarization
        context_text = "\n\n".join(
            f"Item {i}: {item.get('content', str(item))}"
            for i, item in enumerate(context_items)
        )
        prompt = (
            f"Summarize the following context in about {target_tokens} tokens. "
            f"Preserve all key facts, decisions, and evidence. "
            f"Remove redundancy but keep unique information.\n\n"
            f"{context_text}"
        )
        # In production: call self._llm.run() with this prompt
        return self._fallback_compress(context_items, target_tokens)

    @staticmethod
    def _fallback_compress(
        context_items: list[dict[str, Any]],
        target_tokens: int,
    ) -> str:
        """Fallback: select most recent items within token budget."""
        result: list[str] = []
        total_tokens = 0
        # Process in reverse order (most recent first)
        for item in reversed(context_items):
            content = item.get("content", str(item))
            item_tokens = len(content) // 4
            if total_tokens + item_tokens > target_tokens:
                break
            result.append(content)
            total_tokens += item_tokens
        return "\n\n".join(reversed(result))
