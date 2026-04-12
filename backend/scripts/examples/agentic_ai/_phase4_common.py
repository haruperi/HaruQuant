"""Shared helpers for Phase 4 live-control-plane examples."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.core.settings import load_runtime_settings_from_mapping  # noqa: E402
from apps.mt5 import get_mt5_api  # noqa: E402
from apps.trading import Engine  # noqa: E402
from backend.contracts.common import Originator  # noqa: E402
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
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload  # noqa: E402
from backend.db import (  # noqa: E402
    ExecutionRepository,
    ResearchAuditRepository,
    WorkflowRepository,
    apply_pending_migrations,
)


UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).resolve().parent
TMP_DIR = EXAMPLE_DIR / "_tmp"
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


def build_db_path(filename: str) -> Path:
    return TMP_DIR / filename


def build_settings(database_path: Path) -> object:
    return load_runtime_settings_from_mapping(
        {
            "app_name": "haruquant-phase4-example",
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{database_path.as_posix()}",
        }
    )


def bootstrap_database(
    database_path: Path,
) -> tuple[ExecutionRepository, WorkflowRepository, ResearchAuditRepository]:
    applied = apply_pending_migrations(database_path, MIGRATIONS_DIR)
    print(f"Applied migrations on fresh database: {len(applied)}")
    return (
        ExecutionRepository(database_path),
        WorkflowRepository(database_path),
        ResearchAuditRepository(database_path),
    )


def initialize_sim_engine(*, symbol: str = "EURUSD") -> Engine:
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
    return engine


class SimulatorExecutionGateway:
    def __init__(self, engine: Engine) -> None:
        self._api = engine.api

    def _lot_volume(self, request: dict[str, object]) -> float:
        size = request.get("size", {})
        if isinstance(size, dict):
            units = float(size.get("units", 0.0) or 0.0)
        else:
            units = 0.0
        return max(0.01, round(units / 100000.0, 2))

    def place_order(self, request: dict[str, object]) -> object:
        symbol = str(request["symbol"])
        side = str(request["side"]).lower()
        symbol_info = self._api.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"simulator symbol metadata unavailable for {symbol}")
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        price = float(symbol_info.ask if side == "buy" else symbol_info.bid)
        return self._api.order_send(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "type": order_type,
                "volume": self._lot_volume(request),
                "price": price,
                "comment": str(request["idempotency_key"]),
            }
        )

    def modify_position(self, request: dict[str, object]) -> object:
        return self._api.order_send(request)

    def partial_close(self, request: dict[str, object]) -> object:
        return self._api.order_send(request)

    def full_close(self, request: dict[str, object]) -> object:
        return self._api.order_send(request)

    def cancel_order(self, request: dict[str, object]) -> object:
        return self._api.order_send(request)


def build_hypothesis(*, required_validation_data: tuple[str, ...] = ()) -> TradeHypothesis:
    return TradeHypothesis(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_hyp",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-003",
        compliance_profile_id="cmp_001",
        payload=TradeHypothesisPayload(
            hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            thesis="Breakout continuation through London session.",
            entry_rationale="Momentum retest remains intact with stable spread.",
            invalidation_rationale="Breakout fails if swing low breaks.",
            stop_loss_logic={"type": "swing_low", "price": 1.0827},
            take_profit_logic={"type": "rr_multiple", "value": 2},
            holding_horizon="intraday",
            confidence=0.81,
            calibration_note="Calibrated against paper distribution.",
            evidence=[
                EvidenceItem(
                    source_type="observation",
                    ref_id="obs_001",
                    summary="Spread and regime conditions are supportive.",
                    freshness_class="fresh",
                )
            ],
            required_validation_data=list(required_validation_data),
            strategy_family="fx_momentum",
            feature_version="v1",
            strategy_code_hash="hash_001",
        ),
    )


def build_proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_prop",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-003",
        compliance_profile_id="cmp_001",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={
                "entry_rationale": "breakout retest",
                "entry_price": 1.0842,
                "stop_loss_logic": {"type": "swing_low", "price": 1.0827},
                "take_profit_logic": {"type": "rr_multiple", "value": 2},
            },
            proposed_size={"units": 1000},
            operating_envelope={"max_slippage_bps": 5},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def build_decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_risk",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="paper",
        operating_mode="MODE-003",
        compliance_profile_id="cmp_001",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="prop_001",
            decision="APPROVE",
            reasons=["within paper limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.2},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )


def seed_phase4_workflow_graph(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO core_workflows (
                workflow_id, workflow_type, environment, operating_mode, state,
                objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf_001",
                "trade_review",
                "paper",
                "MODE-003",
                "CREATED",
                "Run a supervised paper control-plane path",
                "{}",
                "user",
                "operator_001",
                "{}",
                "[]",
            ),
        )
        connection.execute(
            """
            INSERT INTO core_trade_hypotheses (
                hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale,
                stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note,
                strategy_family, feature_version, strategy_code_hash, evidence_bundle_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hyp_001",
                "wf_001",
                "strat_001",
                "EURUSD",
                "buy",
                "Breakout continuation",
                "Retest holds",
                "Breakout fails",
                '{"type":"swing_low"}',
                '{"type":"rr_multiple","value":2}',
                "intraday",
                0.81,
                "calibrated",
                "fx_momentum",
                "v1",
                "hash_001",
                None,
            ),
        )
        connection.execute(
            """
            INSERT INTO core_trade_proposals (
                proposal_id, workflow_id, hypothesis_id, state, symbol, direction,
                candidate_price_logic_json, proposed_size_json, operating_envelope_json,
                session_restrictions_json, expiry_at, transformation_version, readiness_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "prop_001",
                "wf_001",
                "hyp_001",
                "READY_FOR_RISK",
                "EURUSD",
                "buy",
                '{"entry_price":1.0842}',
                '{"units":1000}',
                '{"max_slippage_bps":5}',
                '{"session":"london"}',
                "2026-04-09T10:20:00Z",
                "proposal_v1",
                "ready_for_risk",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_assessment_requests (
                risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref,
                market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json,
                compliance_profile_id, current_kill_switch_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_req_001",
                "wf_001",
                "prop_001",
                "new_entry",
                "acct_001",
                "port_001",
                "mkt_001",
                '{"market":"fresh"}',
                "PAPER_APPROVED",
                '{"policy_version":"pol_001","formula_version":"formula_v1"}',
                "cmp_001",
                "ARMED",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_decisions (
                risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text,
                risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id,
                approval_token, freshness_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_001",
                "risk_req_001",
                "prop_001",
                "wf_001",
                "APPROVE",
                "Within bounded paper envelope",
                '{"var_95":1.2}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_001",
                "approval_001",
                "fresh",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def seed_timeout_workflow(database_path: Path) -> str:
    workflow_id = "wf_timeout_001"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO core_workflows (
                workflow_id, workflow_type, environment, operating_mode, state,
                objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                "trade_review",
                "paper",
                "MODE-003",
                "REASONING",
                "Timeout monitoring example",
                "{}",
                "service",
                "monitoring:example",
                json.dumps({"timeout_seconds": 60}, sort_keys=True),
                "[]",
            ),
        )
        connection.execute(
            "UPDATE core_workflows SET updated_at = ? WHERE workflow_id = ?",
            ("2026-04-09T09:58:00Z", workflow_id),
        )
        connection.commit()
    finally:
        connection.close()
    return workflow_id


def dashboard_route_inventory() -> tuple[str, ...]:
    operator_pages_root = Path(PROJECT_ROOT) / "ui" / "src" / "app" / "(dashboard)" / "operator"
    routes: list[str] = []
    for page_file in sorted(operator_pages_root.rglob("page.tsx")):
        relative = page_file.relative_to(operator_pages_root).parent
        route = "/operator" if str(relative) == "." else f"/operator/{str(relative).replace(os.sep, '/')}"
        routes.append(route)
    return tuple(routes)


def dashboard_component_inventory() -> tuple[str, ...]:
    components_root = Path(PROJECT_ROOT) / "ui" / "src" / "components" / "operator"
    return tuple(sorted(path.name for path in components_root.glob("*.tsx")))
