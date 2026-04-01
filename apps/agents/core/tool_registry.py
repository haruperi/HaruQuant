"""Central registry for typed, permission-bounded agent tools."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from apps.agents.core.agent_models import ToolSpec
from apps.agents.core.policies import PermissionTier


class ToolRegistry:
    """Store tool metadata independently from workflow logic."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool_spec: ToolSpec) -> None:
        """Register one tool spec after validating the declared mode."""
        PermissionTier.from_value(tool_spec.mode)
        if tool_spec.tool_name in self._tools:
            raise ValueError(f"Tool already registered: {tool_spec.tool_name}")
        self._tools[tool_spec.tool_name] = tool_spec

    def get(self, tool_name: str) -> Optional[ToolSpec]:
        """Return one tool spec if registered."""
        return self._tools.get(tool_name)

    def list_names(self) -> Iterable[str]:
        """Return tool names in stable order."""
        return tuple(sorted(self._tools))
