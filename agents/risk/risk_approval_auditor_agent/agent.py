"""Runtime wrapper."""

from __future__ import annotations

from agents.risk.shared.risk_agent import build_runtime_agent

from .prompts import SYSTEM_PROMPT
from .service import CONFIG
from .tools import TOOL_FUNCTIONS


def build_agent():
    return build_runtime_agent(CONFIG, SYSTEM_PROMPT, TOOL_FUNCTIONS)
