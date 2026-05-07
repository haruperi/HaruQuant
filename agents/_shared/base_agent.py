"""Shared base agent interfaces and deterministic runtime envelope."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agents._shared.base_contracts import (
    AgentContext,
    AgentDecision,
    AgentRequest,
    AgentResponse,
    AgentRunResult,
    EvidenceItem,
    LLMAnalysis,
)


class HaruQuantAgentService(ABC):
    agent_name: str

    @abstractmethod
    async def run(self, request: AgentRequest, context: AgentContext) -> AgentResponse:
        pass

    @abstractmethod
    def gather_evidence(self, request: AgentRequest, context: AgentContext) -> list[EvidenceItem]:
        pass

    @abstractmethod
    async def run_llm_analysis(
        self,
        request: AgentRequest,
        context: AgentContext,
        evidence: list[EvidenceItem],
    ) -> LLMAnalysis | None:
        pass

    @abstractmethod
    def make_deterministic_decision(
        self,
        request: AgentRequest,
        context: AgentContext,
        evidence: list[EvidenceItem],
        llm_analysis: LLMAnalysis | None,
    ) -> AgentDecision:
        pass


class AgentBase:
    """Common plan -> act -> observe -> evaluate -> finalize envelope."""

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
            return AgentRunResult(agent_name=self.agent_name, status="failed", failure_reason=str(exc))

    def plan(self, task: Any, context: dict[str, Any]) -> dict[str, Any]:
        return {"task_id": getattr(task, "task_id", None), "context": context}

    def act(self, task: Any, context: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        return {"plan": plan, "allowed_tools": list(self.allowed_tools)}

    def observe(self, task: Any, context: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
        return {"action": action, "observation": "completed deterministic agent step"}

    def evaluate(self, task: Any, context: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
        return {"observation": observation, "status": "completed"}

    def finalize(self, task: Any, context: dict[str, Any], evaluation: dict[str, Any]) -> AgentRunResult:
        task_id = getattr(task, "task_id", None)
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output={"task_id": task_id, "role": self.role, "evaluation": evaluation},
            observations=[{"task_id": task_id, "agent_name": self.agent_name, "summary": f"{self.agent_name} completed assigned work."}],
            decisions=[{"task_id": task_id, "agent_name": self.agent_name, "decision": "completed", "rationale": "Deterministic agent run."}],
        )


__all__ = ["AgentBase", "HaruQuantAgentService"]
