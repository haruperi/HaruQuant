from agents.portfolio.live_execution_agent.deterministic_policy import evaluate_live_execution_gates


def test_live_mode_disabled_blocks():
    assert "live_mode_disabled" in evaluate_live_execution_gates({"strategy_state": "live", "kill_switch_status": "healthy"})
