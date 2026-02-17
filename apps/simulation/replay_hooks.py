"""Deterministic replay hooks for reproducibility checks."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, List, Mapping


_CANONICAL_KEYS = (
    "timestamp",
    "time",
    "symbol",
    "side",
    "type",
    "price",
    "volume",
    "qty",
    "ticket",
    "id",
)


def canonicalize_replay_events(events: Iterable[Mapping[str, Any]]) -> List[dict[str, Any]]:
    """
    Return a stable, deterministic representation of replay events.

    Ordering is deterministic by:
      timestamp/time -> symbol -> side/type -> ticket/id -> original index.
    """
    normalized: List[dict[str, Any]] = []
    for idx, raw in enumerate(events):
        event = dict(raw)
        canonical: dict[str, Any] = {k: event.get(k) for k in _CANONICAL_KEYS if k in event}
        canonical["_idx"] = idx
        normalized.append(canonical)

    def sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        ts = item.get("timestamp", item.get("time", ""))
        return (
            ts,
            item.get("symbol", ""),
            item.get("side", item.get("type", "")),
            item.get("ticket", item.get("id", "")),
            item.get("_idx", 0),
        )

    normalized.sort(key=sort_key)
    return normalized


def replay_fingerprint(events: Iterable[Mapping[str, Any]]) -> str:
    """Compute deterministic SHA-256 fingerprint for replay event sequence."""
    canonical = canonicalize_replay_events(events)
    payload = json.dumps(canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_replay_runs(
    baseline_events: Iterable[Mapping[str, Any]],
    candidate_events: Iterable[Mapping[str, Any]],
) -> tuple[bool, str]:
    """Compare two replay runs using deterministic fingerprints."""
    base_hash = replay_fingerprint(baseline_events)
    cand_hash = replay_fingerprint(candidate_events)
    if base_hash == cand_hash:
        return True, f"Replay consistent: {base_hash}"
    return False, f"Replay mismatch: baseline={base_hash} candidate={cand_hash}"

