"""Central registry for typed, permission-bounded agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from apps.agents.core.agent_models import ToolSpec
from apps.agents.core.policies import PermissionTier


@dataclass(frozen=True)
class RegisteredTool:
    """Bind one tool spec to a callable implementation."""

    spec: ToolSpec
    handler: Callable[..., Any]


class ToolRegistry:
    """Store tool metadata independently from workflow logic."""

    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register(self, tool_spec: ToolSpec, handler: Callable[..., Any]) -> None:
        """Register one tool spec and its implementation."""
        PermissionTier.from_value(tool_spec.mode)
        if tool_spec.tool_name in self._tools:
            raise ValueError(f"Tool already registered: {tool_spec.tool_name}")
        self._tools[tool_spec.tool_name] = RegisteredTool(spec=tool_spec, handler=handler)

    def get(self, tool_name: str) -> Optional[ToolSpec]:
        """Return one tool spec if registered."""
        tool = self._tools.get(tool_name)
        return None if tool is None else tool.spec

    def get_registered(self, tool_name: str) -> Optional[RegisteredTool]:
        """Return the registered tool including handler if present."""
        return self._tools.get(tool_name)

    def execute(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute one registered tool by name."""
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool not registered: {tool_name}")
        return tool.handler(**kwargs)

    def list_names(self) -> Iterable[str]:
        """Return tool names in stable order."""
        return tuple(sorted(self._tools))
