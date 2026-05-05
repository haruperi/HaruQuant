"""Summarization/compression rules (Playbook §9.4)."""

from __future__ import annotations

from typing import Any, Dict, List


class ContextCompression:
    """Compress context using sliding window and abstraction levels."""

    def __init__(self, max_items: int = 50, abstraction_levels: int = 3) -> None:
        self.max_items = max_items
        self.abstraction_levels = abstraction_levels

    def compress(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress items to fit within max_items using sliding window."""
        if len(items) <= self.max_items:
            return items

        window_size = len(items) // self.abstraction_levels
        compressed: List[Dict[str, Any]] = []
        for level in range(self.abstraction_levels):
            start = level * window_size
            end = start + window_size
            chunk = items[start:end]
            if len(chunk) > 1:
                compressed.append({
                    "_summary": True,
                    "_level": level,
                    "_count": len(chunk),
                    "_first": chunk[0],
                    "_last": chunk[-1],
                })
            elif chunk:
                compressed.append(chunk[0])

        remaining = items[self.abstraction_levels * window_size:]
        compressed.extend(remaining)
        return compressed[-self.max_items:]

    def estimate_compression_ratio(self, items: List[Dict[str, Any]]) -> float:
        if not items:
            return 1.0
        compressed = self.compress(items)
        return len(compressed) / len(items)
