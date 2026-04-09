"""Evidence bundle automation services."""

from .assembler import LifecycleEvidenceBundle, assemble_lifecycle_evidence_bundle
from .manifest import EvidenceArtifact, build_evidence_bundle_manifest

__all__ = [
    "EvidenceArtifact",
    "LifecycleEvidenceBundle",
    "assemble_lifecycle_evidence_bundle",
    "build_evidence_bundle_manifest",
]
