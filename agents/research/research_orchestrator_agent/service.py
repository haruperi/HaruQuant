"""Service interface for the Research Department Orchestrator Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="research_orchestrator_agent",
    display_name="Research Department Orchestrator Agent",
    report_type="research_orchestration_report",
    prompt_version="research_orchestrator_agent_prompt_v1",
    policy_version="research_orchestrator_agent_policy_v1",
    purpose='Coordinates research agents, merges findings, resolves conflicts, and prepares final research packages.',
    allowed_actions=('create_research_plan', 'route_research_tasks', 'merge_research_reports', 'resolve_research_conflicts', 'produce_final_research_package', 'save_research_package', 'handoff_approved_hypothesis'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('call_research_agent_services', 'retrieve_evidence_memory', 'save_research_package'),
    required_evidence_sources=("research_request",),
    controlled_write_actions=('save_research_package',),
)


class ResearchOrchestratorAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)
