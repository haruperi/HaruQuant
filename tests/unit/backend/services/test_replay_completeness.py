from __future__ import annotations

from datetime import datetime, timezone

from backend.contracts.common import Originator
from backend.contracts.replay_bundle.model import IntegrityManifest, ReplayBundle, ReplayBundlePayload
from backend.db import ResearchAuditRepository
from backend.services.audit.replay_completeness import ReplayCompletenessChecker


def test_replay_completeness_checker_detects_missing_refs(tmp_path) -> None:
    repository = ResearchAuditRepository(tmp_path / "agentic.db")
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "CREATE TABLE research_evidence_bundles (evidence_bundle_id TEXT PRIMARY KEY, workflow_id TEXT, bundle_type TEXT NOT NULL, summary TEXT NOT NULL, content_ref TEXT, content_hash TEXT NOT NULL, freshness_status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "CREATE TABLE audit_trajectory_logs (log_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, correlation_id TEXT NOT NULL, agent_name TEXT NOT NULL, phase TEXT NOT NULL, iteration_no INTEGER NOT NULL, input_schema TEXT NOT NULL, input_hash TEXT NOT NULL, output_schema TEXT NOT NULL, output_hash TEXT NOT NULL, tool_calls_json TEXT NOT NULL, observation_payload_ref TEXT, evaluation_output_ref TEXT, latency_ms INTEGER NOT NULL, token_usage_json TEXT, final_state TEXT NOT NULL, signature TEXT, artifact_ref TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO research_evidence_bundles (evidence_bundle_id, workflow_id, bundle_type, summary, content_hash, freshness_status) VALUES ('evidence_001', 'wf_001', 'research_snapshot', 'summary', 'hash', 'fresh')"
        )
    bundle = ReplayBundle(
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
            completeness_status="partial",
            included_refs=["evidence_001", "log_missing"],
            integrity_manifest=IntegrityManifest(
                manifest_hash="hash",
                manifest_algorithm="sha256",
            ),
            export_profile="audit_export",
            generated_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        ),
    )

    report = ReplayCompletenessChecker(repository).check(bundle)

    assert report.complete is False
    assert report.missing_refs == ("log_missing",)
    assert report.available_refs == ("evidence_001",)
