"""Small JSON persistence helpers for deterministic agent artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json_artifact(directory: str | Path, name: str, payload: dict[str, Any]) -> str:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def stable_id(prefix: str, value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    safe = "-".join(part for part in safe.split("-") if part)
    return f"{prefix}-{safe[:48] or utc_stamp().lower()}"


__all__ = ["stable_id", "utc_stamp", "write_json_artifact"]
