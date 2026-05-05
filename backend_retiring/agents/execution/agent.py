"""Execution Department facade for planning and governed execution handoff."""

from backend_retiring.agents.execution_agent import EXECUTION_AGENT_INSTRUCTION, ExecutionAgentWrapper

EXECUTION_DEPARTMENT = "execution"

__all__ = [
    "EXECUTION_DEPARTMENT",
    "EXECUTION_AGENT_INSTRUCTION",
    "ExecutionAgentWrapper",
]
