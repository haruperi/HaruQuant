from agents.executive.ceo_agent.internal.planner_agent.agent import build_agent


def test_build_agent():
    assert build_agent()["name"] == "internal_planner_agent"
