"""Pre-execution tool parameter validation.

Validates tool call parameters against registered schemas BEFORE
tool execution, preventing dangerous or malformed tool invocations.
"""

from __future__ import annotations

from backend.common.logger import logger
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolParameterSchema:
    """Expected schema for a tool's parameters."""
    name: str
    required_fields: tuple[str, ...] = ()
    optional_fields: dict[str, str] = field(default_factory=dict)  # field_name -> type hint
    max_output_tokens: int = 4096
    description: str = ""


class ToolValidationError(ValueError):
    """Raised when tool parameter validation fails."""
    pass


class ToolValidator:
    """Pre-execution tool parameter validation registry."""

    def __init__(self) -> None:
        self._schemas: dict[str, ToolParameterSchema] = {}

    def register(self, tool_name: str, schema: ToolParameterSchema) -> None:
        """Register a parameter schema for a tool."""
        self._schemas[tool_name] = schema

    def register_simple(self, tool_name: str, required_fields: tuple[str, ...] = (),
                        optional_fields: dict[str, str] | None = None,
                        max_output_tokens: int = 4096) -> None:
        """Convenience: register a simple schema."""
        self._schemas[tool_name] = ToolParameterSchema(
            name=tool_name,
            required_fields=required_fields,
            optional_fields=optional_fields or {},
            max_output_tokens=max_output_tokens,
        )

    def validate(self, tool_call: dict[str, Any]) -> None:
        """Validate a tool call against its registered schema.

        Raises ToolValidationError if validation fails.
        """
        name = tool_call.get("tool_name") or tool_call.get("name") or ""
        if name not in self._schemas:
            raise ToolValidationError(f"Unknown tool: {name}")

        schema = self._schemas[name]
        params = tool_call.get("parameters", tool_call.get("arguments", {}))

        # Check required fields
        for req_field in schema.required_fields:
            if req_field not in params:
                raise ToolValidationError(
                    f"Tool '{name}' requires parameter '{req_field}' (missing)"
                )

        # Check optional field types (basic string matching for type hints)
        for opt_field, type_hint in schema.optional_fields.items():
            if opt_field in params:
                value = params[opt_field]
                if not self._check_type(value, type_hint):
                    raise ToolValidationError(
                        f"Tool '{name}' parameter '{opt_field}' expected type '{type_hint}', "
                        f"got {type(value).__name__}"
                    )

    def get_schema(self, tool_name: str) -> ToolParameterSchema | None:
        """Get the registered schema for a tool, or None."""
        return self._schemas.get(tool_name)

    def get_max_output_tokens(self, tool_name: str) -> int:
        """Get the max output tokens for a tool."""
        schema = self._schemas.get(tool_name)
        return schema.max_output_tokens if schema else 4096

    @staticmethod
    def _check_type(value: Any, type_hint: str) -> bool:
        """Basic type check against a string hint."""
        if type_hint == "str" or type_hint == "string":
            return isinstance(value, str)
        if type_hint == "int" or type_hint == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if type_hint == "float" or type_hint == "number":
            return isinstance(value, (int, float))
        if type_hint == "bool" or type_hint == "boolean":
            return isinstance(value, bool)
        if type_hint == "list" or type_hint == "array":
            return isinstance(value, (list, tuple))
        if type_hint == "dict" or type_hint == "object":
            return isinstance(value, dict)
        return True  # Unknown type hint — allow


# Pre-registered schemas for common MCP tools
def register_mcp_schemas(validator: ToolValidator) -> None:
    """Register parameter schemas for common MCP tools."""
    validator.register_simple("get_account_info")
    validator.register_simple("list_positions")
    validator.register_simple("list_orders")
    validator.register_simple("get_symbol_info", required_fields=("symbol",))
    validator.register_simple("get_ticks", required_fields=("symbol",), optional_fields={"count": "int"})
    validator.register_simple("place_order", required_fields=("symbol", "action"), optional_fields={"volume": "float", "price": "float", "stop_loss": "float", "take_profit": "float"})
    validator.register_simple("modify_position", required_fields=("ticket",))
    validator.register_simple("partial_close", required_fields=("ticket", "volume"))
    validator.register_simple("full_close", required_fields=("ticket",))
    validator.register_simple("cancel_order", required_fields=("ticket",))
    validator.register_simple("execute_query", required_fields=("query",))
    validator.register_simple("search_knowledge", required_fields=("query",), optional_fields={"top_k": "int", "category": "str"})
