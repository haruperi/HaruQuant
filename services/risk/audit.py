"""Risk audit artifact helpers."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import utc_stamp, write_json_artifact


def write_risk_audit(component_name: str, payload: dict[str, Any]) -> str:
    return write_json_artifact("reports/risk", f"{component_name}-{utc_stamp()}.json", payload)
