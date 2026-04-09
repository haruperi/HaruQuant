"""Broker response normalization for the MT5 MCP boundary."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "_asdict"):
        return value._asdict()
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return {key: val for key, val in vars(value).items() if not key.startswith("_")}
    return {"value": value}


def normalize_broker_response(response: Any) -> dict[str, Any]:
    """Normalize MT5 order-send style responses into a stable receipt shape."""

    payload = _to_dict(response)
    retcode = payload.get("retcode")
    status = "accepted" if retcode in {0, 10008, 10009} else "rejected"
    return {
        "status": status,
        "retcode": retcode,
        "order_id": payload.get("order") or payload.get("order_id"),
        "deal_id": payload.get("deal") or payload.get("deal_id"),
        "comment": payload.get("comment"),
        "request_echo": payload.get("request"),
        "raw": payload,
    }


__all__ = ["normalize_broker_response"]
