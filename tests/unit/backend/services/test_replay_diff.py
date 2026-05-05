from __future__ import annotations

from datetime import datetime, timezone

from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.replay_bundle.model import IntegrityManifest, ReplayBundle, ReplayBundlePayload
from haruquant.strategy import compare_replay_to_original
from haruquant.strategy import ReplayRunResult


def test_compare_replay_to_original_reports_missing_refs_and_hash_mismatch() -> None:
    original_bundle = ReplayBundle(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="service", id="replay_assembler"),
        environment="paper",
        operating_mode="MODE-002",
        payload=ReplayBundlePayload(
            replay_bundle_id="rpl_001",
            workflow_id="wf_001",
            completeness_status="complete",
            included_refs=["evidence_001", "log_001"],
            integrity_manifest=IntegrityManifest(
                manifest_hash="hash_original",
                manifest_algorithm="sha256",
            ),
            export_profile="audit_export",
            generated_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        ),
    )
    replay_result = ReplayRunResult(
        workflow_id="wf_001",
        replay_bundle_id="rpl_001",
        included_refs=("evidence_001",),
        reconstructed_hash="hash_replay",
    )

    report = compare_replay_to_original(
        original_bundle=original_bundle,
        replay_result=replay_result,
    )

    assert report.matches_original is False
    assert report.missing_refs == ("log_001",)
    assert report.unexpected_refs == ()
    assert report.original_hash == "hash_original"
    assert report.replay_hash == "hash_replay"
