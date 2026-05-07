"""Runtime adapter boundary for the Strategy Risk Assumption Agent."""

from __future__ import annotations

from agents.strategy_development.shared.strategy_agent import build_runtime_agent

from .prompts import SYSTEM_INSTRUCTIONS
from .service import CONFIG
from .tools import TOOLS


def build_agent():
    return build_runtime_agent(CONFIG, SYSTEM_INSTRUCTIONS, TOOLS)
