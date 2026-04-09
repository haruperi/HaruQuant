"""Workflow-scoped memory binding primitives."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class WorkflowMemoryBinding:
    """Ephemeral memory namespaces bound to one workflow."""

    workflow_id: str
    session_id: str | None
    session_memory: dict[str, Any] = field(default_factory=dict)
    workflow_memory: dict[str, Any] = field(default_factory=dict)
    cached_context: dict[str, Any] = field(default_factory=dict)
    replay_memory_refs: tuple[str, ...] = ()


class WorkflowMemoryBindings:
    """Maintain isolated memory bindings per workflow."""

    def __init__(self) -> None:
        self._bindings: dict[str, WorkflowMemoryBinding] = {}

    def bind_workflow(
        self,
        *,
        workflow_id: str,
        session_id: str | None = None,
    ) -> WorkflowMemoryBinding:
        binding = self._bindings.get(workflow_id)
        if binding is not None:
            return binding
        created = WorkflowMemoryBinding(workflow_id=workflow_id, session_id=session_id)
        self._bindings[workflow_id] = created
        return created

    def get_binding(self, workflow_id: str) -> WorkflowMemoryBinding | None:
        return self._bindings.get(workflow_id)

    def update_session_memory(
        self,
        *,
        workflow_id: str,
        values: dict[str, Any],
    ) -> WorkflowMemoryBinding:
        binding = self._require_binding(workflow_id)
        updated = replace(
            binding,
            session_memory={**binding.session_memory, **values},
        )
        self._bindings[workflow_id] = updated
        return updated

    def update_workflow_memory(
        self,
        *,
        workflow_id: str,
        values: dict[str, Any],
    ) -> WorkflowMemoryBinding:
        binding = self._require_binding(workflow_id)
        updated = replace(
            binding,
            workflow_memory={**binding.workflow_memory, **values},
        )
        self._bindings[workflow_id] = updated
        return updated

    def update_cached_context(
        self,
        *,
        workflow_id: str,
        values: dict[str, Any],
    ) -> WorkflowMemoryBinding:
        binding = self._require_binding(workflow_id)
        updated = replace(
            binding,
            cached_context={**binding.cached_context, **values},
        )
        self._bindings[workflow_id] = updated
        return updated

    def append_replay_memory_ref(
        self,
        *,
        workflow_id: str,
        replay_ref: str,
    ) -> WorkflowMemoryBinding:
        binding = self._require_binding(workflow_id)
        replay_memory_refs = binding.replay_memory_refs
        if replay_ref not in replay_memory_refs:
            replay_memory_refs = (*replay_memory_refs, replay_ref)
        updated = replace(binding, replay_memory_refs=replay_memory_refs)
        self._bindings[workflow_id] = updated
        return updated

    def _require_binding(self, workflow_id: str) -> WorkflowMemoryBinding:
        binding = self.get_binding(workflow_id)
        if binding is None:
            raise LookupError(f"workflow memory binding not found: {workflow_id}")
        return binding
