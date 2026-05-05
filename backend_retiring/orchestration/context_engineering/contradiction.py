"""Contradiction resolution rules (Playbook §9.4)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ContradictionResolver:
    """Detect and resolve contradictions between context sources."""

    def detect(
        self, sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find contradictory values for the same key across sources."""
        if len(sources) < 2:
            return []
        contradictions: List[Dict[str, Any]] = []
        all_keys = set()
        for src in sources:
            all_keys.update(src.get("data", {}).keys())

        for key in all_keys:
            values = []
            for src in sources:
                val = src.get("data", {}).get(key)
                if val is not None:
                    values.append({"source": src.get("source_type", "unknown"), "value": val})

            if len(values) >= 2:
                unique_values = set(str(v["value"]) for v in values)
                if len(unique_values) > 1:
                    contradictions.append({
                        "key": key,
                        "sources": values,
                        "resolution": "use_most_trusted",
                    })
        return contradictions

    def resolve(
        self, contradiction: Dict[str, Any], trust_order: List[str]
    ) -> Optional[Any]:
        """Resolve a contradiction using trust order."""
        sources = contradiction.get("sources", [])
        for trusted in trust_order:
            for src in sources:
                if src["source"] == trusted:
                    return src["value"]
        return sources[0]["value"] if sources else None
