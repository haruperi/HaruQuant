from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend_retiring.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    OrchestratorAgentWrapper,
    PromptRegistryRecord,
    PromptRegistryService,
    PromptStatus,
    RuntimeTrajectoryLogService,
    attach_prompt_provenance_to_run_result,
    build_run_trajectory_log,
)
from data.database import ResearchAuditRepository, apply_pending_migrations


class _FakeProdOrchestratorRuntime:
    def __init__(self, *, operating_mode: str) -> None:
        self._operating_mode = operating_mode

    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_prod_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "orchestrator_agent"},
                "environment": "prod",
                "operating_mode": self._operating_mode,
                "contract_type": "WorkflowPlan",
                "schema_version": "1.0.0",
                "payload": {
                    "plan_id": "plan_prod_001",
                    "selected_pattern": "sequential",
                    "phase_steps": [
                        {
                            "step_id": "collect_evidence",
                            "phase": "reason",
                            "owner_agent": "strategy_agent",
                            "goal": "collect evidence",
                            "input_contract_type": "WorkflowIntent",
                            "expected_output_contract_type": "TradeHypothesis",
                        },
                        {
                            "step_id": "risk_gate",
                            "phase": "risk",
                            "owner_agent": "risk_governor_agent",
                            "goal": "apply deterministic checks",
                            "input_contract_type": "TradeHypothesis",
                            "expected_output_contract_type": "RiskAssessmentDecision",
                        },
                    ],
                },
            },
            tool_calls=({"tool_name": "research.lookup", "latency_ms": 11},),
            token_usage={"prompt": 12, "completion": 8},
        )


@pytest.mark.parametrize("operating_mode", ["MODE-003", "MODE-004"])
def test_production_workflows_emit_trajectory_logs_and_runtime_assertions(
    tmp_path,
    operating_mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "data" / "database" / "migrations"
    database_path = tmp_path / f"agentic-{operating_mode}.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_prod_001", "trade_review", "prod", operating_mode, "CREATED", "Review live setup", "{}", "operator", "operator_001", "{}", "[]"),
        )

    prompt_registry = PromptRegistryService(
        (
            PromptRegistryRecord(
                prompt_version_id="prompt_prod_001",
                agent_name="orchestrator_agent",
                prompt_name="orchestrator-prod",
                semantic_version="1.0.0",
                environment="prod",
                instruction_text="Coordinate the live workflow safely.",
                status=PromptStatus.ACTIVE,
                effective_from=datetime(2026, 4, 9, tzinfo=timezone.utc),
            ),
        )
    )
    prompt_record = prompt_registry.get_active_version(
        agent_name="orchestrator_agent",
        environment="prod",
        at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
    )
    wrapper = OrchestratorAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )
    request = ADKRunRequest(
        workflow_id="wf_prod_001",
        correlation_id=f"corr_{operating_mode}",
        agent_name="orchestrator_agent",
        input_payload={"goal": "Review live EURUSD setup"},
        prompt_version_id=prompt_record.prompt_version_id,
        allowed_tools=("research.lookup",),
    )

    result = wrapper.execute(
        runtime_agent=_FakeProdOrchestratorRuntime(operating_mode=operating_mode),
        request=request,
    )
    validated = CanonicalOutputValidator().validate(result.output_payload)
    result_with_provenance = attach_prompt_provenance_to_run_result(result, record=prompt_record)
    persisted = RuntimeTrajectoryLogService(repository).persist(
        build_run_trajectory_log(
            request=request,
            result=result_with_provenance,
            phase="plan",
            iteration_no=0,
            input_schema="WorkflowIntent",
            output_schema="WorkflowPlan",
        )
    )

    assert validated.contract_type == "WorkflowPlan"
    assert persisted.workflow_id == "wf_prod_001"
    assert persisted.final_state == "COMPLETED"
    assert persisted.tool_calls_json is not None and "call_hash" in persisted.tool_calls_json
    assert persisted.token_usage_json is not None and '"model":"gemini-2.5-flash"' in persisted.token_usage_json
    assert f'"prompt_hash":"{prompt_record.content_hash}"' in persisted.token_usage_json
