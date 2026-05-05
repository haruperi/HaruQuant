"""Function-based workflow executor for step implementations.

Complements backend/orchestration/workflow/executor.py (the full ADK-based
executor). This simpler executor maps YAML step names to Python functions,
runs them in order, and collects results — ideal for examples, testing,
and direct API integration.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Dict, Optional

from backend.agents.runtime.workflow_definition import WorkflowRegistry
from haruquant.utils import logger

from .steps_data_transformation import STEP_IMPLEMENTATIONS, WorkflowContext


class WorkflowStepError(Exception):
    """Raised when a workflow step implementation fails."""
    pass


def _filter_kwargs(fn: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the kwargs that fn actually accepts."""
    sig = inspect.signature(fn)
    params = set(sig.parameters.keys())
    params.discard("ctx")
    return {k: v for k, v in kwargs.items() if k in params}


class WorkflowExecutor:
    """Load a YAML workflow definition and execute it step-by-step.

    Maps each step name to a registered implementation function,
    runs them in definition order, and collects results.
    """

    def __init__(
        self,
        step_registry: Optional[Dict[str, Callable]] = None,
        workflow_registry: Optional[WorkflowRegistry] = None,
    ) -> None:
        self._step_registry = step_registry or {}
        self._wf_registry = workflow_registry or WorkflowRegistry()

    def register_step(self, step_name: str, fn: Callable) -> None:
        """Register or override a step implementation."""
        self._step_registry[step_name] = fn

    def execute(
        self,
        workflow_name: str,
        context: Optional[WorkflowContext] = None,
        **step_kwargs: Any,
    ) -> Dict[str, Any]:
        """Load and execute a named workflow.

        Args:
            workflow_name: Name of the YAML workflow (e.g. "data_transformation").
            context: Mutable context dict shared across steps.
            **step_kwargs: Keyword arguments forwarded to steps that accept them.

        Returns:
            Dict mapping step names to their result dicts.
        """
        wf_def = self._wf_registry.load(workflow_name)
        ctx = context if context is not None else WorkflowContext()
        ctx["workflow_definition"] = {
            "name": wf_def.name,
            "version": wf_def.version,
            "pattern": wf_def.pattern.value,
        }

        results: Dict[str, Any] = {}
        for step_def in wf_def.steps:
            handler = self._step_registry.get(step_def.name)
            if handler is None:
                logger.warning(
                    f"WorkflowExecutor: no handler for step '{step_def.name}', skipping"
                )
                continue

            logger.info(f"WorkflowExecutor: running step '{step_def.name}'")
            t0 = time.time()
            try:
                filtered_kwargs = _filter_kwargs(handler, step_kwargs)
                step_result = handler(ctx, **filtered_kwargs)
            except Exception as exc:
                raise WorkflowStepError(
                    f"Step '{step_def.name}' failed: {exc}"
                ) from exc
            elapsed = time.time() - t0

            status = step_result.get("status", "UNKNOWN")
            logger.info(
                f"WorkflowExecutor: step '{step_def.name}' → {status} ({elapsed:.2f}s)"
            )
            results[step_def.name] = step_result

        return results
