from __future__ import annotations

import pandas as pd

from services.risk import GovernanceEngine, PortfolioRiskEngine, PortfolioStateEngine, RiskLimits, RiskSnapshotEngine
from services.risk.limits import LimitEvent
from services.risk.limits import PolicyEngine


def _bars(periods: int = 80, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.0005) + (base % 5) * 0.0001
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0003,
            "High": close + 0.0006,
            "Low": close - 0.0006,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 for _ in range(periods)],
        },
        index=idx,
    )


def _build_state(limits: RiskLimits) -> object:
    return PortfolioStateEngine().build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8500.0,
            "margin_used": 1500.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.5, "type": "BUY", "strategy_id": "trend"},
            {"symbol": "GBPUSD", "volume": 0.3, "type": "BUY", "strategy_id": "trend"},
            {"symbol": "USDJPY", "volume": 0.2, "type": "SELL", "strategy_id": "mean_reversion"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(),
            "GBPUSD": _bars(),
            "USDJPY": _bars(),
        },
        limits=limits,
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-04T07:00:00",
    )


def test_policy_engine_returns_explainable_hard_limit_breach():
    engine = PolicyEngine()
    decision = engine.evaluate_pre_trade(
        equity=10000.0,
        current_var=200.0,
        new_var=1200.0,
        delta_var=1000.0,
        current_es=300.0,
        new_es=1600.0,
        delta_es=1300.0,
        current_margin_used=1000.0,
        new_margin_used=2000.0,
        rc_map_new={"EURUSD": 0.55, "GBPUSD": 0.45},
        currency_exposure=None,
        gross_portfolio_notional=100000.0,
        cluster_metrics={"FOREX": {"var": 1200.0, "es": 1600.0}},
        policy=RiskLimits(
            var_cap_frac=0.05,
            es_cap_frac=0.10,
            delta_var_cap_frac=0.03,
            delta_es_cap_frac=0.05,
            max_margin_used_frac=0.15,
            max_single_rc_frac=0.50,
            cluster_var_caps={"FOREX": 0.08},
            cluster_es_caps={"FOREX": 0.12},
        ),
    )

    assert decision.decision == "REJECT"
    assert decision.breaches
    assert any(event.rule_key == "portfolio_var_cap" for event in decision.breaches)
    assert any(event.rule_key == "margin_cap" for event in decision.breaches)
    assert decision.governance_state is not None
    assert decision.governance_state.status == "breach"


def test_policy_engine_records_stress_overrides():
    engine = PolicyEngine()
    effective, overrides = engine.effective_policy(
        RiskLimits(var_cap_frac=0.09, es_cap_frac=0.14, max_single_rc_frac=0.18),
        regime=type("StressRegime", (), {"name": "STRESS"})(),
    )

    assert effective.var_cap_frac == 0.07
    assert effective.es_cap_frac == 0.10
    assert effective.max_single_rc_frac == 0.12
    assert overrides
    assert any(override.field_name == "var_cap_frac" for override in overrides)


def test_snapshot_engine_includes_governance_state_and_events():
    state = _build_state(
        RiskLimits(
            var_cap_frac=0.01,
            es_cap_frac=0.02,
            warning_utilization_frac=0.50,
        )
    )

    snapshot = RiskSnapshotEngine().build_snapshot(state)

    assert snapshot.governance_state is not None
    assert snapshot.summary["compliance_state"] in {"warning", "breach", "compliant"}
    assert snapshot.summary["governance_decision"] in {"ACCEPT", "REJECT"}
    assert isinstance(snapshot.policy_events, list)


class _DummyRiskAdapter:
    def __init__(self, state):
        self._state = state

    def get_account_equity(self):
        return float(self._state.account.equity)

    def get_symbol_info(self, symbol):
        spec = self._state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        return abs(float(lots)) * 500.0

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        bars = self._state.markets[symbol].bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars


def test_governance_engine_rejects_breaching_candidate_trade():
    state = _build_state(
        RiskLimits(
            var_cap_frac=0.0001,
            es_cap_frac=0.0002,
            delta_var_cap_frac=0.0001,
            delta_es_cap_frac=0.0002,
            max_single_rc_frac=0.45,
            cluster_var_caps={"FOREX": 0.02},
            cluster_es_caps={"FOREX": 0.03},
        )
    )
    governance = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=_DummyRiskAdapter(state),
            timeframe="H1",
            start_pos=0,
            end_pos=80,
        ),
        limits=state.limits or RiskLimits(),
    )

    report = governance.evaluate_add_position(
        current_positions=state.position_map,
        candidate_symbol="EURUSD",
        candidate_lots=0.60,
        symbol_to_cluster=state.symbol_to_cluster,
    )

    assert report.decision == "REJECT"
    assert report.breaches


def test_governance_engine_does_not_force_accept_netting_candidate():
    state = _build_state(RiskLimits())
    governance = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=_DummyRiskAdapter(state),
            timeframe="H1",
            start_pos=0,
            end_pos=80,
        ),
        limits=state.limits or RiskLimits(),
    )

    breach_event = LimitEvent(
        event_type="hard_limit",
        rule_key="portfolio_var_cap",
        severity="breach",
        message="Projected VaR exceeds limit.",
        observed_value=2000.0,
        threshold_value=500.0,
    )

    def fake_evaluate_pre_trade(**kwargs):
        return type(
            "Decision",
            (),
            {
                "decision": "REJECT",
                "reason": "Projected VaR exceeds limit.",
                "breaches": [breach_event],
                "warnings": [],
                "overrides": [],
                "governance_state": None,
                "circuit_breaker_state": None,
                "policy_events": [],
            },
        )()

    governance.policy_engine.evaluate_pre_trade = fake_evaluate_pre_trade  # type: ignore[method-assign]

    report = governance.evaluate_add_position(
        current_positions={"EURUSD": 1.0},
        candidate_symbol="EURUSD",
        candidate_lots=-1.0,
    )

    assert report.decision == "REJECT"
    assert report.reason == "Projected VaR exceeds limit."
    assert report.breaches


def test_governance_engine_can_evaluate_candidate_from_canonical_state():
    state = _build_state(
        RiskLimits(
            var_cap_frac=0.0001,
            es_cap_frac=0.0002,
            delta_var_cap_frac=0.0001,
            delta_es_cap_frac=0.0002,
        )
    )
    governance = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=_DummyRiskAdapter(state),
            timeframe="H1",
            start_pos=0,
            end_pos=80,
        ),
        limits=state.limits or RiskLimits(),
    )

    report = governance.evaluate_add_position_from_state(
        current_state=state,
        candidate_symbol="EURUSD",
        candidate_lots=0.60,
    )

    assert report.decision == "REJECT"
    assert report.breaches
