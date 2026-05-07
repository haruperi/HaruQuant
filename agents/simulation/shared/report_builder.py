"""Report builders for Simulation Department outputs."""

from __future__ import annotations

from typing import Any


def build_markdown_report(title: str, payload: dict[str, Any]) -> str:
    lines = [f"# {title}", "", "## Deterministic Summary"]
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"
