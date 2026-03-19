"""File export helpers for risk reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_json_report(content: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
    return p


def save_markdown_report(content: str, path: str | Path) -> Path:
    p = Path(path)
    p.write_text(content, encoding="utf-8")
    return p
