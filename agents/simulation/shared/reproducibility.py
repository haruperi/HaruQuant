"""Reproducibility helpers for simulation packages."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reproducibility_status(*, data_hash: str, config_hash: str, strategy_code_hash: str) -> dict[str, str | bool]:
    return {
        "data_hash": data_hash,
        "config_hash": config_hash,
        "strategy_code_hash": strategy_code_hash,
        "reproducible": bool(data_hash and config_hash and strategy_code_hash),
    }
