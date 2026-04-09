from __future__ import annotations

from backend.agents import WorkflowMemoryBindings


def test_workflow_memory_bindings_isolate_workflow_state() -> None:
    bindings = WorkflowMemoryBindings()

    bindings.bind_workflow(workflow_id="wf_001", session_id="sess_001")
    bindings.bind_workflow(workflow_id="wf_002", session_id="sess_002")
    bindings.update_session_memory(workflow_id="wf_001", values={"operator_id": "op_001"})
    bindings.update_workflow_memory(workflow_id="wf_001", values={"plan_id": "plan_001"})
    bindings.update_cached_context(workflow_id="wf_001", values={"market_snapshot_ref": "mkt_001"})

    first = bindings.get_binding("wf_001")
    second = bindings.get_binding("wf_002")

    assert first is not None
    assert second is not None
    assert first.session_memory == {"operator_id": "op_001"}
    assert first.workflow_memory == {"plan_id": "plan_001"}
    assert first.cached_context == {"market_snapshot_ref": "mkt_001"}
    assert second.session_memory == {}
    assert second.workflow_memory == {}
    assert second.cached_context == {}


def test_workflow_memory_bindings_preserve_immutable_replay_refs() -> None:
    bindings = WorkflowMemoryBindings()
    bindings.bind_workflow(workflow_id="wf_001")

    first = bindings.append_replay_memory_ref(workflow_id="wf_001", replay_ref="rpb_001")
    second = bindings.append_replay_memory_ref(workflow_id="wf_001", replay_ref="rpb_001")
    third = bindings.append_replay_memory_ref(workflow_id="wf_001", replay_ref="rpb_002")

    assert first.replay_memory_refs == ("rpb_001",)
    assert second.replay_memory_refs == ("rpb_001",)
    assert third.replay_memory_refs == ("rpb_001", "rpb_002")
