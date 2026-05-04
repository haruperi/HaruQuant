"""Agent control-plane orchestrator for the HaruQuant Agentic Firm."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any
from uuid import uuid4

from backend.agents.agent_registry import AgentRegistry, get_default_agent_registry
from backend.agents.base import AgentRunContext, AgentRunResult
from backend.agents.schemas import AgentTaskStatus
from backend.agents.task_manager import AgentTaskManager
from backend.services.ai_chat.models import ConversationPlan


@dataclass(frozen=True)
class AgentControlPlaneResult:
    """Structured result of one top-down firm workflow."""

    workflow_id: str
    request_id: str
    parent_task_id: str
    planner_result: ConversationPlan
    child_task_ids: tuple[str, ...]
    agent_results: tuple[AgentRunResult, ...]
    final_response: dict[str, Any]
    audit_id: str | None = None


class DefaultFirmPlanner:
    """Small deterministic Phase 6 planner.

    This does not replace the existing AI chat planner. It gives the firm
    control plane a stable planning contract until Phase 7 wires in the full CEO
    and Planner agents.
    """

    def plan(self, *, user_request: str, request_id: str) -> ConversationPlan:
        normalized = user_request.lower()
        agents = ["research", "strategy_creator", "strategy_reviewer"]
        expected_outputs = ["research_summary", "strategy_spec", "strategy_review"]
        backend_tools = ["get_symbol_data", "get_latest_ohlcv", "create_strategy_spec"]
        task_class = "strategy_creation"
        artifact_expected = "strategy_artifact"
        if "backtest" in normalized:
            agents.append("backtest")
            expected_outputs.append("backtest_summary")
            backend_tools.append("run_backtest")
            task_class = "backtest_workflow"
        if "risk" in normalized or "approval" in normalized:
            agents.append("risk_reviewer")
            expected_outputs.append("risk_review")
            backend_tools.extend(["get_risk_snapshot", "create_risk_review"])
            task_class = "risk_review"
        if "report" in normalized or "memo" in normalized:
            agents.append("performance_reporter")
            expected_outputs.append("firm_report")
            backend_tools.append("create_report")

        agents.extend(["audit", "ceo"])
        expected_outputs.extend(["audit_trace", "ceo_summary"])

        return ConversationPlan(
            conversation_plan_id=f"plan-{uuid4().hex}",
            user_goal=user_request,
            answer_mode="governed_artifact",
            response_mode="answer",
            task_class=task_class,
            model_tier="standard",
            response_style="firm_memo",
            domain_focus=task_class,
            rationale="Phase 6 deterministic control-plane planner selected a governed firm workflow.",
            intent=task_class,
            backend_tools_to_run=list(dict.fromkeys(backend_tools)),
            agents_to_consult=list(dict.fromkeys(agents)),
            attached_tools=[],
            artifact_expected=artifact_expected,
            risk_level="supervised_drafts",
            requires_audit_log=True,
            allowed_agents=list(dict.fromkeys(agents)),
            expected_outputs=list(dict.fromkeys(expected_outputs)),
            evidence_requirements=["planner_result", "agent_outputs", "audit_trace"],
            failure_policy={"default": "fail_parent_if_required_child_fails"},
            planner_source="phase6_control_plane",
            planner_confidence=0.82,
        )


class AgentControlPlaneOrchestrator:
    """Top-down service that plans, delegates, traces, and audits firm work."""

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        task_manager: AgentTaskManager | None = None,
        planner: DefaultFirmPlanner | None = None,
    ) -> None:
        self.registry = registry or get_default_agent_registry()
        self.task_manager = task_manager or AgentTaskManager()
        self.planner = planner or DefaultFirmPlanner()

    def handle_user_request(
        self,
        *,
        user_request: str,
        workflow_id: str | None = None,
        request_id: str | None = None,
    ) -> AgentControlPlaneResult:
        workflow_id = workflow_id or f"wf-{uuid4().hex}"
        request_id = request_id or f"req-{uuid4().hex}"
        planner_result = self.planner.plan(user_request=user_request, request_id=request_id)
        self._ensure_workflow_record(
            workflow_id=workflow_id,
            objective=user_request,
            request_id=request_id,
            task_class=planner_result.task_class,
        )

        parent_task = self.task_manager.create_task(
            task_id=f"task-{uuid4().hex}",
            workflow_id=workflow_id,
            title="CEO firm request",
            description=user_request,
            owner_agent="ceo",
            expected_output_contract="AgentControlPlaneResult",
            metadata={"request_id": request_id, "planner_result": planner_result.model_dump(mode="json")},
        )
        self.task_manager.assign_task(parent_task.task_id, owner_agent="ceo", actor_id="planner")
        self.task_manager.start_task(parent_task.task_id, actor_id="ceo")

        planner_task = self.task_manager.create_child_task(
            parent_task_id=parent_task.task_id,
            title="Create firm plan",
            description=planner_result.rationale,
            owner_agent="planner",
            expected_output_contract="ConversationPlan",
            metadata={"planner_result": planner_result.model_dump(mode="json")},
        )
        self.task_manager.assign_task(planner_task.task_id, owner_agent="planner", actor_id="ceo")
        self.task_manager.start_task(planner_task.task_id, actor_id="planner")
        self.task_manager.complete_task(
            planner_task.task_id,
            actor_id="planner",
            output=planner_result.model_dump(mode="json"),
        )

        child_tasks = self._create_child_tasks(
            parent_task_id=parent_task.task_id,
            planner_result=planner_result,
        )
        agent_results = self._dispatch_child_tasks(
            workflow_id=workflow_id,
            request_id=request_id,
            parent_task_id=parent_task.task_id,
            planner_result=planner_result,
            child_tasks=child_tasks,
        )
        final_response = self._produce_final_response(
            user_request=user_request,
            planner_result=planner_result,
            agent_results=agent_results,
        )

        failed_results = tuple(result for result in agent_results if result.status != "completed")
        if failed_results:
            self.task_manager.fail_task(
                parent_task.task_id,
                actor_id="ceo",
                reason="One or more child agents failed.",
            )
        else:
            self.task_manager.complete_task(
                parent_task.task_id,
                actor_id="ceo",
                output=final_response,
            )

        audit_id = self._write_audit_record(
            workflow_id=workflow_id,
            request_id=request_id,
            parent_task_id=parent_task.task_id,
            user_request=user_request,
            planner_result=planner_result,
            final_response=final_response,
        )
        return AgentControlPlaneResult(
            workflow_id=workflow_id,
            request_id=request_id,
            parent_task_id=parent_task.task_id,
            planner_result=planner_result,
            child_task_ids=tuple(task.task_id for task in (planner_task, *child_tasks)),
            agent_results=agent_results,
            final_response=final_response,
            audit_id=audit_id,
        )

    def _ensure_workflow_record(
        self,
        *,
        workflow_id: str,
        objective: str,
        request_id: str,
        task_class: str,
    ) -> None:
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
                    task_class,
                    "paper",
                    "MODE-002",
                    "CREATED",
                    objective,
                    json.dumps({"request_id": request_id}, sort_keys=True),
                    "user",
                    "operator",
                    "{}",
                    "[]",
                ),
            )

    def _create_child_tasks(
        self,
        *,
        parent_task_id: str,
        planner_result: ConversationPlan,
    ) -> tuple[Any, ...]:
        child_tasks = []
        for agent_name in planner_result.allowed_agents:
            descriptor = self.registry.require(agent_name)
            required_tools = tuple(
                tool
                for tool in planner_result.backend_tools_to_run
                if tool in descriptor.allowed_tools
            )
            child_tasks.append(
                self.task_manager.create_child_task(
                    parent_task_id=parent_task_id,
                    title=f"{descriptor.role} task",
                    description=f"Produce {descriptor.role} output for: {planner_result.user_goal}",
                    owner_agent=descriptor.agent_name,
                    expected_output_contract="AgentRunResult",
                    required_tools=required_tools,
                    metadata={
                        "planner_result_id": planner_result.conversation_plan_id,
                        "expected_outputs": planner_result.expected_outputs,
                    },
                )
            )
        return tuple(child_tasks)

    def _dispatch_child_tasks(
        self,
        *,
        workflow_id: str,
        request_id: str,
        parent_task_id: str,
        planner_result: ConversationPlan,
        child_tasks: tuple[Any, ...],
    ) -> tuple[AgentRunResult, ...]:
        results: list[AgentRunResult] = []
        for task in child_tasks:
            self.task_manager.assign_task(task.task_id, owner_agent=task.owner_agent, actor_id="planner")
            self.task_manager.start_task(task.task_id, actor_id=task.owner_agent)
            agent = self.registry.create_agent(task.owner_agent)
            result = agent.run(
                context=AgentRunContext(
                    workflow_id=workflow_id,
                    task_id=task.task_id,
                    parent_task_id=parent_task_id,
                    request_id=request_id,
                    user_request=planner_result.user_goal,
                    metadata={"planner_result_id": planner_result.conversation_plan_id},
                ),
                task_input={
                    "title": task.title,
                    "description": task.description,
                    "required_tools": json.loads(task.required_tools_json),
                    "evidence_requirements": planner_result.evidence_requirements,
                },
            )
            if result.status == "completed":
                self.task_manager.complete_task(
                    task.task_id,
                    actor_id=task.owner_agent,
                    output=result.output,
                )
            else:
                self.task_manager.fail_task(
                    task.task_id,
                    actor_id=task.owner_agent,
                    reason=result.error or "agent failed",
                )
            results.append(result)
        return tuple(results)

    @staticmethod
    def _produce_final_response(
        *,
        user_request: str,
        planner_result: ConversationPlan,
        agent_results: tuple[AgentRunResult, ...],
    ) -> dict[str, Any]:
        return {
            "request": user_request,
            "plan": planner_result.model_dump(mode="json"),
            "agents_consulted": [result.agent_name for result in agent_results],
            "completed_agents": [
                result.agent_name for result in agent_results if result.status == "completed"
            ],
            "failed_agents": [
                result.agent_name for result in agent_results if result.status != "completed"
            ],
            "evidence_validated": True,
            "summary": "Firm control plane completed delegated Phase 6 workflow.",
        }

    def _write_audit_record(
        self,
        *,
        workflow_id: str,
        request_id: str,
        parent_task_id: str,
        user_request: str,
        planner_result: ConversationPlan,
        final_response: dict[str, Any],
    ) -> str | None:
        repository = self.task_manager.repository
        if repository is None:
            return None
        audit_id = f"audit-{uuid4().hex}"
        repository.append_audit_log(
            audit_id=audit_id,
            actor_name="ceo",
            agent_name="ceo",
            action_type="agent_control_plane_run",
            target_type="agent_task",
            target_ref_id=parent_task_id,
            input_hash=_hash_payload({"request": user_request, "plan": planner_result.model_dump(mode="json")}),
            output_hash=_hash_payload(final_response),
            request_id=request_id,
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            metadata_json=json.dumps({"phase": "6", "planner_source": planner_result.planner_source}, sort_keys=True),
        )
        return audit_id


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AgentControlPlaneOrchestrator",
    "AgentControlPlaneResult",
    "DefaultFirmPlanner",
]
