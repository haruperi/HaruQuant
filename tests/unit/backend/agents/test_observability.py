from __future__ import annotations

from pathlib import Path

from backend.agents import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    RuntimeTrajectoryLog,
    RuntimeTrajectoryLogService,
    build_run_trajectory_log,
)
from backend.data.database import ResearchAuditRepository, apply_pending_migrations
from backend.agents.runtime.evaluator import hash_schema_name


def test_runtime_trajectory_log_service_persists_to_audit_store(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "data" / "database" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )

    service = RuntimeTrajectoryLogService(repository)
    record = service.persist(
        RuntimeTrajectoryLog(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="strategy_agent",
            phase="reason",
            iteration_no=1,
            input_schema="WorkflowIntent",
            input_payload={"objective": "review eurusd"},
            output_schema="TradeHypothesis",
            output_payload={"symbol": "EURUSD", "direction": "buy"},
            latency_ms=85,
            final_state="COMPLETED",
            tool_calls=({"tool_name": "research.lookup", "latency_ms": 12},),
            token_usage={"prompt": 10, "completion": 7},
            artifact_ref="artifact_001",
        )
    )

    assert record.workflow_id == "wf_001"
    assert record.correlation_id == "corr_001"
    assert record.agent_name == "strategy_agent"
    assert record.input_schema == "WorkflowIntent"
    assert record.output_schema == "TradeHypothesis"
    assert '"tool_name":"research.lookup"' in record.tool_calls_json
    assert '"prompt":10' in record.token_usage_json
    assert record.artifact_ref == "artifact_001"


class _FakeRuntimeAgent:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={"route": request.input_payload["route"]},
            final_state="COMPLETED",
        )


def test_build_run_trajectory_log_propagates_workflow_and_correlation_ids() -> None:
    runner = ADKRunnerService(
        ADKRunnerConfig(
            runner_name="agent-runtime",
            default_model="gemini-2.5-flash",
        )
    )
    request = ADKRunRequest(
        workflow_id="wf_123",
        correlation_id="corr_123",
        agent_name="orchestrator_agent",
        input_payload={"route": "research"},
    )

    result = runner.run(agent=_FakeRuntimeAgent(), request=request)
    log = build_run_trajectory_log(
        request=request,
        result=result,
        phase="plan",
        iteration_no=0,
        input_schema="WorkflowIntent",
        output_schema="WorkflowPlan",
    )

    assert log.workflow_id == "wf_123"
    assert log.correlation_id == "corr_123"
    assert log.agent_name == "orchestrator_agent"


def test_runtime_trajectory_log_captures_schema_names_and_hashes() -> None:
    log = RuntimeTrajectoryLog(
        workflow_id="wf_123",
        correlation_id="corr_123",
        agent_name="research_agent",
        phase="research",
        iteration_no=0,
        input_schema="WorkflowIntent",
        input_payload={"query": "eurusd macro"},
        output_schema="ObservationEvent",
        output_payload={"summary": "fresh signal"},
        latency_ms=44,
        final_state="COMPLETED",
    )
    same_payload_different_schema = RuntimeTrajectoryLog(
        workflow_id="wf_123",
        correlation_id="corr_123",
        agent_name="research_agent",
        phase="research",
        iteration_no=0,
        input_schema="TradeProposal",
        input_payload={"query": "eurusd macro"},
        output_schema="ObservationEvent",
        output_payload={"summary": "fresh signal"},
        latency_ms=44,
        final_state="COMPLETED",
    )

    assert log.input_schema_hash == hash_schema_name("WorkflowIntent")
    assert log.output_schema_hash == hash_schema_name("ObservationEvent")
    assert log.input_hash != same_payload_different_schema.input_hash


def test_runtime_trajectory_log_captures_tool_call_hashes_and_latency() -> None:
    log = RuntimeTrajectoryLog(
        workflow_id="wf_123",
        correlation_id="corr_123",
        agent_name="research_agent",
        phase="research",
        iteration_no=0,
        input_schema="WorkflowIntent",
        input_payload={"query": "eurusd macro"},
        output_schema="ObservationEvent",
        output_payload={"summary": "fresh signal"},
        latency_ms=44,
        final_state="COMPLETED",
        tool_calls=(
            {
                "tool_name": "research.lookup",
                "latency_ms": 12,
                "arguments": {"query": "eurusd macro"},
            },
        ),
    )

    assert '"call_hash":"' in log.tool_calls_json
    assert '"latency_ms":12' in log.tool_calls_json
    assert log.latency_ms == 44


def test_build_run_trajectory_log_captures_model_prompt_and_verdict_provenance() -> None:
    request = ADKRunRequest(
        workflow_id="wf_123",
        correlation_id="corr_123",
        agent_name="research_agent",
        input_payload={"query": "eurusd macro"},
        prompt_version_id="prompt_002",
    )
    result = ADKRunResult(
        runner_name="agent-runtime",
        runtime_version="local-adk-wrapper-v1",
        agent_name="research_agent",
        workflow_id="wf_123",
        correlation_id="corr_123",
        session_id="sess_001",
        model="gemini-2.5-pro",
        prompt_version_id="prompt_002",
        prompt_hash="hash_prompt_002",
        latency_ms=61,
        output_payload={"summary": "fresh signal"},
        final_state="COMPLETED",
        tool_calls=(),
        token_usage={"prompt": 12, "completion": 8},
    )

    log = build_run_trajectory_log(
        request=request,
        result=result,
        phase="research",
        iteration_no=1,
        input_schema="WorkflowIntent",
        output_schema="ObservationEvent",
    )

    assert log.final_state == "COMPLETED"
    assert '"model":"gemini-2.5-pro"' in log.token_usage_json
    assert '"prompt_hash":"hash_prompt_002"' in log.token_usage_json
    assert '"completion":8' in log.token_usage_json
