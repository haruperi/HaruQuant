"""Phase 6 agent control-plane orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agents.control_plane.agent_registry import AgentRegistry
from agents._shared import AgentBase, AgentRunResult
from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent
from agents._shared.schemas import AgentPlan
from agents.control_plane.task_manager import AgentTaskManager


@dataclass(frozen=True)
class AgentControlPlaneResult:
    workflow_id: str
    request_id: str
    parent_task_id: str
    planner_task_id: str
    child_task_ids: list[str]
    planner_result: AgentPlan
    agent_outputs: dict[str, AgentRunResult] = field(default_factory=dict)
    execution_trace: dict[str, Any] = field(default_factory=dict)
    final_response: dict[str, Any] = field(default_factory=dict)
    audit_id: str | None = None


class _DepartmentAgent(AgentBase):
    def __init__(self, *, agent_name: str, role: str, allowed_tools: tuple[str, ...]) -> None:
        self.agent_name = agent_name
        self.role = role
        self.allowed_tools = allowed_tools


class AgentControlPlaneOrchestrator:
    """Accepts a user request, plans, delegates, traces, and audits it."""

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        task_manager: AgentTaskManager | None = None,
        planner: PlannerAgent | None = None,
        ceo: CEOAgent | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.task_manager = task_manager or AgentTaskManager()
        self.planner = planner or PlannerAgent()
        self.ceo = ceo or CEOAgent()

    def handle_user_request(
        self,
        *,
        user_request: str,
        workflow_id: str | None = None,
        request_id: str | None = None,
    ) -> AgentControlPlaneResult:
        workflow_id = workflow_id or f"wf-{uuid4().hex}"
        request_id = request_id or f"req-{uuid4().hex}"
        self._ensure_workflow(workflow_id, user_request)

        parent = self.task_manager.create_task(
            task_id=f"{workflow_id}-ceo",
            workflow_id=workflow_id,
            title="CEO control-plane request",
            description=user_request,
            owner_agent="ceo",
            expected_output_contract="AgentControlPlaneResult",
        )
        self.task_manager.assign_task(parent.task_id, owner_agent="ceo")
        self.task_manager.start_task(parent.task_id, actor_id="ceo")

        planner_task = self.task_manager.create_child_task(
            task_id=f"{workflow_id}-planner",
            parent_task_id=parent.task_id,
            workflow_id=workflow_id,
            title="Plan workflow",
            description="Create structured agent delegation plan.",
            owner_agent="planner",
            expected_output_contract="AgentPlan",
        )
        self.task_manager.assign_task(planner_task.task_id, owner_agent="planner")
        self.task_manager.start_task(planner_task.task_id, actor_id="planner")
        planner_result = self.planner.create_plan(
            user_request=user_request,
            request_id=request_id,
        )
        self.task_manager.complete_task(planner_task.task_id, actor_id="planner")

        child_task_ids: list[str] = [planner_task.task_id]
        agent_outputs: dict[str, AgentRunResult] = {}
        failed_agents: list[str] = []
        for agent_name in planner_result.allowed_agents:
            if agent_name in {"ceo", "planner"}:
                continue
            descriptor = self.registry.require(agent_name)
            child = self.task_manager.create_child_task(
                parent_task_id=parent.task_id,
                workflow_id=workflow_id,
                title=f"{descriptor.agent_name} delegated work",
                description=f"Execute {planner_result.intent} duties.",
                owner_agent=descriptor.agent_name,
                expected_output_contract="AgentRunResult",
            )
            child_task_ids.append(child.task_id)
            self.task_manager.assign_task(child.task_id, owner_agent=descriptor.agent_name)
            self.task_manager.start_task(child.task_id, actor_id=descriptor.agent_name)
            output = _DepartmentAgent(
                agent_name=descriptor.agent_name,
                role=descriptor.role,
                allowed_tools=descriptor.allowed_tools,
            ).run(child, {"planner_result": planner_result.model_dump(mode="json")})
            agent_outputs[descriptor.agent_name] = output
            if output.status == "completed":
                self.task_manager.complete_task(child.task_id, actor_id=descriptor.agent_name)
            else:
                failed_agents.append(descriptor.agent_name)
                self.task_manager.fail_task(child.task_id, actor_id=descriptor.agent_name)

        self.task_manager.complete_task(parent.task_id, actor_id="ceo")
        audit_id = f"audit-{uuid4().hex}"
        execution_trace = {
            "planner_result": planner_result.model_dump(mode="json"),
            "agent_instructions": {
                agent: f"Execute {planner_result.intent} duties."
                for agent in agent_outputs
            },
            "tool_calls": [],
            "observations": [
                observation
                for output in agent_outputs.values()
                for observation in output.observations
            ],
            "final_decisions": [
                decision
                for output in agent_outputs.values()
                for decision in output.decisions
            ],
            "evidence_refs": [
                evidence
                for output in agent_outputs.values()
                for evidence in output.evidence_refs
            ],
            "failure_reasons": {
                agent: output.failure_reason
                for agent, output in agent_outputs.items()
                if output.failure_reason
            },
        }
        final_response = {
            "summary": "CEO Agent completed delegated firm workflow.",
            "request": user_request,
            "intent": planner_result.intent,
            "ceo_memo": self.ceo.create_final_memo(
                request=user_request,
                planner_result=planner_result,
                agent_outputs=agent_outputs,
                evidence_refs=execution_trace["evidence_refs"],
            ),
            "completed_agents": [
                agent for agent, output in agent_outputs.items() if output.status == "completed"
            ],
            "failed_agents": failed_agents,
            "evidence_refs": execution_trace["evidence_refs"],
        }
        self._append_audit(
            audit_id=audit_id,
            workflow_id=workflow_id,
            request_id=request_id,
            parent_task_id=parent.task_id,
            metadata={
                "phase": "7",
                "planner_intent": planner_result.intent,
                "child_task_ids": child_task_ids,
                "execution_trace": execution_trace,
            },
        )
        return AgentControlPlaneResult(
            workflow_id=workflow_id,
            request_id=request_id,
            parent_task_id=parent.task_id,
            planner_task_id=planner_task.task_id,
            child_task_ids=child_task_ids,
            planner_result=planner_result,
            agent_outputs=agent_outputs,
            execution_trace=execution_trace,
            final_response=final_response,
            audit_id=audit_id,
        )

    def _ensure_workflow(self, workflow_id: str, objective: str) -> None:
        repository = self.task_manager.repository
        if repository is None:
            return
        with repository._connect() as connection:  # noqa: SLF001
            connection.execute(
                """
                INSERT OR IGNORE INTO core_workflows (
                    workflow_id,
                    workflow_type,
                    environment,
                    operating_mode,
                    state,
                    objective,
                    scope_json,
                    initiator_type,
                    initiator_id,
                    timeout_policy_json,
                    stop_conditions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    "agent_control_plane",
                    "paper",
                    "MODE-002",
                    "CREATED",
                    objective,
                    "{}",
                    "user",
                    "operator",
                    "{}",
                    "[]",
                ),
            )

    def _append_audit(
        self,
        *,
        audit_id: str,
        workflow_id: str,
        request_id: str,
        parent_task_id: str,
        metadata: dict[str, Any],
    ) -> None:
        repository = self.task_manager.repository
        if repository is None:
            return
        import json

        repository.append_audit_log(
            audit_id=audit_id,
            actor_name="ceo",
            agent_name="ceo",
            action_type="agent_control_plane_run",
            input_hash=f"request:{request_id}",
            output_hash=f"workflow:{workflow_id}",
            request_id=request_id,
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            metadata_json=json.dumps(metadata, sort_keys=True),
        )


__all__ = ["AgentControlPlaneOrchestrator", "AgentControlPlaneResult"]
