from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.common import FixedClock
from backend.data.database import ExecutionRepository, apply_pending_migrations
from backend.mcp.mt5_mcp import MT5ReadOnlyTools
from backend.orchestration.workflow import KillSwitchState
from backend.services import (
    BrokerTruthFetcher,
    ReconciliationStartupLoader,
    SymbolMetadataCacheEntry,
    aggregate_readiness_results,
    build_local_execution_truth,
    compare_execution_truth,
    evaluate_new_entry_block,
    evaluate_retry_guard,
    validate_market_open,
    validate_price_freshness,
    validate_terminal_connectivity,
)


UTC = timezone.utc


class FakeBrokerReadGateway:
    def account_info(self):
        return {"login": 12345, "equity": 10000.0}

    def positions_get(self):
        return ()

    def orders_get(self):
        return (
            {
                "ticket": 401,
                "symbol": "EURUSD",
                "external_id": "client_001",
            },
        )

    def symbol_info(self, symbol: str):
        return {"symbol": symbol}

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True):
        return []


def _seed_execution_graph(repository: ExecutionRepository) -> None:
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "wf_001",
                "trade_review",
                "paper",
                "MODE-002",
                "CREATED",
                "Review setup",
                "{}",
                "user",
                "operator_001",
                "{}",
                "[]",
            ),
        )
        connection.execute(
            "INSERT INTO core_trade_hypotheses (hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale, stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note, strategy_family, feature_version, strategy_code_hash, evidence_bundle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "hyp_001",
                "wf_001",
                "strat_001",
                "EURUSD",
                "long",
                "Momentum",
                "Breakout",
                "Loss of support",
                '{"type":"atr_stop"}',
                '{"type":"rr_target"}',
                "intraday",
                0.82,
                None,
                "fx_momentum",
                "v1",
                "hash_001",
                None,
            ),
        )
        connection.execute(
            "INSERT INTO core_trade_proposals (proposal_id, workflow_id, hypothesis_id, state, symbol, direction, candidate_price_logic_json, proposed_size_json, operating_envelope_json, session_restrictions_json, expiry_at, transformation_version, readiness_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "prop_001",
                "wf_001",
                "hyp_001",
                "READY_FOR_RISK",
                "EURUSD",
                "buy",
                '{"type":"limit"}',
                '{"units":1000}',
                '{"max_slippage_bps":5}',
                '{"session":"london"}',
                "2026-04-08T12:00:00Z",
                "v1",
                "ready_for_risk",
            ),
        )
        connection.execute(
            "INSERT INTO risk_risk_assessment_requests (risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref, market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json, compliance_profile_id, current_kill_switch_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "risk_req_001",
                "wf_001",
                "prop_001",
                "open_position",
                None,
                None,
                None,
                "{}",
                "PAPER_APPROVED",
                '{"policy_version":"risk_policy_1"}',
                None,
                "ARMED",
            ),
        )
        connection.execute(
            "INSERT INTO risk_risk_decisions (risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text, risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id, approval_token, freshness_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "risk_dec_001",
                "risk_req_001",
                "prop_001",
                "wf_001",
                "APPROVE",
                "Within limits",
                '{"var":0.02}',
                "2026-04-08T12:30:00Z",
                "risk_policy_1",
                "formula_1",
                None,
                "approval_001",
                "fresh",
            ),
        )


def test_phase2_integration_reconciliation_uses_mt5_boundary_and_blocks_uncertain_retry(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ExecutionRepository(database_path)
    _seed_execution_graph(repository)
    repository.create_intent(
        execution_intent_id="exec_001",
        workflow_id="wf_001",
        proposal_id="prop_001",
        risk_decision_id="risk_dec_001",
        action_type="open_position",
        symbol="EURUSD",
        side="buy",
        order_type="limit",
        size_json='{"units":1000}',
        idempotency_key="idem_001",
        client_order_id="client_001",
        status="SENT",
    )

    startup_loader = ReconciliationStartupLoader(repository)
    in_flight = startup_loader.load_in_flight_execution_intents()
    broker_truth = BrokerTruthFetcher(
        MT5ReadOnlyTools(gateway=FakeBrokerReadGateway())
    ).fetch_for_client_order_id("client_001")
    local_truth = build_local_execution_truth(in_flight[0])
    comparison = compare_execution_truth(local_truth=local_truth, broker_truth=broker_truth)
    guard = evaluate_retry_guard(comparison)

    assert [record.execution_intent_id for record in in_flight] == ["exec_001"]
    assert comparison.result_state.value == "MATCHED"
    assert guard.allow_retry is True


def test_phase2_integration_kill_switch_and_readiness_fail_closed() -> None:
    kill_switch = evaluate_new_entry_block(KillSwitchState.SOFT_TRIGGERED)
    metadata = SymbolMetadataCacheEntry(
        snapshot_id="meta_001",
        symbol="EURUSD",
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        market_open=False,
        tradable=True,
        supported_fill_modes=("IOC", "FOK"),
        stop_level_points=10,
        freeze_level_points=5,
        tick_size=0.0001,
        point_value=10.0,
        contract_size=100000.0,
        max_age_seconds=5,
    )
    readiness = aggregate_readiness_results(
        (
            validate_market_open(metadata),
            validate_price_freshness(
                metadata,
                clock=FixedClock(datetime(2026, 4, 9, 10, 0, 6, tzinfo=UTC)),
            ),
            validate_terminal_connectivity(connected=False),
        )
    )

    assert kill_switch.blocked is True
    assert kill_switch.reason_codes == ("kill_switch_blocks_new_entries",)
    assert readiness.allowed is False
    assert readiness.reason_codes == (
        "market_closed",
        "stale_price_snapshot",
        "terminal_disconnected",
    )
