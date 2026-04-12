"""Phase 3 usage examples for the agent runtime."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.trading import Engine, Trade  # noqa: E402
from backend.agents import (  # noqa: E402
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    ComplianceAgentWrapper,
    ContextRedactionMiddleware,
    CorrelationAgentWrapper,
    DrawdownAgentWrapper,
    EvaluatorOptimizerStep,
    EvaluatorOptimizerWorkflowRunner,
    EvaluatorRubric,
    EvaluatorRubricCriterion,
    ExecutionAgentWrapper,
    ExposureAgentWrapper,
    MonitoringAgentWrapper,
    OrchestratorAgentWrapper,
    OrchestratorWorkerTask,
    OrchestratorWorkerWorkflowRunner,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
    PortfolioAgentWrapper,
    PromptRegistryRecord,
    PromptRegistryService,
    PromptStatus,
    RegimeAgentWrapper,
    ResearchAgentWrapper,
    RoutingWorkflowBranch,
    RoutingWorkflowRunner,
    RuntimeTrajectoryLogService,
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
    SessionManager,
    SlippageAgentWrapper,
    StrategyAgentWrapper,
    ToolAllowlistMiddleware,
    TrajectoryEvaluationService,
    VolatilityAgentWrapper,
    WorkflowMemoryBindings,
    attach_prompt_provenance,
    attach_prompt_provenance_to_run_result,
    build_run_trajectory_log,
    detect_unsupported_assertions,
    enforce_refine_loop_limit,
    generate_refinement_recommendations,
    hash_schema_name,
)
from backend.agents.risk_governor_agent import RiskGovernorAgentAdapter  # noqa: E402
from backend.agents.runtime.retrieval_guard import evaluate_retrieved_text  # noqa: E402
from backend.contracts.evaluation_report.model import EvaluationReport, EvaluationReportPayload  # noqa: E402
from backend.contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload  # noqa: E402
from backend.contracts.incident_alert.model import IncidentAlert, IncidentAlertPayload  # noqa: E402
from backend.contracts.observation_event.model import ObservationEvent, ObservationEventPayload  # noqa: E402
from backend.contracts.risk_assessment_decision.model import (  # noqa: E402
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_hypothesis.model import (  # noqa: E402
    EvidenceItem,
    TradeHypothesis,
    TradeHypothesisPayload,
)
from backend.contracts.workflow_plan.model import WorkflowPlan, WorkflowPlanPayload  # noqa: E402
from backend.db import ResearchAuditRepository, WorkflowRepository, apply_pending_migrations  # noqa: E402


UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).resolve().parent
TMP_DIR = EXAMPLE_DIR / "_tmp" / "phase3_agent_runtime"
DB_PATH = TMP_DIR / "phase3_agent_runtime.sqlite3"
E2E_DB_PATH = TMP_DIR / "phase3_agent_runtime_e2e.sqlite3"
MIGRATIONS_DIR = Path(PROJECT_ROOT) / "backend" / "db" / "migrations"


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def reset_example_state() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_database(*, db_path: Path = DB_PATH) -> tuple[WorkflowRepository, ResearchAuditRepository]:
    applied = apply_pending_migrations(db_path, MIGRATIONS_DIR)
    print(f"Applied migrations on fresh database: {len(applied)}")
    workflow_repository = WorkflowRepository(db_path)
    workflow_repository.create_workflow(
        workflow_id="wf_phase3_example",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="CREATED",
        objective="Phase 3 agent runtime example",
        scope_json="{}",
        initiator_type="operator",
        initiator_id="ops:example",
        timeout_policy_json="{}",
        stop_conditions_json="[]",
    )
    return workflow_repository, ResearchAuditRepository(db_path)


class StaticRuntime:
    def __init__(
        self,
        output_payload: dict,
        *,
        tool_calls: tuple[dict, ...] = (),
        token_usage: dict[str, int] | None = None,
        final_state: str = "COMPLETED",
    ) -> None:
        self._output_payload = output_payload
        self._tool_calls = tool_calls
        self._token_usage = token_usage
        self._final_state = final_state

    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload=dict(self._output_payload),
            final_state=self._final_state,
            tool_calls=self._tool_calls,
            token_usage=self._token_usage,
        )


class StaticRiskDecisionService:
    def __init__(self, decision: RiskAssessmentDecision) -> None:
        self._decision = decision

    def evaluate(self, risk_request_id: str) -> RiskAssessmentDecision:
        _ = risk_request_id
        return self._decision


def initialize_sim_engine(*, symbol: str = "EURUSD") -> tuple[Engine, dict[str, object]]:
    engine = Engine(backend="sim")
    api = engine.api
    account = api.account_info()
    account["login"] = 123456
    account["server"] = "Agentic AI Simulator"
    account["company"] = "HaruQuant"
    account["balance"] = 100000.0
    account["profit"] = 0.0
    account["equity"] = 100000.0
    account["margin"] = 0.0
    account["margin_free"] = 100000.0
    account["commission"] = 7.0
    account["leverage"] = 400

    if api.symbol_info(symbol) is None:
        symbol_info = engine.client.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"simulator symbol metadata unavailable for {symbol}")
        engine.state.trading_symbols.append(symbol_info)

    trade = Trade(api)
    trade.SetExpertMagicNumber(12345)
    trade.SetDeviationInPoints(20)
    trade.SetTypeFillingBySymbol(symbol)

    info = api.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"simulator symbol metadata unavailable for {symbol}")

    open_result = trade.PositionOpen(
        symbol=symbol,
        order_type="BUY",
        volume=0.01,
        price=float(info.ask),
        sl=float(info.ask) - (8 * float(info.point) * 10),
        tp=float(info.ask) + (20 * float(info.point) * 10),
        comment="phase3-sim-position",
    )
    if int(open_result.retcode) not in (10008, 10009):
        raise RuntimeError(f"failed to seed phase3 simulator position: retcode={int(open_result.retcode)}")

    return engine, {
        "symbol": symbol,
        "account": api.account_info(),
        "symbol_info": api.symbol_info(symbol),
        "positions": api.positions_get(),
        "orders": api.orders_get(),
        "ticks": engine.client.get_ticks(symbol, count=3, as_dataframe=False),
    }


def base_envelope(contract_type: str) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "contract_type": contract_type,
        "workflow_id": "wf_phase3_example",
        "correlation_id": "corr_phase3_example",
        "causation_id": "evt_phase3_example",
        "timestamp_utc": "2026-04-09T10:00:00Z",
        "originator": {"type": "agent", "id": "phase3-example-agent"},
        "environment": "paper",
        "operating_mode": "MODE-002",
    }


def build_workflow_plan_payload() -> dict:
    return WorkflowPlan(
        **base_envelope("WorkflowPlan"),
        payload=WorkflowPlanPayload(
            plan_id="plan_001",
            selected_pattern="sequential_review",
            phase_steps=[{"phase": "plan", "owner": "orchestrator_agent"}],
            assigned_agents=["orchestrator_agent", "strategy_agent"],
            tool_permissions={"orchestrator_agent": ["research.lookup"]},
            success_conditions=["workflow planned"],
            escalation_conditions=["policy conflict"],
        ),
    ).model_dump(mode="json")


def build_trade_hypothesis_payload() -> dict:
    return TradeHypothesis(
        **base_envelope("TradeHypothesis"),
        payload=TradeHypothesisPayload(
            hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            thesis="EURUSD shows short-term continuation with contained spread.",
            entry_rationale="Momentum confirmation and liquidity conditions align.",
            invalidation_rationale="Thesis fails if volatility regime turns disorderly.",
            stop_loss_logic={"type": "fixed_points", "points": 8},
            take_profit_logic={"type": "fixed_points", "points": 20},
            holding_horizon="intraday",
            confidence=0.74,
            calibration_note="Confidence calibrated against paper data.",
            evidence=[
                EvidenceItem(
                    source_type="research",
                    ref_id="obs_001",
                    summary="Supporting regime observation.",
                    freshness_class="WARM",
                )
            ],
            required_validation_data=["spread_snapshot", "volatility_state"],
            strategy_family="trend",
            feature_version="features-v1",
            strategy_code_hash="sha256:strategy",
        ),
    ).model_dump(mode="json")


def build_observation_payload(observation_id: str, source: str, simulator_context: dict[str, object]) -> dict:
    symbol_info = simulator_context["symbol_info"]
    return ObservationEvent(
        **base_envelope("ObservationEvent"),
        payload=ObservationEventPayload(
            observation_id=observation_id,
            observation_type="advisory_observation",
            severity="info",
            source=source,
            payload_ref_or_inline={
                "summary": f"{source} advisory summary",
                "symbol": simulator_context["symbol"],
                "bid": float(getattr(symbol_info, "bid", 0.0) or 0.0),
                "ask": float(getattr(symbol_info, "ask", 0.0) or 0.0),
            },
            authority_state={"mode": "advisory_only", "broker_backend": "sim"},
            freshness_status="fresh",
            observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        ),
    ).model_dump(mode="json")


def build_incident_alert_payload() -> dict:
    return IncidentAlert(
        **base_envelope("IncidentAlert"),
        payload=IncidentAlertPayload(
            incident_id="inc_001",
            severity="warning",
            alert_type="OBSERVABILITY_DRIFT",
            summary="Latency elevated for one runtime call.",
            source="monitoring_agent",
            related_refs=["log_001"],
            recommended_action="Review trajectory logs before promoting workflow.",
            incident_state="open",
        ),
    ).model_dump(mode="json")


def build_evaluation_report_payload(agent_name: str) -> dict:
    return EvaluationReport(
        **base_envelope("EvaluationReport"),
        payload=EvaluationReportPayload(
            evaluation_id=f"eval_{agent_name}",
            target_type="workflow",
            target_ref="wf_phase3_example",
            rubric_name="phase3-advisory",
            rubric_scores={"grounding": 0.9, "clarity": 0.85},
            overall_score=0.875,
            verdict="pass",
            issues=[],
            improvement_actions=["Keep evidence bundle updated."],
            evaluator_identity=agent_name,
            evaluation_model_id="local-adk-wrapper-v1",
        ),
    ).model_dump(mode="json")


def build_execution_intent_payload(simulator_context: dict[str, object]) -> dict:
    symbol_info = simulator_context["symbol_info"]
    return ExecutionIntent(
        **base_envelope("ExecutionIntent"),
        payload=ExecutionIntentPayload(
            execution_intent_id="exec_001",
            proposal_id="proposal_001",
            risk_decision_id="risk_001",
            broker_action_type="submit_order",
            symbol=str(simulator_context["symbol"]),
            side="buy",
            size={"units": 10000},
            order_type="market",
            price_params={"reference_price": float(getattr(symbol_info, "ask", 0.0) or 0.0)},
            sl_tp_params={"stop_loss_points": 8, "take_profit_points": 20},
            idempotency_key="idem_001",
            expiry_time=datetime(2026, 4, 9, 10, 5, tzinfo=UTC),
            pre_send_validation_snapshot_ref="snap_001",
        ),
    ).model_dump(mode="json")


def build_risk_decision_payload() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        **base_envelope("RiskAssessmentDecision"),
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="proposal_001",
            decision="APPROVE",
            reasons=["all_checks_passed"],
            risk_metrics_snapshot={"gross_exposure": 12000.0},
            freshness_expiry=datetime(2026, 4, 9, 10, 30, tzinfo=UTC),
            policy_version="policy-risk-2026.04.09",
            formula_version="risk-formula-v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )


def example_01_runtime_foundation(runner: ADKRunnerService, simulator_context: dict[str, object]) -> ADKRunRequest:
    print_example_header("Example 01: Runtime Foundation")
    session_manager = SessionManager()
    session = session_manager.create_session(metadata={"channel": "operator-ui"})
    active_session = session_manager.activate_session(session.session_id)
    bound_session = session_manager.bind_workflow(
        session_id=active_session.session_id,
        workflow_id="wf_phase3_example",
    )

    memory = WorkflowMemoryBindings()
    memory.bind_workflow(workflow_id="wf_phase3_example", session_id=bound_session.session_id)
    memory.update_session_memory(workflow_id="wf_phase3_example", values={"role": "operator"})
    memory.update_workflow_memory(workflow_id="wf_phase3_example", values={"objective": "review EURUSD"})
    memory.update_cached_context(
        workflow_id="wf_phase3_example",
        values={"last_contract": "WorkflowIntent"},
    )
    binding = memory.append_replay_memory_ref(
        workflow_id="wf_phase3_example",
        replay_ref="replay_ref_001",
    )

    tool_policy = ToolAllowlistMiddleware()
    tool_decision = tool_policy.enforce(
        allowed_tools=("research.lookup", "risk.snapshot.read"),
        requested_tools=("research.lookup",),
    )

    redaction = ContextRedactionMiddleware()
    redacted = redaction.redact(
        {
            "approval_token": "top-secret-token",
            "api_key": "secret-key",
            "safe_context": {"goal": "review setup"},
        }
    )
    retrieval_report = evaluate_retrieved_text("Grounded market summary with no unsafe markers.")

    request = ADKRunRequest(
        workflow_id="wf_phase3_example",
        correlation_id="corr_phase3_example",
        agent_name="orchestrator_agent",
        input_payload={
            "goal": "Plan a paper trade review",
            "simulator_account_login": simulator_context["account"]["login"],
            "simulator_symbol": simulator_context["symbol"],
            "simulator_open_positions": len(simulator_context["positions"]),
            "simulator_open_orders": len(simulator_context["orders"]),
        },
        session_id=bound_session.session_id,
        prompt_version_id="prompt_orchestrator_001",
        allowed_tools=tool_decision.allowed_tools,
        metadata={"ui_channel": "operator"},
    )

    print(f"runner_name={runner.config.runner_name}")
    print(f"session_id={bound_session.session_id}")
    print(f"workflow_refs={binding.replay_memory_refs}")
    print(f"allowed_tools={tool_decision.allowed_tools}")
    print(f"redacted_paths={redacted.redacted_paths}")
    print(f"retrieval_safe={retrieval_report.safe}")
    return request


def example_02_prompt_and_version_registry(
    runner: ADKRunnerService,
    request: ADKRunRequest,
) -> tuple[ADKRunRequest, object]:
    print_example_header("Example 02: Prompt and Version Registry")
    prompt_registry = PromptRegistryService(
        (
            PromptRegistryRecord(
                prompt_version_id="prompt_orchestrator_001",
                agent_name="orchestrator_agent",
                prompt_name="orchestrator-default",
                semantic_version="1.0.0",
                environment="paper",
                instruction_text="Coordinate the workflow safely.",
                status=PromptStatus.ACTIVE,
                effective_from=datetime(2026, 4, 9, tzinfo=UTC),
            ),
        )
    )
    prompt_record = prompt_registry.get_active_version(
        agent_name="orchestrator_agent",
        environment="paper",
        at=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
    )
    payload_with_prompt = attach_prompt_provenance(
        {"goal": "Plan the workflow"},
        record=prompt_record,
    )
    runtime = StaticRuntime(
        build_workflow_plan_payload(),
        tool_calls=({"tool_name": "research.lookup", "latency_ms": 12},),
        token_usage={"prompt": 18, "completion": 10},
    )
    result = runner.run(
        agent=runtime,
        request=ADKRunRequest(
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            agent_name=request.agent_name,
            input_payload=payload_with_prompt,
            session_id=request.session_id,
            prompt_version_id=prompt_record.prompt_version_id,
            allowed_tools=request.allowed_tools,
            metadata=request.metadata,
        ),
    )
    result_with_provenance = attach_prompt_provenance_to_run_result(result, record=prompt_record)
    validation = CanonicalOutputValidator().validate(result_with_provenance.output_payload)
    print(f"prompt_version_id={prompt_record.prompt_version_id}")
    print(f"prompt_hash_prefix={prompt_record.content_hash[:8]}")
    print(f"validated_contract={validation.contract_type}")
    print(f"run_latency_ms={result_with_provenance.latency_ms}")
    return result_with_provenance, prompt_record


def example_03_core_agents(runner: ADKRunnerService, simulator_context: dict[str, object]) -> None:
    print_example_header("Example 03: Core Agents")
    validator = CanonicalOutputValidator()
    base_request = ADKRunRequest(
        workflow_id="wf_phase3_example",
        correlation_id="corr_phase3_example",
        agent_name="placeholder",
        input_payload={"goal": "example"},
    )
    wrappers = (
        ("orchestrator", OrchestratorAgentWrapper(runner, validator), StaticRuntime(build_workflow_plan_payload())),
        ("strategy", StrategyAgentWrapper(runner, validator), StaticRuntime(build_trade_hypothesis_payload())),
        ("research", ResearchAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_001", "research_agent", simulator_context))),
        ("monitoring", MonitoringAgentWrapper(runner, validator), StaticRuntime(build_incident_alert_payload())),
        ("portfolio", PortfolioAgentWrapper(runner, validator), StaticRuntime(build_evaluation_report_payload("portfolio_agent"))),
        ("compliance", ComplianceAgentWrapper(runner, validator), StaticRuntime(build_evaluation_report_payload("compliance_agent"))),
        ("execution", ExecutionAgentWrapper(runner, validator), StaticRuntime(build_execution_intent_payload(simulator_context))),
    )
    for name, wrapper, runtime in wrappers:
        result = wrapper.execute(
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id=base_request.workflow_id,
                correlation_id=base_request.correlation_id,
                agent_name=wrapper.agent_name,
                input_payload={"goal": f"{name} output"},
            ),
        )
        print(f"{name}_contract={result.output_payload['contract_type']}")

    risk_governor = RiskGovernorAgentAdapter(StaticRiskDecisionService(build_risk_decision_payload()))
    decision = risk_governor.evaluate(risk_request_id="risk_req_001")
    print(f"risk_governor_contract={decision.contract_type}")


def example_04_optional_sub_agents(runner: ADKRunnerService, simulator_context: dict[str, object]) -> None:
    print_example_header("Example 04: Optional Sub-Agents")
    validator = CanonicalOutputValidator()
    wrappers = (
        ("volatility", VolatilityAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_vol", "volatility_agent", simulator_context))),
        ("regime", RegimeAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_reg", "regime_agent", simulator_context))),
        ("slippage", SlippageAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_slip", "slippage_agent", simulator_context))),
        ("correlation", CorrelationAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_corr", "correlation_agent", simulator_context))),
        ("exposure", ExposureAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_expo", "exposure_agent", simulator_context))),
        ("drawdown", DrawdownAgentWrapper(runner, validator), StaticRuntime(build_observation_payload("obs_dd", "drawdown_agent", simulator_context))),
    )
    for name, wrapper, runtime in wrappers:
        result = wrapper.execute(
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="wf_phase3_example",
                correlation_id="corr_phase3_example",
                agent_name=wrapper.agent_name,
                input_payload={"goal": f"{name} output"},
            ),
        )
        print(f"{name}_contract={result.output_payload['contract_type']}")


def example_05_workflow_patterns(runner: ADKRunnerService, simulator_context: dict[str, object]) -> None:
    print_example_header("Example 05: Workflow Patterns")
    sequential = SequentialWorkflowRunner(runner).run(
        steps=(
            SequentialWorkflowStep(
                step_name="plan",
                runtime_agent=StaticRuntime(build_workflow_plan_payload()),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="orchestrator_agent",
                    input_payload={"step": "plan"},
                ),
            ),
            SequentialWorkflowStep(
                step_name="research",
                runtime_agent=StaticRuntime(build_observation_payload("obs_seq", "research_agent", simulator_context)),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="research_agent",
                    input_payload={"step": "research"},
                ),
            ),
        )
    )
    routed = RoutingWorkflowRunner(runner).run(
        route_key="incident",
        branches=(
            RoutingWorkflowBranch(
                route_key="plan",
                runtime_agent=StaticRuntime(build_workflow_plan_payload()),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="orchestrator_agent",
                    input_payload={"route": "plan"},
                ),
            ),
            RoutingWorkflowBranch(
                route_key="incident",
                runtime_agent=StaticRuntime(build_incident_alert_payload()),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="monitoring_agent",
                    input_payload={"route": "incident"},
                ),
            ),
        ),
    )
    parallel = ParallelWorkflowRunner(runner).run(
        tasks=(
            ParallelWorkflowTask(
                task_name="volatility",
                runtime_agent=StaticRuntime(build_observation_payload("obs_p1", "volatility_agent", simulator_context)),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="volatility_agent",
                    input_payload={"task": "volatility"},
                ),
            ),
            ParallelWorkflowTask(
                task_name="regime",
                runtime_agent=StaticRuntime(build_observation_payload("obs_p2", "regime_agent", simulator_context)),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="regime_agent",
                    input_payload={"task": "regime"},
                ),
            ),
        )
    )
    optimizer = EvaluatorOptimizerWorkflowRunner(runner).run(
        generator_step=EvaluatorOptimizerStep(
            runtime_agent=StaticRuntime(
                build_evaluation_report_payload("portfolio_agent"),
                token_usage={"prompt": 8, "completion": 5},
            ),
            request=ADKRunRequest(
                workflow_id="wf_phase3_example",
                correlation_id="corr_phase3_example",
                agent_name="portfolio_agent",
                input_payload={"task": "optimize"},
            ),
        ),
        evaluator=lambda result: 0.88 if result.output_payload["contract_type"] == "EvaluationReport" else 0.2,
        acceptance_threshold=0.8,
        max_iterations=3,
    )
    workers = OrchestratorWorkerWorkflowRunner(runner).run(
        tasks=(
            OrchestratorWorkerTask(
                worker_name="exposure_worker",
                runtime_agent=StaticRuntime(build_observation_payload("obs_w1", "exposure_agent", simulator_context)),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="exposure_agent",
                    input_payload={"task": "exposure"},
                ),
            ),
            OrchestratorWorkerTask(
                worker_name="drawdown_worker",
                runtime_agent=StaticRuntime(build_observation_payload("obs_w2", "drawdown_agent", simulator_context)),
                request=ADKRunRequest(
                    workflow_id="wf_phase3_example",
                    correlation_id="corr_phase3_example",
                    agent_name="drawdown_agent",
                    input_payload={"task": "drawdown"},
                ),
            ),
        )
    )
    refine_guard = enforce_refine_loop_limit(iteration_count=2, max_iterations=3)

    print(f"sequential_steps={len(sequential)}")
    print(f"routing_contract={routed.output_payload['contract_type']}")
    print(f"parallel_tasks={tuple(parallel.keys())}")
    print(f"optimizer_terminated_by={optimizer.terminated_by}")
    print(f"worker_count={len(workers)}")
    print(f"refine_guard_allowed={refine_guard.allowed}")


def example_06_evaluator_infrastructure() -> None:
    print_example_header("Example 06: Evaluator Infrastructure")
    rubric = EvaluatorRubric(
        rubric_name="phase3-runtime",
        criteria=(
            EvaluatorRubricCriterion("grounding", 0.6, 0.7),
            EvaluatorRubricCriterion("clarity", 0.4, 0.7),
        ),
    )
    evaluation = TrajectoryEvaluationService().evaluate(
        rubric=rubric,
        scores={"grounding": 0.9, "clarity": 0.8},
    )
    unsupported = detect_unsupported_assertions(
        claims=("EURUSD setup is fully grounded",),
        evidence_refs=("evidence_001",),
    )
    recommendations = generate_refinement_recommendations(
        evaluation=evaluation,
        unsupported_assertions=unsupported,
    )
    print(f"evaluation_verdict={evaluation.verdict}")
    print(f"schema_hash_prefix={hash_schema_name('WorkflowPlan')[:8]}")
    print(f"refinement_actions={recommendations.improvement_actions}")


def example_07_observability_and_trajectory_logs(
    audit_repository: ResearchAuditRepository,
    run_result,
    prompt_record,
) -> None:
    print_example_header("Example 07: Observability and Trajectory Logs")
    request = ADKRunRequest(
        workflow_id="wf_phase3_example",
        correlation_id="corr_phase3_example",
        agent_name="orchestrator_agent",
        input_payload={"goal": "Plan the workflow"},
        prompt_version_id=prompt_record.prompt_version_id,
    )
    log = build_run_trajectory_log(
        request=request,
        result=run_result,
        phase="plan",
        iteration_no=0,
        input_schema="WorkflowIntent",
        output_schema="WorkflowPlan",
        observation_payload_ref="obs_ref_001",
        evaluation_output_ref="eval_ref_001",
        signature="sig_001",
        artifact_ref="artifact://trajectory/001",
    )
    persisted = RuntimeTrajectoryLogService(audit_repository).persist(log)
    print(f"log_id={persisted.log_id}")
    print(f"agent_name={persisted.agent_name}")
    print(f"token_usage_json={persisted.token_usage_json}")
    print(f"tool_calls_json={persisted.tool_calls_json}")


def example_08_end_to_end_agent_runtime() -> None:
    print_example_header("Example 08: End-to-End Agent Runtime")
    if E2E_DB_PATH.exists():
        E2E_DB_PATH.unlink()
    sim_engine, sim_context = initialize_sim_engine()
    try:
        _, audit_repo = bootstrap_database(db_path=E2E_DB_PATH)
        runner_service = ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        )
        base_request = example_01_runtime_foundation(runner_service, sim_context)
        run_result, prompt_record = example_02_prompt_and_version_registry(runner_service, base_request)
        example_03_core_agents(runner_service, sim_context)
        example_04_optional_sub_agents(runner_service, sim_context)
        example_05_workflow_patterns(runner_service, sim_context)
        example_06_evaluator_infrastructure()
        example_07_observability_and_trajectory_logs(audit_repo, run_result, prompt_record)
    finally:
        sim_engine.client.shutdown()


if __name__ == "__main__":
    reset_example_state()
    sim_engine, sim_context = initialize_sim_engine()
    try:
        _, audit_repo = bootstrap_database()
        runner_service = ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        )
        base_request = example_01_runtime_foundation(runner_service, sim_context)
        run_result, prompt_record = example_02_prompt_and_version_registry(runner_service, base_request)
        example_03_core_agents(runner_service, sim_context)
        example_04_optional_sub_agents(runner_service, sim_context)
        example_05_workflow_patterns(runner_service, sim_context)
        example_06_evaluator_infrastructure()
        example_07_observability_and_trajectory_logs(audit_repo, run_result, prompt_record)
    finally:
        sim_engine.client.shutdown()
    example_08_end_to_end_agent_runtime()
