"""Runtime adapter boundary for the Macro and Fundamental Context Agent."""

from __future__ import annotations

from agents.research.shared.research_agent import build_runtime_agent

from .prompts import SYSTEM_INSTRUCTIONS
from .service import CONFIG
from .tools import TOOLS


def build_agent():
    return build_runtime_agent(CONFIG, SYSTEM_INSTRUCTIONS, TOOLS)
