from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.schemas import (
    AgentPlan,
    EvidenceRef,
    StrategySpec,
    TradeProposal,
)
from agents.schemas import ConversationPlan


def test_agent_plan_reuses_conversation_plan_with_governance_fields() -> None:
    assert AgentPlan is ConversationPlan

    plan = AgentPlan(
        conversation_plan_id="plan-1",
        user_goal="Create a EURUSD H1 strategy",
        response_mode="governed_artifact",
        task_class="strategy_creation",
        model_tier="standard",
        response_style="structured",
        domain_focus="forex",
        rationale="Strategy creation requires review and evidence.",
        intent="strategy_creation",
        requires_board_approval=True,
        requires_risk_governor=True,
        requires_audit_log=True,
        allowed_agents=["ceo", "planner", "strategy_creator"],
        blocked_agents=["live_execution"],
        expected_outputs=["StrategySpec", "StrategyReview"],
        evidence_requirements=["source_market_context"],
        failure_policy={"on_missing_symbol": "clarify"},
    )

    assert plan.requires_board_approval is True
    assert plan.requires_risk_governor is True
    assert plan.allowed_agents == ["ceo", "planner", "strategy_creator"]
    assert plan.blocked_agents == ["live_execution"]
    assert plan.expected_outputs == ["StrategySpec", "StrategyReview"]


def test_strategy_spec_requires_testable_logic() -> None:
    spec = StrategySpec(
        strategy_name="EURUSD H1 Mean Reversion",
        market="forex",
        symbol="EURUSD",
        timeframe="H1",
        entry_logic=["Buy when price closes below lower Bollinger Band."],
        exit_logic=["Exit at mid-band or stop loss."],
        position_sizing={"risk_per_trade": 0.005},
        data_requirements=["OHLCV", "spread"],
        risk_assumptions=["No trade without stop loss."],
        cost_assumptions=["Commission and spread included."],
        invalid_conditions=["High-impact news window."],
        test_plan=["Run walk-forward backtest."],
        evidence_refs=[EvidenceRef(evidence_id="ev-1", evidence_type="research_note")],
    )

    assert spec.strategy_name == "EURUSD H1 Mean Reversion"
    assert spec.symbol == "EURUSD"

    with pytest.raises(ValidationError):
        StrategySpec(
            strategy_name="Untestable",
            market="forex",
            symbol="EURUSD",
            timeframe="H1",
            entry_logic=[],
            exit_logic=["exit"],
            position_sizing="fixed",
        )


def test_trade_proposal_requires_risk_approval_by_default_and_forbids_extra_fields() -> None:
    proposal = TradeProposal(
        strategy_id="strategy-1",
        symbol="EURUSD",
        side="buy",
        entry_type="market",
        requested_size=0.1,
        stop_loss=1.07,
        take_profit=1.09,
        max_spread=1.5,
        max_slippage=0.5,
        expected_risk={"risk_pct": 0.5},
        portfolio_impact={"usd_exposure": 0.1},
    )

    assert proposal.requires_risk_approval is True

    with pytest.raises(ValidationError):
        TradeProposal(
            strategy_id="strategy-1",
            symbol="EURUSD",
            side="buy",
            entry_type="market",
            requested_size=0.1,
            unstructured_note="place it fast",
        )
