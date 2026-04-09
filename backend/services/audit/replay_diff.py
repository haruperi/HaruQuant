"""Replay-versus-original comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.replay_bundle.model import ReplayBundle

from .replay_runner import ReplayRunResult


@dataclass(frozen=True)
class ReplayComparisonReport:
    """Stable diff between the original bundle and a replay run."""

    matches_original: bool
    missing_refs: tuple[str, ...]
    unexpected_refs: tuple[str, ...]
    original_hash: str
    replay_hash: str


def compare_replay_to_original(
    *,
    original_bundle: ReplayBundle,
    replay_result: ReplayRunResult,
) -> ReplayComparisonReport:
    """Compare one replay run against the original stored bundle."""

    original_refs = tuple(original_bundle.payload.included_refs)
    replay_refs = replay_result.included_refs
    missing_refs = tuple(ref for ref in original_refs if ref not in replay_refs)
    unexpected_refs = tuple(ref for ref in replay_refs if ref not in original_refs)
    original_hash = original_bundle.payload.integrity_manifest.manifest_hash
    replay_hash = replay_result.reconstructed_hash
    return ReplayComparisonReport(
        matches_original=not missing_refs and not unexpected_refs and original_hash == replay_hash,
        missing_refs=missing_refs,
        unexpected_refs=unexpected_refs,
        original_hash=original_hash,
        replay_hash=replay_hash,
    )
