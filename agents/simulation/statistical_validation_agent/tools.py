"""Tool declarations for Statistical Validation Agent."""

from __future__ import annotations

TOOLS = ('agents/simulation/shared/constants.py', 'agents/simulation/shared/permissions.py', 'agents/simulation/shared/contracts.py', 'agents/simulation/shared/scoring.py', 'agents/simulation/shared/acceptance_rules.py', 'agents/simulation/shared/artifact_paths.py', 'agents/simulation/shared/reproducibility.py', 'agents/simulation/shared/run_manifest.py', 'agents/simulation/shared/report_builder.py', 'agents/simulation/shared/capabilities.py')


def deterministic_tool_stub(*args, **kwargs):
    return {"status": "available", "args": args, "kwargs": kwargs}


TOOL_FUNCTIONS = [deterministic_tool_stub]
