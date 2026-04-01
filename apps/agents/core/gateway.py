"""Small agent workflow gateway used by API/webhook entry points."""

from __future__ import annotations

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import AgentSettings, load_agent_settings
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.incident_investigator import IncidentInvestigatorAgent
from apps.agents.specialists.research_orchestrator import ResearchOrchestratorAgent
from apps.agents.specialists.risk_supervisor import RiskSupervisorAgent
from apps.agents.specialists.strategy_qa import StrategyQAAgent
from apps.agents.specialists.edge_intelligence import EdgeIntelligenceAgent
from apps.agents.specialists.execution_oversight import ExecutionOversightAgent
from apps.agents.specialists.portfolio_allocator import PortfolioAllocationAgent
from apps.agents.tools.catalog import build_default_tool_registry
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.live_tools import LiveTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.workflows.daily_market_brief import run_daily_market_brief
from apps.agents.workflows.execution_quality_watch import run_execution_quality_watch
from apps.agents.workflows.incident_review import run_incident_review
from apps.agents.workflows.live_risk_watch import run_live_risk_watch
from apps.agents.workflows.noop_workflow import run_noop_workflow
from apps.agents.workflows.portfolio_allocation_review import run_portfolio_allocation_review
from apps.agents.workflows.snapshot_drift_watch import run_snapshot_drift_watch
from apps.agents.workflows.strategy_promotion_review import run_strategy_promotion_review
from apps.agents.integrations.llm_client import NoOpLLMClient


class AgentWorkflowGateway:
    """Execute supported agent workflows from one normalized task contract."""

    def __init__(
        self,
        *,
        settings: AgentSettings | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.settings = settings or load_agent_settings("config/agent_settings.json")
        self.planner = AgentPlanner()
        self.verifier = AgentVerifier()
        self.audit_logger = AgentAuditLogger(self.settings.audit_log_path)
        self.tool_registry = tool_registry or build_default_tool_registry()

    def run_task(self, task: AgentTask) -> AgentResult:
        """Dispatch one task to the corresponding workflow runner."""
        plan = self.planner.plan(task)
        if plan.workflow_name == "noop_workflow":
            return run_noop_workflow(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                llm_client=NoOpLLMClient(),
            )
        if plan.workflow_name == "daily_market_brief":
            return run_daily_market_brief(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=ResearchOrchestratorAgent(EdgeTools()),
            )
        if plan.workflow_name == "live_risk_watch":
            return run_live_risk_watch(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=RiskSupervisorAgent(RiskTools()),
            )
        if plan.workflow_name == "incident_review":
            return run_incident_review(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=IncidentInvestigatorAgent(RiskTools()),
            )
        if plan.workflow_name == "strategy_promotion_review":
            return run_strategy_promotion_review(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=StrategyQAAgent(self.tool_registry),
            )
        if plan.workflow_name == "snapshot_drift_watch":
            return run_snapshot_drift_watch(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=EdgeIntelligenceAgent(EdgeTools()),
            )
        if plan.workflow_name == "execution_quality_watch":
            return run_execution_quality_watch(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=ExecutionOversightAgent(LiveTools()),
            )
        if plan.workflow_name == "portfolio_allocation_review":
            return run_portfolio_allocation_review(
                task,
                planner=self.planner,
                verifier=self.verifier,
                audit_logger=self.audit_logger,
                settings=self.settings,
                specialist=PortfolioAllocationAgent(RiskTools(), EdgeTools()),
            )
        raise ValueError(f"Unsupported workflow plan: {plan.workflow_name}")
