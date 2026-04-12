"""Phase 2 usage examples for the deterministic safety core."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.core import FixedClock, generate_prefixed_id  # noqa: E402
from apps.core.time_utils import evaluate_board_baseline_freshness  # noqa: E402
from apps.mt5 import get_mt5_api  # noqa: E402
from apps.trading import Engine, Trade  # noqa: E402
from backend.contracts.common import Originator  # noqa: E402
from backend.contracts.execution_intent.model import (  # noqa: E402
    ExecutionIntent,
    ExecutionIntentPayload,
)
from backend.contracts.risk_assessment_decision.model import LimitConstraint  # noqa: E402
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload  # noqa: E402
from backend.db import (  # noqa: E402
    ExecutionRepository,
    ProposalRepository,
    RiskRepository,
    WorkflowRepository,
    apply_pending_migrations,
)
from backend.mcp.mt5_mcp import (  # noqa: E402
    MT5ReadOnlyTools,
    MT5MutatingTools,
    MT5ToolAuthorizer,
    create_mt5_mcp_server,
    normalize_broker_response,
    reject_stale_execution_inputs,
)
from backend.orchestration.workflow import KillSwitchState, ProposalState  # noqa: E402
from backend.services.execution import (  # noqa: E402
    SymbolMetadataCacheEntry,
    aggregate_readiness_results,
    validate_fill_mode_compatibility,
    validate_market_open,
    validate_price_freshness,
    validate_risk_decision_for_execution,
    validate_stop_and_freeze_levels,
    validate_symbol_tradability,
    validate_terminal_connectivity,
)
from backend.services.policy import (  # noqa: E402
    ApprovalPolicy,
    ComplianceProfile,
    PolicyBundle,
    PolicyScope,
    PolicyVersion,
    RetentionPolicy,
)
from backend.services.reconciliation import (  # noqa: E402
    BrokerTruthFetcher,
    ReconciliationIncidentService,
    ReconciliationPersistenceService,
    ReconciliationStartupLoader,
    build_local_execution_truth,
    compare_execution_truth,
    evaluate_retry_guard,
)
from backend.services.risk import (  # noqa: E402
    AccountSnapshot,
    MarketSnapshot,
    PackedRiskDecisionArtifacts,
    PortfolioSnapshot,
    PositionExposure,
    RiskDecisionEnvelopeContext,
    RiskDecisionPersistenceService,
    RiskDecisionProvenance,
    RiskRequestAssemblyContext,
    assemble_risk_assessment_request,
    calculate_correlation_concentration,
    calculate_currency_concentration,
    calculate_drawdown_state,
    calculate_exposure_summary,
    calculate_margin_utilization,
    calculate_strategy_family_concentration,
    calculate_symbol_concentration,
    calculate_volatility_adjusted_size,
    compose_risk_decision,
    enforce_risk_decision_expiry,
    evaluate_compliance_profile_compatibility,
    evaluate_operating_mode_compatibility,
    evaluate_regime_restriction,
    evaluate_session_restrictions,
    evaluate_spread_slippage_precheck,
    invalidate_for_material_proposal_change,
    pack_risk_decision_rationale_and_provenance,
    CorrelationPair,
)
from backend.services.safety import (  # noqa: E402
    KillSwitchAuditService,
    KillSwitchService,
    RecoveryApproval,
    evaluate_new_entry_block,
    require_hard_trigger_recovery_dual_auth,
)


UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).resolve().parent
TMP_DIR = EXAMPLE_DIR / "_tmp" / "phase2_deterministic_safety_core"
DB_PATH = TMP_DIR / "phase2_deterministic_safety_core.sqlite3"
MIGRATIONS_DIR = Path(PROJECT_ROOT) / "backend" / "db" / "migrations"
mt5 = get_mt5_api()


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def reset_example_state() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_database() -> tuple[RiskRepository, ExecutionRepository, WorkflowRepository, ProposalRepository]:
    applied = apply_pending_migrations(DB_PATH, MIGRATIONS_DIR)
    print(f"Applied migrations on fresh database: {len(applied)}")
    return (
        RiskRepository(DB_PATH),
        ExecutionRepository(DB_PATH),
        WorkflowRepository(DB_PATH),
        ProposalRepository(DB_PATH),
    )


class SimulatorMT5GatewayAdapter:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._api = engine.api
        self._client = engine.client

    def account_info(self):
        return self._api.account_info()

    def positions_get(self):
        return self._api.positions_get()

    def orders_get(self):
        return self._api.orders_get()

    def symbol_info(self, symbol: str):
        return self._api.symbol_info(symbol)

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True):
        return self._client.get_ticks(symbol, count=count, as_dataframe=as_dataframe)

    def order_send(self, request: dict):
        return self._api.order_send(request)


def initialize_sim_engine(*, symbol: str = "EURUSD") -> tuple[Engine, Trade]:
    engine = Engine(backend="sim")
    api = engine.api
    account = api.account_info()
    account["login"] = 123456
    account["server"] = "Agentic AI Simulator"
    account["company"] = "HaruQuant"
    account["balance"] = 100000.0
    account["credit"] = 0.0
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
    return engine, trade


def seed_simulator_broker_state(*, engine: Engine, trade: Trade, symbol: str = "EURUSD") -> None:
    info = engine.api.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"simulator symbol metadata unavailable for {symbol}")

    point = float(info.point)
    buy_price = float(info.ask)
    open_result = trade.PositionOpen(
        symbol=symbol,
        order_type="BUY",
        volume=0.01,
        price=buy_price,
        sl=buy_price - (8 * point * 10),
        tp=buy_price + (20 * point * 10),
        comment="client-order-001",
    )
    if int(open_result.retcode) not in (10008, 10009):
        raise RuntimeError(f"failed to seed simulator position: retcode={int(open_result.retcode)}")

    pending_price = float(info.ask) + (25 * point * 10)
    pending_result = trade.OrderOpen(
        symbol=symbol,
        order_type="BUY_STOP",
        volume=0.01,
        price=pending_price,
        sl=0.0,
        tp=0.0,
        comment="client-order-pending-001",
    )
    if int(pending_result.retcode) not in (10008, 10009):
        raise RuntimeError(f"failed to seed simulator pending order: retcode={int(pending_result.retcode)}")


def build_originator() -> Originator:
    return Originator(type="service", id="phase2-example")


def build_policy_bundle() -> PolicyBundle:
    return PolicyBundle(
        scope=PolicyScope(environment="test", workflow_type="live_execution", role="risk_manager"),
        policies=(
            PolicyVersion(
                policy_version_id="policy-risk-2026-04-09",
                policy_type="risk_limits",
                version="2026.04.09",
                status="active",
                effective_from="2026-04-09T09:00:00Z",
                content_hash="sha256:risk-limits",
            ),
        ),
        bundle_version="bundle-2026.04.09",
        metadata={"formula_version": "risk-formula-v1"},
    )


def build_compliance_profile() -> ComplianceProfile:
    return ComplianceProfile(
        compliance_profile_id="uae-enterprise-v1",
        name="UAE Enterprise",
        version="1.0.0",
        active=True,
        jurisdictions=("AE",),
        retention=RetentionPolicy(30, 365, 365, True),
        approvals=ApprovalPolicy(
            dual_auth_live_override=True,
            hard_kill_recovery_dual_auth=True,
            policy_change_dual_auth=True,
            required_roles=("risk_manager", "compliance"),
        ),
    )


def build_trade_proposal(*, workflow_id: str, direction: str = "buy", size_units: int = 10000) -> TradeProposal:
    return TradeProposal(
        workflow_id=workflow_id,
        correlation_id=generate_prefixed_id("corr"),
        causation_id=generate_prefixed_id("cause"),
        originator=build_originator(),
        environment="test",
        operating_mode="MODE-002",
        compliance_profile_id="uae-enterprise-v1",
        payload=TradeProposalPayload(
            proposal_id=generate_prefixed_id("proposal"),
            source_hypothesis_id=generate_prefixed_id("hyp"),
            symbol="EURUSD",
            direction=direction,
            candidate_price_logic={"entry": "market", "reference_price": 1.0865},
            proposed_size={"units": size_units, "risk_fraction": 0.01},
            operating_envelope={"mode": "paper", "max_slippage_points": 3},
            session_restrictions={"allowed_window": ["09:00", "17:00"]},
            expiry_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
            transformation_version="proposal-transform-v1",
            readiness_state="ready_for_risk",
        ),
    )


def seed_trade_hypothesis(*, proposal: TradeProposal) -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO core_trade_hypotheses (
                hypothesis_id,
                workflow_id,
                strategy_id,
                symbol,
                direction,
                thesis_text,
                entry_rationale,
                invalidation_rationale,
                stop_loss_logic_json,
                take_profit_logic_json,
                holding_horizon,
                confidence_score,
                calibration_note,
                strategy_family,
                feature_version,
                strategy_code_hash,
                evidence_bundle_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal.payload.source_hypothesis_id,
                proposal.workflow_id,
                "strategy-eurusd-01",
                proposal.payload.symbol,
                proposal.payload.direction,
                "Short-term EURUSD continuation setup.",
                "Enter on market confirmation with bounded spread.",
                "Invalidate if spread or volatility regime drifts beyond limits.",
                json.dumps({"type": "fixed_points", "points": 8}, sort_keys=True),
                json.dumps({"type": "fixed_points", "points": 20}, sort_keys=True),
                "intraday",
                0.72,
                "Seeded by Phase 2 example.",
                "trend",
                "features-v1",
                "sha256:strategy-code",
                None,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def example_01_freshness_and_snapshots() -> None:
    print_example_header("Example 01: Freshness and Snapshot Infrastructure")
    freshness = evaluate_board_baseline_freshness(
        {
            "best_bid_ask_tick": datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
            "risk_decision": datetime(2026, 4, 9, 8, 59, 45, tzinfo=UTC),
            "strategy_lifecycle_state": datetime(2026, 4, 9, 8, 55, 0, tzinfo=UTC),
        },
        clock=FixedClock(datetime(2026, 4, 9, 9, 0, 1, tzinfo=UTC)),
    )
    account_snapshot = AccountSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("acct"),
        account_id="paper-account-01",
        observed_at=datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
        balance=100000.0,
        equity=100500.0,
        free_margin=95000.0,
        margin_used=5500.0,
        currency="USD",
    )
    portfolio_snapshot = PortfolioSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("port"),
        portfolio_id="portfolio-01",
        observed_at=datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
        open_position_count=3,
        gross_exposure=45000.0,
        net_exposure=15000.0,
        symbols=("EURUSD", "GBPUSD", "USDJPY"),
    )
    market_snapshot = MarketSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("mkt"),
        symbol="EURUSD",
        snapshot_type="best_bid_ask_tick",
        observed_at=datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
        best_bid=1.0864,
        best_ask=1.0866,
        spread_points=2.0,
        tradable=True,
    )
    print(f"freshness_valid={freshness.is_valid}")
    print(f"shortest_ttl_seconds={freshness.shortest_ttl_seconds}")
    print(f"account_snapshot_id={account_snapshot.snapshot_id}")
    print(f"portfolio_snapshot_id={portfolio_snapshot.snapshot_id}")
    print(f"market_snapshot_id={market_snapshot.snapshot_id}")


def example_02_risk_engine_core(
    *,
    risk_repository: RiskRepository,
    workflow_repository: WorkflowRepository,
    proposal_repository: ProposalRepository,
) -> tuple[TradeProposal, object, object, str]:
    print_example_header("Example 02: Risk Engine Core")
    workflow_id = generate_prefixed_id("wf")
    proposal = build_trade_proposal(workflow_id=workflow_id)
    policy_bundle = build_policy_bundle()
    compliance_profile = build_compliance_profile()
    observed_at = datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC)

    account_snapshot = AccountSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("acct"),
        account_id="paper-account-01",
        observed_at=observed_at,
        balance=100000.0,
        equity=100500.0,
        free_margin=95000.0,
        margin_used=5500.0,
        currency="USD",
    )
    portfolio_snapshot = PortfolioSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("port"),
        portfolio_id="portfolio-01",
        observed_at=observed_at,
        open_position_count=3,
        gross_exposure=45000.0,
        net_exposure=15000.0,
        symbols=("EURUSD", "GBPUSD", "USDJPY"),
    )
    market_snapshot = MarketSnapshot.from_policy(
        snapshot_id=generate_prefixed_id("mkt"),
        symbol="EURUSD",
        snapshot_type="best_bid_ask_tick",
        observed_at=observed_at,
        best_bid=1.0864,
        best_ask=1.0866,
        spread_points=2.0,
        tradable=True,
    )
    risk_request = assemble_risk_assessment_request(
        proposal=proposal,
        account_snapshot=account_snapshot,
        portfolio_snapshot=portfolio_snapshot,
        market_snapshot=market_snapshot,
        context=RiskRequestAssemblyContext(
            workflow_id=workflow_id,
            correlation_id=generate_prefixed_id("corr"),
            causation_id=generate_prefixed_id("cause"),
            originator=build_originator(),
            environment="test",
            operating_mode="MODE-002",
            compliance_profile=compliance_profile,
            policy_bundle=policy_bundle,
            strategy_lifecycle_state="paper",
            current_kill_switch_state="armed",
            account_scope_id=account_snapshot.account_id,
            strategy_scope_id="strategy-eurusd-01",
        ),
    )

    positions = (
        PositionExposure("EURUSD", "USD", "trend", 20000.0, "buy"),
        PositionExposure("GBPUSD", "USD", "trend", 15000.0, "sell"),
        PositionExposure("USDJPY", "JPY", "mean_reversion", 10000.0, "buy"),
    )
    exposure_summary = calculate_exposure_summary(positions)
    symbol_concentration = calculate_symbol_concentration(positions, threshold=0.45)
    currency_concentration = calculate_currency_concentration(positions, threshold=0.70)
    family_concentration = calculate_strategy_family_concentration(positions, threshold=0.60)
    margin_utilization = calculate_margin_utilization(
        balance=account_snapshot.balance,
        equity=account_snapshot.equity,
        free_margin=account_snapshot.free_margin,
        margin_used=account_snapshot.margin_used,
    )
    sizing = calculate_volatility_adjusted_size(
        base_size=1.0,
        reference_volatility=0.010,
        observed_volatility=0.015,
    )
    drawdown = calculate_drawdown_state(peak_equity=110000.0, current_equity=100500.0)
    correlation = calculate_correlation_concentration(
        (
            CorrelationPair("EURUSD", "GBPUSD", 0.44, 0.33, 0.88),
            CorrelationPair("EURUSD", "USDJPY", 0.44, 0.22, -0.30),
        ),
        threshold=0.10,
    )
    regime = evaluate_regime_restriction(current_regime="trend", allowed_regimes=("trend", "calm"))
    session = evaluate_session_restrictions(
        current_time=datetime(2026, 4, 9, 11, 0, tzinfo=UTC),
        allowed_window=("09:00", "17:00"),
        blackout_windows=(("12:30", "13:00"),),
    )
    spread = evaluate_spread_slippage_precheck(
        spread_points=2.0,
        max_spread_points=3.0,
        expected_slippage_points=1.5,
        max_slippage_points=3.0,
    )
    mode_check = evaluate_operating_mode_compatibility(
        workflow_operating_mode="MODE-002",
        allowed_operating_modes=("MODE-001", "MODE-002"),
    )
    compliance_check = evaluate_compliance_profile_compatibility(
        active_compliance_profile_id=compliance_profile.compliance_profile_id,
        allowed_compliance_profile_ids=("uae-enterprise-v1",),
    )

    print(f"risk_request_id={risk_request.payload.risk_request_id}")
    print(f"gross_exposure={exposure_summary.gross_exposure} net_exposure={exposure_summary.net_exposure}")
    print(f"symbol_concentration_breaches={symbol_concentration.breached_keys}")
    print(f"currency_concentration_breaches={currency_concentration.breached_keys}")
    print(f"strategy_family_breaches={family_concentration.breached_keys}")
    print(f"margin_utilization={margin_utilization.utilization_ratio:.4f}")
    print(f"adjusted_size={sizing.adjusted_size:.4f}")
    print(f"drawdown_band={drawdown.band}")
    print(f"correlation_breaches={correlation.breached_pairs}")
    print(
        f"restrictions_allowed={all((regime.allowed, session.allowed, spread.allowed, mode_check.allowed, compliance_check.allowed))}"
    )
    composed = compose_risk_decision(
        checks=(
            evaluate_regime_restriction(current_regime="trend", allowed_regimes=("trend",)),
            evaluate_operating_mode_compatibility(
                workflow_operating_mode="MODE-002",
                allowed_operating_modes=("MODE-002",),
            ),
        ),
        limit_constraints=(
            LimitConstraint(
                constraint_type="max_position_size",
                value={"units": 7500},
            ),
        ),
    )
    packed = pack_risk_decision_rationale_and_provenance(
        composed=composed,
        context=RiskDecisionEnvelopeContext(
            workflow_id=risk_request.workflow_id,
            correlation_id=risk_request.correlation_id,
            causation_id=risk_request.causation_id,
            originator=build_originator(),
            environment="test",
            operating_mode="MODE-002",
            compliance_profile_id="uae-enterprise-v1",
        ),
        provenance=RiskDecisionProvenance(
            proposal_id=proposal.payload.proposal_id,
            rationale_text="All deterministic checks passed; constrain size for concentration control.",
            risk_metrics_snapshot={
                "gross_exposure": 45000.0,
                "margin_utilization": 0.0547,
            },
            freshness_expiry=datetime(2026, 4, 9, 9, 0, 30, tzinfo=UTC),
            policy_version="policy-risk-2026-04-09",
            formula_version="risk-formula-v1",
            provenance_bundle_id=generate_prefixed_id("prov"),
            account_snapshot_ref=risk_request.payload.account_snapshot_ref,
            market_snapshot_ref=risk_request.payload.market_snapshot_ref,
            approval_token=generate_prefixed_id("approval"),
        ),
    )
    workflow_repository.create_workflow(
        workflow_id=risk_request.workflow_id,
        workflow_type="live_execution",
        environment="test",
        operating_mode="MODE-002",
        state="CREATED",
        objective="Phase 2 deterministic safety example",
        scope_json=json.dumps({"symbol": proposal.payload.symbol}, sort_keys=True),
        initiator_type="service",
        initiator_id="phase2-example",
        timeout_policy_json=json.dumps({"seconds": 60}, sort_keys=True),
        stop_conditions_json=json.dumps(["done"]),
    )
    seed_trade_hypothesis(proposal=proposal)
    proposal_repository.create_proposal(
        proposal_id=proposal.payload.proposal_id,
        workflow_id=proposal.workflow_id,
        hypothesis_id=proposal.payload.source_hypothesis_id,
        state="READY_FOR_RISK",
        symbol=proposal.payload.symbol,
        direction=proposal.payload.direction,
        candidate_price_logic_json=json.dumps(proposal.payload.candidate_price_logic, sort_keys=True),
        proposed_size_json=json.dumps(proposal.payload.proposed_size, sort_keys=True),
        operating_envelope_json=json.dumps(proposal.payload.operating_envelope, sort_keys=True),
        session_restrictions_json=json.dumps(proposal.payload.session_restrictions, sort_keys=True),
        expiry_at=proposal.payload.expiry_at.isoformat().replace("+00:00", "Z"),
        transformation_version=proposal.payload.transformation_version,
        readiness_state=proposal.payload.readiness_state,
    )
    risk_repository.create_request(
        risk_request_id=risk_request.payload.risk_request_id,
        workflow_id=risk_request.workflow_id,
        proposal_id=risk_request.payload.proposal_id,
        action_type=risk_request.payload.action_type,
        account_snapshot_ref=risk_request.payload.account_snapshot_ref,
        portfolio_snapshot_ref=risk_request.payload.portfolio_snapshot_ref,
        market_snapshot_ref=risk_request.payload.market_snapshot_ref,
        requested_freshness_json=json.dumps(
            risk_request.payload.requested_freshness_classes.model_dump(),
            sort_keys=True,
        ),
        strategy_lifecycle_state=risk_request.payload.strategy_lifecycle_state,
        active_policy_bundle_json=json.dumps(
            risk_request.payload.active_policy_bundle.model_dump(),
            sort_keys=True,
        ),
        compliance_profile_id=risk_request.payload.compliance_profile_id,
        current_kill_switch_state=risk_request.payload.current_kill_switch_state,
    )
    persistence = RiskDecisionPersistenceService(DB_PATH)
    decision_record, constraints = persistence.save(
        risk_request_id=risk_request.payload.risk_request_id,
        packed=packed,
    )
    valid_expiry = enforce_risk_decision_expiry(
        freshness_expiry=packed.contract.payload.freshness_expiry,
        clock=FixedClock(datetime(2026, 4, 9, 9, 0, 5, tzinfo=UTC)),
    )
    changed_proposal = build_trade_proposal(
        workflow_id=proposal.workflow_id,
        direction=proposal.payload.direction,
        size_units=12000,
    )
    change_validity = invalidate_for_material_proposal_change(
        approved_proposal=proposal,
        current_proposal=changed_proposal,
    )
    print(f"risk_decision_id={decision_record.risk_decision_id}")
    print(f"decision={decision_record.decision}")
    print(f"persisted_constraints={len(constraints)}")
    print(f"expiry_valid={valid_expiry.valid}")
    print(f"material_change_valid={change_validity.valid}")
    return proposal, risk_request, packed.contract, workflow_id


def example_03_kill_switch(workflow_id: str) -> None:
    print_example_header("Example 03: Kill Switch")
    service = KillSwitchService()
    soft = service.apply_action(current_state=KillSwitchState.ARMED, action="soft_trigger")
    hard = service.apply_action(current_state=soft.state, action="hard_trigger")
    recovery_pending = service.apply_action(
        current_state=hard.state,
        action="request_recovery",
        authorization="operator",
    )
    recovery_approved = service.apply_action(
        current_state=recovery_pending.state,
        action="approve_recovery",
        authorization="risk_manager",
    )
    rearmed = service.apply_action(
        current_state=recovery_approved.state,
        action="rearm",
    )
    block = evaluate_new_entry_block(hard.state)
    dual_auth = require_hard_trigger_recovery_dual_auth(
        (
            RecoveryApproval("risk_manager", "risk:alice"),
            RecoveryApproval("compliance", "compliance:bob"),
        )
    )
    audit = KillSwitchAuditService(DB_PATH)
    event = audit.log_event(
        previous_state=KillSwitchState.HARD_TRIGGERED,
        new_state=KillSwitchState.RECOVERY_PENDING,
        trigger_type="manual",
        reason_code="review_recovery",
        actor_type="operator",
        actor_id="ops:example",
        workflow_id=workflow_id,
        metadata={"dual_auth_required": True},
    )
    print(f"hard_state={hard.state.value}")
    print(f"blocked_new_entries={block.blocked}")
    print(f"dual_auth_ready={dual_auth}")
    print(f"rearmed_state={rearmed.state.value}")
    print(f"kill_switch_event_id={event.kill_event_id}")


def example_04_execution_readiness(proposal: TradeProposal, risk_decision) -> ExecutionIntent:
    print_example_header("Example 04: Execution Readiness Validator")
    metadata = build_metadata_entry(observed_at=datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC))
    checks = (
        validate_market_open(metadata),
        validate_symbol_tradability(metadata),
        validate_price_freshness(
            metadata,
            clock=FixedClock(datetime(2026, 4, 9, 9, 0, 1, tzinfo=UTC)),
        ),
        validate_stop_and_freeze_levels(
            metadata,
            stop_distance_points=8,
            modify_distance_points=5,
        ),
        validate_fill_mode_compatibility(metadata, requested_fill_mode="IOC"),
        validate_terminal_connectivity(connected=True),
        validate_risk_decision_for_execution(
            risk_decision,
            approved_proposal=proposal,
            current_proposal=proposal,
            clock=FixedClock(datetime(2026, 4, 9, 9, 0, 10, tzinfo=UTC)),
        ),
    )
    aggregate = aggregate_readiness_results(checks)
    execution_intent = ExecutionIntent(
        workflow_id=proposal.workflow_id,
        correlation_id=generate_prefixed_id("corr"),
        causation_id=generate_prefixed_id("cause"),
        originator=build_originator(),
        environment="test",
        operating_mode="MODE-002",
        compliance_profile_id="uae-enterprise-v1",
        payload=ExecutionIntentPayload(
            execution_intent_id=generate_prefixed_id("exec"),
            proposal_id=proposal.payload.proposal_id,
            risk_decision_id=risk_decision.payload.risk_decision_id,
            broker_action_type="submit_order",
            symbol=proposal.payload.symbol,
            side=proposal.payload.direction,
            size={"units": 7500},
            order_type="market",
            price_params={"reference_price": 1.0866},
            sl_tp_params={"stop_loss_points": 8, "take_profit_points": 20},
            idempotency_key=generate_prefixed_id("idem"),
            expiry_time=datetime(2026, 4, 9, 9, 1, 0, tzinfo=UTC),
            pre_send_validation_snapshot_ref=metadata.snapshot_id,
        ),
    )
    print(f"readiness_allowed={aggregate.allowed}")
    print(f"readiness_reason_codes={aggregate.reason_codes}")
    print(f"execution_intent_id={execution_intent.payload.execution_intent_id}")
    return execution_intent


def example_05_mt5_mcp_boundary(execution_intent: ExecutionIntent, *, engine: Engine) -> None:
    print_example_header("Example 05: MT5 MCP Boundary")
    gateway = SimulatorMT5GatewayAdapter(engine)
    read_tools = MT5ReadOnlyTools(gateway)
    write_tools = MT5MutatingTools(gateway)
    authorizer = MT5ToolAuthorizer()
    server = create_mt5_mcp_server().startup()
    authorizer.authorize(tool_name="get_account_info", role="viewer")
    authorizer.authorize(tool_name="place_order", role="trader")
    reject_stale_execution_inputs(
        observed_at=datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
        max_age_seconds=2,
        clock=FixedClock(datetime(2026, 4, 9, 9, 0, 1, tzinfo=UTC)),
    )
    account_info = read_tools.get_account_info()
    symbol_info = read_tools.get_symbol_info("EURUSD")
    ticks = read_tools.get_ticks("EURUSD", count=3)
    raw_response = write_tools.place_order(
        {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": execution_intent.payload.symbol,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": float(symbol_info["ask"]) + (25 * float(symbol_info["point"]) * 10),
            "volume": 0.01,
            "comment": "client-order-new-001",
        }
    )
    normalized = normalize_broker_response(raw_response)
    print(f"mt5_server_started={server.started}")
    print(f"mt5_tool_count={len(server.list_tools())}")
    print(f"account_login={account_info['login']}")
    print(f"symbol_info_name={symbol_info['symbol']}")
    print(f"open_positions={len(read_tools.list_positions())}")
    print(f"open_orders={len(read_tools.list_orders())}")
    print(f"tick_count={ticks['count']}")
    print(f"normalized_broker_status={normalized['status']}")


def build_metadata_entry(*, observed_at: datetime) -> SymbolMetadataCacheEntry:
    return SymbolMetadataCacheEntry(
        snapshot_id=generate_prefixed_id("sym"),
        symbol="EURUSD",
        observed_at=observed_at,
        market_open=True,
        tradable=True,
        supported_fill_modes=("IOC", "FOK"),
        stop_level_points=5,
        freeze_level_points=3,
        tick_size=0.00001,
        point_value=0.0001,
        contract_size=100000.0,
        max_age_seconds=2,
    )


def example_07_end_to_end_deterministic_safety_core() -> None:
    print_example_header("Example 07: End-to-End Deterministic Safety Core")
    sim_engine, sim_trade = initialize_sim_engine()
    try:
        seed_simulator_broker_state(engine=sim_engine, trade=sim_trade)
        risk_repo, execution_repo, workflow_repo, proposal_repo = bootstrap_database()
        proposal_contract, risk_request_contract, risk_decision_contract, workflow_id = example_02_risk_engine_core(
            risk_repository=risk_repo,
            workflow_repository=workflow_repo,
            proposal_repository=proposal_repo,
        )
        example_03_kill_switch(workflow_id)
        execution_intent_contract = example_04_execution_readiness(
            proposal_contract,
            risk_decision_contract,
        )
        example_05_mt5_mcp_boundary(execution_intent_contract, engine=sim_engine)
        example_06_reconciliation_flow(
            execution_repository=execution_repo,
            workflow_repository=workflow_repo,
            execution_intent=execution_intent_contract,
            risk_decision_id=risk_decision_contract.payload.risk_decision_id,
            engine=sim_engine,
        )
    finally:
        sim_engine.client.shutdown()


def example_06_reconciliation_flow(
    *,
    execution_repository: ExecutionRepository,
    workflow_repository: WorkflowRepository,
    execution_intent: ExecutionIntent,
    risk_decision_id: str,
    engine: Engine,
) -> None:
    print_example_header("Example 06: Reconciliation and Retry Guard")
    execution_repository.create_intent(
        execution_intent_id=generate_prefixed_id("exec"),
        workflow_id=execution_intent.workflow_id,
        proposal_id=execution_intent.payload.proposal_id,
        risk_decision_id=risk_decision_id,
        action_type=execution_intent.payload.broker_action_type,
        symbol=execution_intent.payload.symbol,
        side=execution_intent.payload.side,
        order_type=execution_intent.payload.order_type,
        size_json=json.dumps(execution_intent.payload.size, sort_keys=True),
        price_params_json=json.dumps(execution_intent.payload.price_params, sort_keys=True),
        sl_tp_params_json=json.dumps(execution_intent.payload.sl_tp_params, sort_keys=True),
        idempotency_key=generate_prefixed_id("idem"),
        client_order_id="client-order-inflight-001",
        status=ProposalState.SENT.value,
        expiry_at=execution_intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=execution_intent.payload.pre_send_validation_snapshot_ref,
    )
    intent_record = execution_repository.create_intent(
        execution_intent_id=execution_intent.payload.execution_intent_id,
        workflow_id=execution_intent.workflow_id,
        proposal_id=execution_intent.payload.proposal_id,
        risk_decision_id=risk_decision_id,
        action_type=execution_intent.payload.broker_action_type,
        symbol=execution_intent.payload.symbol,
        side=execution_intent.payload.side,
        order_type=execution_intent.payload.order_type,
        size_json=json.dumps(execution_intent.payload.size, sort_keys=True),
        price_params_json=json.dumps(execution_intent.payload.price_params, sort_keys=True),
        sl_tp_params_json=json.dumps(execution_intent.payload.sl_tp_params, sort_keys=True),
        idempotency_key=execution_intent.payload.idempotency_key,
        client_order_id="client-order-001",
        status=ProposalState.EXECUTION_FAILED.value,
        expiry_at=execution_intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
        pre_send_validation_snapshot_ref=execution_intent.payload.pre_send_validation_snapshot_ref,
    )
    receipt = execution_repository.add_receipt(
        receipt_id=generate_prefixed_id("rcpt"),
        execution_intent_id=intent_record.execution_intent_id,
        broker="mt5",
        broker_order_id="ord-local-001",
        broker_deal_id="deal-local-001",
        receipt_status="filled",
        requested_price=1.0866,
        fill_price=1.0867,
        fill_qty=7500,
        spread_points=2.0,
        slippage_points=1.0,
        slippage_bps=0.9,
        broker_message="filled locally",
        broker_retcode=10009,
        authoritative_state=json.dumps({"status": "FILLED"}, sort_keys=True),
    )
    loader = ReconciliationStartupLoader(execution_repository)
    in_flight = loader.load_in_flight_execution_intents()
    read_tools = MT5ReadOnlyTools(SimulatorMT5GatewayAdapter(engine))
    broker_truth = BrokerTruthFetcher(read_tools).fetch_for_client_order_id("client-order-001")
    local_truth = build_local_execution_truth(intent_record, receipt)
    comparison = compare_execution_truth(local_truth=local_truth, broker_truth=broker_truth)
    retry_guard = evaluate_retry_guard(comparison)
    incident = ReconciliationIncidentService(DB_PATH).raise_for_unresolved_divergence(
        execution_intent_id=intent_record.execution_intent_id,
        comparison=comparison,
    )
    run = ReconciliationPersistenceService(DB_PATH).save(
        execution_intent_id=intent_record.execution_intent_id,
        run_reason="startup_scan",
        comparison=comparison,
        incident_id=incident.incident_id,
    )
    print(f"in_flight_count={len(in_flight)}")
    print(f"reconciliation_result={comparison.result_state.value}")
    print(f"retry_allowed={retry_guard.allow_retry}")
    print(f"incident_id={incident.incident_id}")
    print(f"reconciliation_run_id={run.reconciliation_run_id}")


if __name__ == "__main__":
    reset_example_state()
    example_01_freshness_and_snapshots()
    sim_engine, sim_trade = initialize_sim_engine()
    try:
        seed_simulator_broker_state(engine=sim_engine, trade=sim_trade)
        risk_repo, _, workflow_repo, proposal_repo = bootstrap_database()
        proposal_contract, _, risk_decision_contract, workflow_id = example_02_risk_engine_core(
            risk_repository=risk_repo,
            workflow_repository=workflow_repo,
            proposal_repository=proposal_repo,
        )
        example_03_kill_switch(workflow_id)
        example_04_execution_readiness(proposal_contract, risk_decision_contract)
    finally:
        sim_engine.client.shutdown()
    example_07_end_to_end_deterministic_safety_core()
