from agents.portfolio.shared.portfolio_agent import GenericPortfolioAgent, PortfolioAgentConfig
CONFIG = PortfolioAgentConfig(agent_name="cost_optimizer", display_name="Cost Optimizer Agent", allowed_actions=['produce_daily_cost_report', 'produce_weekly_cost_report', 'recommend_cache_usage', 'recommend_cheaper_model_routing'], blocked_actions=['weaken_risk_controls', 'route_risk_governor_to_llm', 'route_execution_decisions_to_llm'], required_evidence=['cost_usage'], permission_profile="cost_read_only_v1")
def make_policy_decision(task_input: dict, evidence_state: dict) -> dict:
    return GenericPortfolioAgent(CONFIG).deterministic_policy(task_input, evidence_state)
