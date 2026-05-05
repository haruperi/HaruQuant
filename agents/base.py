"""Base agent runtime envelope for the HaruQuant control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentRunResult:
    agent_name: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    failure_reason: str | None = None


class AgentBase:
    """Common `plan -> act -> observe -> evaluate -> finalize` envelope."""

    agent_name = "agent"
    role = "Generic agent"
    allowed_tools: tuple[str, ...] = ()

    def run(self, task: Any, context: dict[str, Any] | None = None) -> AgentRunResult:
        context = context or {}
        try:
            plan = self.plan(task, context)
            action = self.act(task, context, plan)
            observation = self.observe(task, context, action)
            evaluation = self.evaluate(task, context, observation)
            return self.finalize(task, context, evaluation)
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            return AgentRunResult(
                agent_name=self.agent_name,
                status="failed",
                failure_reason=str(exc),
            )

    def plan(self, task: Any, context: dict[str, Any]) -> dict[str, Any]:
        return {"task_id": getattr(task, "task_id", None), "context": context}

    def act(
        self,
        task: Any,
        context: dict[str, Any],
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        return {"plan": plan, "allowed_tools": list(self.allowed_tools)}

    def observe(
        self,
        task: Any,
        context: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        return {"action": action, "observation": "completed deterministic agent step"}

    def evaluate(
        self,
        task: Any,
        context: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        return {"observation": observation, "status": "completed"}

    def finalize(
        self,
        task: Any,
        context: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> AgentRunResult:
        task_id = getattr(task, "task_id", None)
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output={
                "task_id": task_id,
                "role": self.role,
                "evaluation": evaluation,
            },
            observations=[
                {
                    "task_id": task_id,
                    "agent_name": self.agent_name,
                    "summary": f"{self.agent_name} completed assigned work.",
                }
            ],
            decisions=[
                {
                    "task_id": task_id,
                    "agent_name": self.agent_name,
                    "decision": "completed",
                    "rationale": "Deterministic Phase 6 control-plane agent run.",
                }
            ],
        )
