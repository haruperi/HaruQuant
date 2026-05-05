from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend_retiring.contracts.replay_bundle.model import ReplayBundle, ReplayBundlePayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend_retiring"
    / "contracts"
    / "replay_bundle"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_replay_bundle_accepts_valid_example():
    contract = ReplayBundle.model_validate(_load_example("valid", "complete_bundle.json"))

    assert contract.contract_type == "ReplayBundle"
    assert contract.payload.completeness_status == "complete"
    assert contract.payload.integrity_manifest.manifest_algorithm == "sha256"


def test_replay_bundle_rejects_invalid_completeness_status():
    with pytest.raises(ValidationError):
        ReplayBundle.model_validate(_load_example("invalid", "bad_completeness_status.json"))


def test_replay_bundle_payload_requires_integrity_manifest():
    with pytest.raises(ValidationError):
        ReplayBundlePayload(
            replay_bundle_id="rpb_01",
            workflow_id="wf_01",
            completeness_status="complete",
            included_refs=["prop_01"],
            export_profile="standard_replay",
            generated_at="2026-04-08T10:25:59Z",
        )
