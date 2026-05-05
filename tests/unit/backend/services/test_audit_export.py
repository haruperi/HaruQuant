from __future__ import annotations

from backend.data.database import ReplayBundleRecord
from services.strategy.evidence.audit.export import build_audit_export_package


def test_build_audit_export_package_labels_profile_and_export_mode() -> None:
    package = build_audit_export_package(
        ReplayBundleRecord(
            replay_bundle_id="rpb_001",
            workflow_id="wf_001",
            bundle_hash="hash_001",
            object_store_uri="s3://bucket/replay_001",
            completeness_status="complete",
            export_profile="regulatory_export",
            integrity_manifest_ref="manifest_001",
            created_at="2026-04-09T10:00:00Z",
        ),
        compliance_profile_id="comp_eu_mifid",
    )

    assert package.export_profile == "regulatory_export"
    assert package.labels == ("regulatory_export", "profile:comp_eu_mifid")
