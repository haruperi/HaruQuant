"""Service interface for the Research Validation Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="research_validation_agent",
    display_name="Research Validation Agent",
    report_type="research_validation_report",
    prompt_version="research_validation_agent_prompt_v1",
    policy_version="research_validation_agent_policy_v1",
    purpose='Challenges research conclusions, checks evidence quality, bias risk, missing evidence, and handoff readiness.',
    allowed_actions=('validate_research_evidence', 'assign_validation_status', 'block_weak_hypotheses', 'save_validation_result', 'handoff_approved_hypothesis'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('retrieve_research_reports', 'check_evidence_quality', 'check_bias_risks', 'save_research_validation_report'),
    required_evidence_sources=("research_validation_context",),
    controlled_write_actions=('save_validation_result',),
)


class ResearchValidationAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)
