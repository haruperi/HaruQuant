"""Declarative YAML workflow definitions.

Allows workflows to be defined as YAML data instead of imperative Python code.
Parses definitions into workflow runner configurations for all 5 patterns:
sequential, routing, parallel, evaluator-optimizer, orchestrator-workers.
"""

from __future__ import annotations

from haruquant.utils import logger
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import os

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class WorkflowPattern(str, Enum):
    SEQUENTIAL = "sequential"
    ROUTING = "routing"
    PARALLEL = "parallel"
    EVALUATOR_OPTIMIZER = "evaluator_optimizer"
    ORCHESTRATOR_WORKERS = "orchestrator_workers"


@dataclass(frozen=True)
class WorkflowStepDef:
    """Definition of a single workflow step."""
    name: str
    agent: str
    input: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None
    validate: bool = True
    timeout_seconds: Optional[float] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowRouteDef:
    """Definition of a routing branch."""
    route_key: str
    agent: str
    input: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None


@dataclass(frozen=True)
class WorkflowDefinition:
    """Complete workflow definition parsed from YAML."""
    name: str
    pattern: WorkflowPattern
    description: str = ""
    steps: List[WorkflowStepDef] = field(default_factory=list)
    routes: List[WorkflowRouteDef] = field(default_factory=list)
    default_route: Optional[WorkflowRouteDef] = None
    evaluator: Optional[Dict[str, Any]] = None
    acceptance_threshold: float = 0.8
    max_iterations: int = 3
    version: str = "1.0.0"
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            object.__setattr__(
                self, "content_hash",
                hashlib.sha256(f"{self.name}:{self.pattern.value}:{self.version}".encode()).hexdigest()[:16],
            )


class WorkflowDefinitionParser:
    """Parses YAML workflow definitions into WorkflowDefinition objects."""

    def parse(self, yaml_content: str) -> WorkflowDefinition:
        """Parse a YAML string into a WorkflowDefinition.

        Raises:
            ValueError: If YAML is invalid or required fields are missing.
            ImportError: If PyYAML is not installed.
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is required. Install with: pip install pyyaml")

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Workflow definition must be a YAML mapping")

        name = data.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("Workflow definition requires a 'name' string field")

        pattern_str = data.get("pattern", "sequential")
        try:
            pattern = WorkflowPattern(pattern_str)
        except ValueError:
            valid = [p.value for p in WorkflowPattern]
            raise ValueError(f"Invalid pattern '{pattern_str}'. Must be one of: {valid}") from None

        description = str(data.get("description", ""))
        version = str(data.get("version", "1.0.0"))
        acceptance_threshold = float(data.get("acceptance_threshold", 0.8))
        max_iterations = int(data.get("max_iterations", 3))

        # Parse steps (for sequential, parallel, evaluator-optimizer patterns)
        steps = []
        steps_data = data.get("steps", [])
        if isinstance(steps_data, list):
            for i, step_data in enumerate(steps_data):
                if not isinstance(step_data, dict):
                    raise ValueError(f"Step {i} must be a YAML mapping")
                step_name = step_data.get("name")
                if not step_name:
                    raise ValueError(f"Step {i} requires a 'name' field")
                agent = step_data.get("agent")
                if not agent:
                    raise ValueError(f"Step '{step_name}' requires an 'agent' field")

                steps.append(WorkflowStepDef(
                    name=str(step_name),
                    agent=str(agent),
                    input=dict(step_data.get("input", {})),
                    expected_output=step_data.get("expected_output"),
                    validate=bool(step_data.get("validate", True)),
                    timeout_seconds=step_data.get("timeout_seconds"),
                    depends_on=list(step_data.get("depends_on", [])),
                ))

        # Parse routes (for routing pattern)
        routes = []
        default_route = None
        routes_data = data.get("routes", [])
        if isinstance(routes_data, list):
            for i, route_data in enumerate(routes_data):
                if not isinstance(route_data, dict):
                    raise ValueError(f"Route {i} must be a YAML mapping")
                route_key = route_data.get("route_key")
                if not route_key:
                    raise ValueError(f"Route {i} requires a 'route_key' field")
                agent = route_data.get("agent")
                if not agent:
                    raise ValueError(f"Route '{route_key}' requires an 'agent' field")

                route_def = WorkflowRouteDef(
                    route_key=str(route_key),
                    agent=str(agent),
                    input=dict(route_data.get("input", {})),
                    expected_output=route_data.get("expected_output"),
                )
                if route_data.get("is_default"):
                    default_route = route_def
                else:
                    routes.append(route_def)

        evaluator = data.get("evaluator")
        if evaluator is not None and not isinstance(evaluator, dict):
            raise ValueError("Evaluator must be a YAML mapping")

        return WorkflowDefinition(
            name=name,
            pattern=pattern,
            description=description,
            steps=steps,
            routes=routes,
            default_route=default_route,
            evaluator=evaluator,
            acceptance_threshold=acceptance_threshold,
            max_iterations=max_iterations,
            version=version,
        )


class WorkflowRegistry:
    """Loads and caches workflow definitions from a directory."""

    def __init__(self, workflow_dir: Optional[str] = None) -> None:
        self._parser = WorkflowDefinitionParser()
        self._workflow_dir = workflow_dir or os.path.join(
            "backend",
            "orchestration",
            "workflow",
            "definitions",
        )
        self._cache: Dict[str, WorkflowDefinition] = {}

    def load(self, workflow_name: str) -> WorkflowDefinition:
        """Load a workflow definition by name.

        Looks for <workflow_name>.yaml in the workflow directory.
        Caches loaded definitions.
        """
        if workflow_name in self._cache:
            return self._cache[workflow_name]

        yaml_path = os.path.join(self._workflow_dir, f"{workflow_name}.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Workflow definition not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        definition = self._parser.parse(content)
        self._cache[workflow_name] = definition
        return definition

    def list_workflows(self) -> List[str]:
        """List all available workflow names in the workflow directory."""
        if not os.path.exists(self._workflow_dir):
            return []
        return [
            f.replace(".yaml", "")
            for f in os.listdir(self._workflow_dir)
            if f.endswith(".yaml")
        ]

    def register(self, name: str, definition: WorkflowDefinition) -> None:
        """Register a workflow definition programmatically."""
        self._cache[name] = definition


def run_workflow(
    workflow_name: str,
    registry: Optional[WorkflowRegistry] = None,
    **inputs: Any,
) -> Dict[str, Any]:
    """Convenience function to run a workflow by name.

    Loads the workflow definition from the registry and returns
    the parsed definition as a dict for inspection.

    Note: Actual execution requires a workflow engine that interprets
    the definition and dispatches to appropriate runners.
    """
    reg = registry or WorkflowRegistry()
    definition = reg.load(workflow_name)
    return {
        "workflow": definition.name,
        "pattern": definition.pattern.value,
        "version": definition.version,
        "step_count": len(definition.steps),
        "route_count": len(definition.routes),
        "has_default_route": definition.default_route is not None,
    }
