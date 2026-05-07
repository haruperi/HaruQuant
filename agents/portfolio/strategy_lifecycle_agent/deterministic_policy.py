from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent, PortfolioAgentConfig
CONFIG = PortfolioAgentConfig(agent_name="strategy_lifecycle", display_name="Strategy Lifecycle Agent", allowed_actions=['recommend_lifecycle_transition', 'request_more_evidence', 'record_transition_audit'], blocked_actions=['skip_lifecycle_stage', 'promote_live_without_board_approval', 'execute_trade', 'approve_risk'], required_evidence=['current_lifecycle_state', 'requested_lifecycle_transition'], permission_profile="portfolio_lifecycle_recommendation_v1")
def make_policy_decision(task_input: dict, evidence_state: dict) -> dict:
    return GenericPortfolioAgent(CONFIG).deterministic_policy(task_input, evidence_state)
