from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent, PortfolioAgentConfig
CONFIG = PortfolioAgentConfig(agent_name="execution_readiness", display_name="Execution Readiness Agent", allowed_actions=['check_execution_readiness', 'flag_broker_health', 'flag_audit_health', 'request_live_trading_disable'], blocked_actions=['execute_trade', 'approve_risk', 'resume_live_trading'], required_evidence=['broker_health', 'audit_health_status', 'risk_governor_status'], permission_profile="portfolio_read_only_v1")
def make_policy_decision(task_input: dict, evidence_state: dict) -> dict:
    return GenericPortfolioAgent(CONFIG).deterministic_policy(task_input, evidence_state)
