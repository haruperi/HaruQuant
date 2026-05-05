"""Canonical serialization helpers for contract models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any, TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize_for_json(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _normalize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def canonical_json_dumps(value: Any) -> str:
    """Serialize a model or mapping to deterministic canonical JSON."""

    normalized = _normalize_for_json(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_json_loads(payload: str) -> Any:
    """Parse canonical JSON back into a Python structure."""

    return json.loads(payload)


def serialize_contract(model: BaseModel) -> str:
    """Serialize a Pydantic contract model to canonical JSON."""

    return canonical_json_dumps(model)


def deserialize_contract(payload: str, model_type: type[ModelT]) -> ModelT:
    """Deserialize canonical JSON into the requested Pydantic model type."""

    return model_type.model_validate(canonical_json_loads(payload))
