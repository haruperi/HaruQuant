"""Service interface for the Evidence Curator Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import GenericResearchAgentService, ResearchAgentConfig

CONFIG = ResearchAgentConfig(
    agent_name="evidence_curator_agent",
    display_name="Evidence Curator Agent",
    report_type="evidence_curator_report",
    prompt_version="evidence_curator_agent_prompt_v1",
    policy_version="evidence_curator_agent_policy_v1",
    purpose='Keeps Research Department evidence memory searchable, auditable, deduplicated, versioned, fresh, and linked.',
    allowed_actions=('save_research_report', 'save_evidence_ref', 'deduplicate_evidence', 'link_evidence', 'mark_stale', 'build_evidence_index'),
    blocked_actions=('place_trade', 'execute_order', 'approve_risk', 'modify_portfolio', 'deploy_strategy'),
    tool_names=('save_evidence_item', 'search_evidence_memory', 'deduplicate_evidence', 'link_evidence_to_report', 'mark_evidence_stale', 'mark_report_superseded'),
    required_evidence_sources=("evidence_memory_request",),
    controlled_write_actions=('save_research_report', 'save_evidence_ref', 'link_evidence', 'mark_stale'),
)


class EvidenceCuratorAgentService(GenericResearchAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)
