from agents.simulation.shared.workflow import run_simulation_department_workflow_sync


def test_simulation_department_workflow_runs():
    responses = run_simulation_department_workflow_sync({"strategy_id": "demo", "strategy_code_hash": "hash", "optimization_requested": True})
    assert "simulation_orchestrator_agent" in responses
    assert responses["backtest_agent"].artifacts["backtest_result_package"]["manifest"]["strategy_code_hash"] == "hash"
    assert "execute_trade" in responses["simulation_orchestrator_agent"].decision.blocked_actions
