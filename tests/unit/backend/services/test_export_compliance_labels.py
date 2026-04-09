from __future__ import annotations

from backend.db import ReplayBundleRecord
from backend.services.audit import build_audit_export_package


def test_build_audit_export_package_labels_export_by_active_compliance_profile() -> None:
    package = build_audit_export_package(
        ReplayBundleRecord(
            replay_bundle_id="rpl_001",
            workflow_id="wf_001",
            bundle_hash="hash_001",
            object_store_uri="memory://replay/rpl_001",
            completeness_status="complete",
            export_profile="regulatory_export",
            integrity_manifest_ref="manifest_001",
            created_at="2026-04-09T10:00:00Z",
        ),
        compliance_profile_id="comp_uae_enterprise",
    )

    assert package.labels == ("regulatory_export", "profile:comp_uae_enterprise")
