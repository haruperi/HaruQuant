from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Trace:
    trace_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    task_id: str | None = None
    workflow_id: str | None = None
    step_id: str | None = None
    tool_call_id: str | None = None
    agent_name: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    latency_ms: float | None = None
    cost: float | None = None
    result_status: str | None = None

