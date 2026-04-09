from __future__ import annotations

from pathlib import Path

from backend.contracts.common import Originator
from backend.contracts.observation_event.model import ObservationEvent, ObservationEventPayload
from backend.db import apply_pending_migrations
from backend.services.monitoring import ObservationIngestionService


def test_observation_ingestion_persists_observation_event(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = ObservationIngestionService(database_path)

    with service._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )

    record = service.ingest(
        ObservationEvent(
            workflow_id="wf_001",
            correlation_id="corr_001",
            causation_id="evt_001",
            timestamp_utc="2026-04-09T10:00:00Z",
            originator=Originator(type="agent", id="monitoring_agent"),
            environment="paper",
            operating_mode="MODE-002",
            payload=ObservationEventPayload(
                observation_id="obs_001",
                observation_type="spread_check",
                severity="warning",
                source="mt5_mcp",
                payload_ref_or_inline={"spread_pips": 2.1},
                authority_state={"state": "PROVISIONAL"},
                freshness_status="fresh",
                observed_at="2026-04-09T10:00:00Z",
            ),
        )
    )

    assert record.observation_id == "obs_001"
    assert record.payload_json == '{"spread_pips":2.1}'
    assert record.authority_state == '{"state":"PROVISIONAL"}'
