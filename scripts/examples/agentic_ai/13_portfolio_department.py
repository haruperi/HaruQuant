from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents._shared import AgentRunContext
from agents.audit.audit_agent import AuditComplianceAgent
from agents.portfolio.allocation_optimizer_agent import AllocationOptimizerAgent
from agents.portfolio.cost_optimizer_agent import CostOptimizerAgent
from agents.portfolio.execution_readiness_agent import ExecutionReadinessAgent
from agents.portfolio.live_execution_agent import LiveExecutionAgent
from agents.portfolio.performance_reporter_agent import PerformanceReporterAgent
from agents.portfolio.portfolio_orchestrator_agent import PortfolioOrchestratorAgent
from agents.portfolio.strategy_lifecycle_agent import StrategyLifecycleAgent
from agents.portfolio.shared.contracts import AllocationProposal, LifecycleTransitionRequest, StrategyLifecycleState
from services.portfolio import AllocationService, LifecycleService, PaperBroker, PortfolioKillSwitch, ReportingService


def main() -> None:
    context = AgentRunContext(workflow_id="portfolio-example", task_id="portfolio-task", user_request="portfolio review")

    orchestrator = PortfolioOrchestratorAgent().run(
        context=context,
        task_input={"risk_governor_constraints": "ok", "audit_health_status": "healthy"},
    )
    lifecycle_agent = StrategyLifecycleAgent().run(
        context=context,
        task_input={"current_lifecycle_state": "paper_candidate", "requested_lifecycle_transition": "paper_live"},
    )
    allocation_agent = AllocationOptimizerAgent().run(
        context=context,
        task_input={"current_allocations": {"s1": 10000.0}, "risk_constraints": {"max_strategy_allocation": 20000.0}},
    )
    readiness = ExecutionReadinessAgent().run(
        context=context,
        task_input={"broker_health": "healthy", "audit_health_status": "healthy", "risk_governor_status": "healthy"},
    )
    report = PerformanceReporterAgent().run(
        context=context,
        task_input={"performance_snapshot": {"portfolio_pnl": 10.0}, "audit_health_status": "healthy"},
    )
    cost = CostOptimizerAgent().run(context=context, task_input={"cost_usage": [{"agent": "portfolio", "cost": 0.01}]})
    audit = AuditComplianceAgent().run(context=context, task_input={"records": [{"live_order": True, "order_id": "order-1"}]})

    broker = PaperBroker()
    paper_receipt = broker.place_order(symbol="EURUSD", side="buy", order_type="market", size=0.01, price=1.1)
    allocation = AllocationService().propose(
        AllocationProposal(
            available_capital=100000.0,
            current_allocations={"s1": 10000.0},
            proposed_allocations={"s1": 15000.0},
            lifecycle_states={"s1": "paper_live"},
            risk_constraints={"max_strategy_allocation": 20000.0},
        )
    )
    lifecycle = LifecycleService().transition(
        LifecycleTransitionRequest(
            strategy_id="s1",
            old_state=StrategyLifecycleState.PAPER_CANDIDATE,
            new_state=StrategyLifecycleState.PAPER_LIVE,
            evidence_refs=["strategy_review"],
        )
    )
    daily_report = ReportingService().generate(report_type="daily", data={"portfolio_pnl": 12.5, "drawdown": 0.01, "trade_count": 1})
    kill_switch = PortfolioKillSwitch().evaluate({"broker_heartbeat": "healthy", "audit_logging_available": True})
    live_block = LiveExecutionAgent().run(context=context, task_input={"live_mode_enabled": False, "strategy_state": "paper"})

    print(f"Orchestrator status: {orchestrator.status}")
    print(f"Lifecycle agent status: {lifecycle_agent.status}")
    print(f"Allocation agent status: {allocation_agent.status}")
    print(f"Readiness status: {readiness.status}")
    print(f"Performance report agent status: {report.status}")
    print(f"Cost agent status: {cost.status}")
    print(f"Audit status: {audit.status}")
    print(f"Paper receipt status: {paper_receipt['status']}")
    print(f"Allocation service status: {allocation.status}")
    print(f"Lifecycle service status: {lifecycle.status}")
    print(f"Daily report status: {daily_report.status}")
    print(f"Kill switch state: {kill_switch['state']}")
    print(f"Live execution without gates: {live_block.status}")


if __name__ == "__main__":
    main()
