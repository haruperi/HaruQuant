from __future__ import annotations

from pathlib import Path

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    ResearchAgentWrapper,
)
from backend.data.database import ExecutionRepository, WorkflowRepository, apply_pending_migrations, default_migrations_dir


class _ScenarioResearchRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_obs_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "research_agent"},
                "environment": "paper",
                "operating_mode": "MODE-000",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "research_summary",
                    "severity": "info",
                    "source": "approved_sources",
                    "payload_ref_or_inline": {
                        "evidence_refs": ["evidence_001"],
                        "summary": "Research-only workflow produced grounded observations.",
                    },
                    "authority_state": {"grounded": True, "execution_authorized": False},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_research_only_workflow_runs_without_executable_intent_creation(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    WorkflowRepository(database_path).create_workflow(
        workflow_id="wf_research_001",
        workflow_type="research_only",
        environment="paper",
        operating_mode="MODE-000",
        state="CREATED",
        objective="Research EURUSD macro and technical context",
        initiator_type="user",
        initiator_id="operator_001",
    )

    wrapper = ResearchAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )
    result = wrapper.execute(
        runtime_agent=_ScenarioResearchRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_research_001",
            correlation_id="corr_research_001",
            agent_name="research_agent",
            input_payload={"query": "Summarize EURUSD drivers without execution intent."},
        ),
    )

    execution_repository = ExecutionRepository(database_path)
    with execution_repository._connect() as connection:  # noqa: SLF001
        execution_intent_count = connection.execute(
            "SELECT COUNT(*) FROM core_execution_intents"
        ).fetchone()[0]

    assert result.output_payload["contract_type"] == "ObservationEvent"
    assert result.output_payload["payload"]["authority_state"]["execution_authorized"] is False
    assert execution_intent_count == 0
