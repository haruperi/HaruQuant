from agents.portfolio.shared.contracts import AllocationProposal, LifecycleTransitionRequest, StrategyLifecycleState
from services.portfolio import AllocationService, LifecycleService, OrderRouter, PaperBroker, PortfolioKillSwitch, ReportingService


def test_all_contracts_and_services_smoke():
    broker = PaperBroker()
    receipt = broker.place_order(symbol="EURUSD", side="buy", order_type="market", size=0.01, price=1.1)
    assert receipt["status"] == "filled"

    allocation = AllocationService().propose(
        AllocationProposal(
            available_capital=100000.0,
            proposed_allocations={"s1": 10000.0},
            lifecycle_states={"s1": "paper_live"},
            risk_constraints={"max_strategy_allocation": 20000.0},
        )
    )
    assert allocation.status == "accepted"

    lifecycle = LifecycleService().transition(
        LifecycleTransitionRequest(
            strategy_id="s1",
            old_state=StrategyLifecycleState.PAPER_CANDIDATE,
            new_state=StrategyLifecycleState.PAPER_LIVE,
            evidence_refs=["strategy_review"],
        )
    )
    assert lifecycle.status == "accepted"

    route = OrderRouter().route_order(order={"strategy_id": "s1", "symbol": "EURUSD", "side": "buy"}, approval_token=None, live_config={}, broker_status={}, kill_switch_status="healthy")
    assert route["status"] == "rejected"

    kill_switch = PortfolioKillSwitch().evaluate({"broker_heartbeat": "healthy"})
    assert kill_switch["state"] == "healthy"

    report = ReportingService().generate(report_type="daily", data={"portfolio_pnl": 1.0, "drawdown": 0.0, "trade_count": 1})
    assert report.status == "complete"
