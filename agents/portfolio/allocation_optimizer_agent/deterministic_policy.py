from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent, PortfolioAgentConfig
CONFIG = PortfolioAgentConfig(agent_name="allocation_optimizer", display_name="Allocation Optimizer Agent", allowed_actions=['recommend_capital_increases', 'recommend_capital_decreases', 'recommend_capped_allocation', 'recommend_no_change'], blocked_actions=['directly_change_live_allocation', 'bypass_board_approval', 'approve_risk', 'execute_trade'], required_evidence=['current_allocations', 'risk_constraints'], permission_profile="portfolio_allocation_recommendation_v1")
def make_policy_decision(task_input: dict, evidence_state: dict) -> dict:
    return GenericPortfolioAgent(CONFIG).deterministic_policy(task_input, evidence_state)
