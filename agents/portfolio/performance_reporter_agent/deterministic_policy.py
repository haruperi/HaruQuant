from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent, PortfolioAgentConfig
CONFIG = PortfolioAgentConfig(agent_name="performance_reporter", display_name="Performance Reporter Agent", allowed_actions=['generate_daily_report', 'generate_weekly_board_report', 'generate_monthly_strategy_review'], blocked_actions=['change_allocation', 'approve_strategy_promotion', 'execute_trade', 'approve_risk'], required_evidence=['performance_snapshot', 'audit_health_status'], permission_profile="portfolio_read_only_v1")
def make_policy_decision(task_input: dict, evidence_state: dict) -> dict:
    return GenericPortfolioAgent(CONFIG).deterministic_policy(task_input, evidence_state)
