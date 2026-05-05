"""Dynamic orchestrator-workers workflow pattern.

The orchestrator receives a goal, plans task decomposition, dispatches
workers in parallel, and synthesizes their outputs into a coherent result.
Unlike the static OrchestratorWorkerWorkflowRunner which accepts a
pre-built task list, this runner uses an AI agent to dynamically plan
and delegate work.
"""

from __future__ import annotations

from services.utils.logger import logger
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
)
from .workflows import ParallelWorkflowRunner, ParallelWorkflowTask


@dataclass(frozen=True)
class OrchestratorPlan:
    """Plan produced by the orchestrator agent."""
    workflow_id: str
    tasks: tuple[Dict[str, Any], ...]  # Each: {task_name, agent_name, input_payload}
    synthesis_instructions: str = ""
    confidence: float = 0.0
    reasoning: str = ""


@dataclass(frozen=True)
class DynamicOrchestratorResult:
    """Result from a dynamic orchestrator-workers workflow run."""
    plan: OrchestratorPlan
    worker_results: Dict[str, ADKRunResult] = field(default_factory=dict)
    synthesized_output: Dict[str, Any] = field(default_factory=dict)
    failed_workers: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    final_state: str = "COMPLETED"


class DynamicOrchestratorWorkerRunner:
    """Dynamic orchestrator that plans, dispatches, and synthesizes.

    Usage:
        runner = DynamicOrchestratorWorkerRunner(
            adk_runner=ADKRunnerService(...),
            orchestrator_agent=orchestrator_llm,
        )
        result = runner.run(
            goal="Analyze EURUSD and generate a trade plan",
            available_workers={
                "research_agent": {"input": {"symbol": "EURUSD"}},
                "strategy_agent": {"input": {"symbol": "EURUSD"}},
                "compliance_agent": {"input": {"risk_class": "C"}},
            },
        )
    """

    def __init__(
        self,
        adk_runner: ADKRunnerService,
        orchestrator_agent: AgentRuntime,
    ) -> None:
        self._adk_runner = adk_runner
        self._orchestrator = orchestrator_agent

    def run(
        self,
        *,
        goal: str,
        available_workers: Dict[str, Dict[str, Any]],
        workflow_id: str = "wf-dynamic-orchestrator",
        correlation_id: str = "corr-dynamic-orchestrator",
        agent_name: str = "orchestrator_agent",
    ) -> DynamicOrchestratorResult:
        """Execute dynamic orchestrator-workers workflow.

        1. Send goal to orchestrator agent for planning
        2. Parse the plan (task decomposition with worker assignments)
        3. Dispatch workers in parallel
        4. Synthesize worker outputs into final result
        """
        # Step 1: Get orchestration plan from AI agent
        plan = self._generate_plan(
            goal=goal,
            available_workers=available_workers,
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            agent_name=agent_name,
        )

        # Step 2: Dispatch workers in parallel
        worker_results = self._dispatch_workers(
            plan=plan,
            available_workers=available_workers,
            workflow_id=workflow_id,
            correlation_id=correlation_id,
        )

        # Step 3: Synthesize results
        synthesized, failed, conflicts = self._synthesize(
            plan=plan,
            worker_results=worker_results,
        )

        return DynamicOrchestratorResult(
            plan=plan,
            worker_results=worker_results,
            synthesized_output=synthesized,
            failed_workers=tuple(failed),
            conflicts=tuple(conflicts),
            final_state="COMPLETED" if not failed else "PARTIAL_FAILURE",
        )

    def _generate_plan(
        self,
        *,
        goal: str,
        available_workers: Dict[str, Dict[str, Any]],
        workflow_id: str,
        correlation_id: str,
        agent_name: str,
    ) -> OrchestratorPlan:
        """Ask the orchestrator agent to generate a task decomposition plan."""
        worker_names = list(available_workers.keys())
        plan_request = ADKRunRequest(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            agent_name=agent_name,
            input_payload={
                "goal": goal,
                "available_workers": worker_names,
                "instruction": (
                    f"You are a workflow orchestrator. Given a goal and a list of "
                    f"available worker agents, decompose the goal into parallel tasks. "
                    f"Return a JSON plan with this exact schema:\n"
                    f'{{"tasks": [{{"task_name": "...", "agent_name": "...", "input_payload": {{...}}}}], '
                    f'"synthesis_instructions": "...", "confidence": 0.0, "reasoning": "..."}}\n\n'
                    f"Goal: {goal}\n"
                    f"Available workers: {', '.join(worker_names)}"
                ),
            },
        )
        context = AgentExecutionContext(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            session_id=None,
            model="dynamic-orchestrator",
            allowed_tools=(),
            prompt_version_id=None,
            metadata={},
        )

        result = self._orchestrator.run(request=plan_request, context=context)
        payload = result.output_payload

        # Parse plan from response
        tasks_data = payload.get("tasks", [])
        if not isinstance(tasks_data, (list, tuple)):
            # Fallback: create tasks for all available workers
            tasks_data = [
                {
                    "task_name": f"{agent_name}_task",
                    "agent_name": agent_name,
                    "input_payload": worker_info.get("input", {}),
                }
                for agent_name, worker_info in available_workers.items()
            ]

        tasks = tuple(
            {
                "task_name": str(t.get("task_name", f"task_{i}")),
                "agent_name": str(t.get("agent_name", "unknown")),
                "input_payload": t.get("input_payload", {}),
            }
            for i, t in enumerate(tasks_data)
        )

        return OrchestratorPlan(
            workflow_id=workflow_id,
            tasks=tasks,
            synthesis_instructions=str(payload.get("synthesis_instructions", "")),
            confidence=float(payload.get("confidence", 0.5)),
            reasoning=str(payload.get("reasoning", "")),
        )

    def _dispatch_workers(
        self,
        *,
        plan: OrchestratorPlan,
        available_workers: Dict[str, Dict[str, Any]],
        workflow_id: str,
        correlation_id: str,
    ) -> Dict[str, ADKRunResult]:
        """Dispatch worker tasks in parallel and collect results."""
        parallel_runner = ParallelWorkflowRunner(self._adk_runner)

        tasks = []
        for task_info in plan.tasks:
            task_name = task_info["task_name"]
            agent_name = task_info["agent_name"]
            worker_config = available_workers.get(agent_name, {})

            # Create a runtime agent for this worker
            worker_agent = self._adk_runner  # Use ADKRunnerService as the agent

            tasks.append(
                ParallelWorkflowTask(
                    task_name=task_name,
                    runtime_agent=worker_agent,
                    request=ADKRunRequest(
                        workflow_id=workflow_id,
                        correlation_id=f"{correlation_id}-{task_name}",
                        agent_name=agent_name,
                        input_payload={
                            **task_info.get("input_payload", {}),
                            **worker_config.get("input", {}),
                            "_orchestrator_goal": plan.synthesis_instructions,
                            "_peer_tasks": [t["task_name"] for t in plan.tasks if t["task_name"] != task_name],
                        },
                    ),
                )
            )

        aggregate = parallel_runner.run(tasks=tuple(tasks))
        return dict(aggregate.results)

    def _synthesize(
        self,
        *,
        plan: OrchestratorPlan,
        worker_results: Dict[str, ADKRunResult],
    ) -> tuple[Dict[str, Any], List[str], List[str]]:
        """Synthesize worker outputs into a coherent final result.

        Returns:
            (synthesized_output, failed_workers, conflicts)
        """
        failed_workers: List[str] = []
        conflicts: List[str] = []
        combined: Dict[str, Any] = {}

        for task_name, result in worker_results.items():
            if result.final_state != "COMPLETED":
                failed_workers.append(task_name)
                combined[task_name] = {
                    "status": result.final_state,
                    "error": result.output_payload.get("error", "Unknown error"),
                }
            else:
                combined[task_name] = result.output_payload

        # Detect conflicts (different workers producing conflicting values for same key)
        seen: Dict[str, Any] = {}
        for task_name, payload in combined.items():
            if not isinstance(payload, dict):
                continue
            for key, value in payload.items():
                if key in {"contract_type", "schema_version", "error", "status"}:
                    continue
                if key in seen and seen[key] != value:
                    conflicts.append(f"{key}:{task_name}")
                else:
                    seen[key] = value

        synthesized = {
            "plan_confidence": plan.confidence,
            "synthesis_instructions": plan.synthesis_instructions,
            "worker_count": len(worker_results),
            "failed_count": len(failed_workers),
            "conflict_count": len(conflicts),
            "combined_results": combined,
        }

        return synthesized, failed_workers, conflicts
