"""Base agent contract for the HaruQuant Agentic Firm control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend_retiring.agents.permissions import AgentToolPermissionService, get_default_permission_service


@dataclass(frozen=True)
class AgentRunContext:
    """Execution context shared by firm agents."""

    workflow_id: str
    task_id: str
    parent_task_id: str | None = None
    request_id: str | None = None
    user_request: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentRunResult:
    """Standard result returned by all control-plane agents."""

    agent_name: str
    task_id: str
    status: str
    output: dict[str, Any]
    observations: tuple[dict[str, Any], ...] = ()
    decisions: tuple[dict[str, Any], ...] = ()
    tool_calls: tuple[dict[str, Any], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error: str | None = None


class AgentRunError(RuntimeError):
    """Raised when a firm agent cannot complete its assigned task."""


class BaseAgent:
    """Template-method base class for firm-managed agents.

    Phase 6 keeps this deterministic and lightweight. Later phases can override
    `plan`, `act`, `observe`, `evaluate`, or `finalize` while preserving the
    same task, permission, and audit envelope.
    """

    agent_name: str = "base"
    role: str = "base"
    allowed_tools: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        permission_service: AgentToolPermissionService | None = None,
    ) -> None:
        self.permission_service = permission_service or get_default_permission_service()

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        try:
            plan = self.plan(context=context, task_input=task_input)
            action = self.act(context=context, task_input=task_input, plan=plan)
            observation = self.observe(context=context, task_input=task_input, action=action)
            evaluation = self.evaluate(
                context=context,
                task_input=task_input,
                observation=observation,
            )
            return self.finalize(
                context=context,
                task_input=task_input,
                plan=plan,
                action=action,
                observation=observation,
                evaluation=evaluation,
            )
        except Exception as exc:  # pragma: no cover - defensive runtime envelope
            return AgentRunResult(
                agent_name=self.agent_name,
                task_id=context.task_id,
                status="failed",
                output={"error": str(exc), "role": self.role},
                error=str(exc),
            )

    def plan(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "task_id": context.task_id,
            "allowed_tools": tuple(self.allowed_tools),
            "objective": task_input.get("description") or task_input.get("title"),
        }

    def act(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        requested_tools = tuple(task_input.get("required_tools") or ())
        approved_tools: list[str] = []
        for tool_name in requested_tools:
            decision = self.permission_service.evaluate(
                agent_name=self.agent_name,
                tool_name=str(tool_name),
                has_human_approval=bool(task_input.get("has_human_approval")),
                has_risk_governor_approval=bool(task_input.get("has_risk_governor_approval")),
            )
            if not decision.allowed:
                raise AgentRunError(
                    f"tool '{tool_name}' denied for {self.agent_name}: {decision.reason}"
                )
            approved_tools.append(str(tool_name))
        return {"approved_tools": tuple(approved_tools), "plan": plan}

    def observe(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "observation_type": "control_plane_progress",
            "summary": f"{self.agent_name} accepted task {context.task_id}.",
            "action": action,
        }

    def evaluate(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        missing_evidence = tuple(task_input.get("evidence_requirements") or ())
        return {
            "verdict": "requires_evidence" if missing_evidence else "complete",
            "missing_evidence": missing_evidence,
            "observation_summary": observation.get("summary"),
        }

    def finalize(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
        plan: dict[str, Any],
        action: dict[str, Any],
        observation: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.agent_name,
            task_id=context.task_id,
            status="completed",
            output={
                "agent_name": self.agent_name,
                "role": self.role,
                "plan": plan,
                "action": action,
                "evaluation": evaluation,
            },
            observations=(observation,),
            decisions=(
                {
                    "decision_type": "report",
                    "decision": evaluation["verdict"],
                    "rationale": evaluation["observation_summary"],
                },
            ),
            tool_calls=tuple(
                {"tool_name": tool_name, "status": "approved"}
                for tool_name in action.get("approved_tools", ())
            ),
        )


class FirmDepartmentAgent(BaseAgent):
    """Generic department agent used until specialized Phase 7+ agents mature."""

    def __init__(
        self,
        *,
        agent_name: str,
        role: str,
        allowed_tools: tuple[str, ...],
        permission_service: AgentToolPermissionService | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.role = role
        self.allowed_tools = allowed_tools
        super().__init__(permission_service=permission_service)


__all__ = [
    "AgentRunContext",
    "AgentRunError",
    "AgentRunResult",
    "BaseAgent",
    "FirmDepartmentAgent",
]
