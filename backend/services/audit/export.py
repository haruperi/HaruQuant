"""Audit export helpers keyed by compliance profile."""

from __future__ import annotations

from dataclasses import dataclass

from backend.data.database import ReplayBundleRecord
from backend.services.compliance_rollout import build_compliance_profile_labels


@dataclass(frozen=True)
class AuditExportPackage:
    """Compliance-profile-aware export payload."""

    export_profile: str
    compliance_profile_id: str
    replay_bundle_id: str
    object_store_uri: str
    labels: tuple[str, ...]


def build_audit_export_package(
    replay_bundle: ReplayBundleRecord,
    *,
    compliance_profile_id: str,
) -> AuditExportPackage:
    """Build a small export package labeled for the target compliance profile."""

    export_profile = replay_bundle.export_profile or "default_audit_export"
    return AuditExportPackage(
        export_profile=export_profile,
        compliance_profile_id=compliance_profile_id,
        replay_bundle_id=replay_bundle.replay_bundle_id,
        object_store_uri=replay_bundle.object_store_uri,
        labels=build_compliance_profile_labels(
            export_profile=export_profile,
            compliance_profile_id=compliance_profile_id,
        ),
    )
