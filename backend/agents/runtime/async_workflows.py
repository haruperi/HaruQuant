"""Async workflow runners for true I/O concurrency.

Uses asyncio.gather() for parallel task execution instead of
ThreadPoolExecutor, providing better concurrency for I/O-bound
LLM calls that are not limited by Python's GIL.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple


class AsyncAgentRuntime(Protocol):
    """Async version of AgentRuntime."""
    async def run_async(
        self,
        *,
        request: Any,
        context: Any,
    ) -> Any: ...


@dataclass(frozen=True)
class AsyncParallelWorkflowTask:
    """One task in an async parallel workflow."""
    task_name: str
    runtime_agent: AsyncAgentRuntime
    request: Any
    timeout_seconds: Optional[float] = None
    critical: bool = True


@dataclass(frozen=True)
class AsyncParallelResult:
    """Fan-in result for async parallel workflow."""
    results: Dict[str, Any]
    timed_out_tasks: Tuple[str, ...] = ()
    failed_tasks: Tuple[str, ...] = ()

    @property
    def successful_tasks(self) -> Tuple[str, ...]:
        return tuple(
            name for name, result in self.results.items()
            if getattr(result, "final_state", None) == "COMPLETED"
        )


class AsyncParallelWorkflowRunner:
    """Execute independent tasks concurrently using asyncio.gather().

    Provides true async concurrency for I/O-bound LLM calls,
    avoiding the GIL limitations of ThreadPoolExecutor.

    Usage:
        runner = AsyncParallelWorkflowRunner()
        result = await runner.run(tasks=(
            AsyncParallelWorkflowTask(
                task_name="research",
                runtime_agent=async_agent,
                request=request,
                timeout_seconds=60.0,
            ),
        ))
    """

    async def run(
        self,
        *,
        tasks: Tuple[AsyncParallelWorkflowTask, ...],
    ) -> AsyncParallelResult:
        if not tasks:
            return AsyncParallelResult(results={})

        async def _run_task(task: AsyncParallelWorkflowTask) -> Any:
            try:
                if task.timeout_seconds is not None:
                    return await asyncio.wait_for(
                        task.runtime_agent.run_async(request=task.request, context=None),
                        timeout=task.timeout_seconds,
                    )
                return await task.runtime_agent.run_async(request=task.request, context=None)
            except asyncio.TimeoutError:
                return {"error": f"Task {task.task_name} timed out", "final_state": "TIMED_OUT"}
            except Exception as exc:
                return {"error": str(exc), "final_state": "FAILED"}

        coroutines = [_run_task(task) for task in tasks]
        raw_results = await asyncio.gather(*coroutines, return_exceptions=True)

        results: Dict[str, Any] = {}
        timed_out: List[str] = []
        failed: List[str] = []

        for task, raw in zip(tasks, raw_results):
            if isinstance(raw, Exception):
                failed.append(task.task_name)
                results[task.task_name] = {"error": str(raw), "final_state": "FAILED"}
            elif isinstance(raw, dict) and raw.get("final_state") == "TIMED_OUT":
                timed_out.append(task.task_name)
                results[task.task_name] = raw
            elif isinstance(raw, dict) and raw.get("final_state") == "FAILED":
                failed.append(task.task_name)
                results[task.task_name] = raw
            else:
                results[task.task_name] = raw

        return AsyncParallelResult(
            results=results,
            timed_out_tasks=tuple(timed_out),
            failed_tasks=tuple(failed),
        )


@dataclass(frozen=True)
class AsyncSequentialResult:
    """Result from async sequential workflow."""
    results: Tuple[Any, ...]
    final_state: str = "COMPLETED"


class AsyncSequentialWorkflowRunner:
    """Execute workflow steps sequentially using async/await.

    Each step receives prior step outputs in request metadata.

    Usage:
        runner = AsyncSequentialWorkflowRunner()
        result = await runner.run(steps=(
            AsyncSequentialWorkflowStep(
                step_name="research",
                runtime_agent=async_agent,
                request=request,
            ),
        ))
    """

    async def run(
        self,
        *,
        steps: Tuple["AsyncSequentialWorkflowStep", ...],
    ) -> AsyncSequentialResult:
        from dataclasses import replace

        results: List[Any] = []
        context_chain: Dict[str, Any] = {}

        for step in steps:
            augmented_request = replace(
                step.request,
                metadata={
                    **step.request.metadata,
                    "prior_steps": dict(context_chain),
                },
            )
            result = await step.runtime_agent.run_async(
                request=augmented_request,
                context=None,
            )
            context_chain[step.step_name] = {
                "output": getattr(result, "output_payload", result),
                "state": getattr(result, "final_state", "UNKNOWN"),
            }
            results.append(result)

            if getattr(result, "final_state", "COMPLETED") != "COMPLETED":
                return AsyncSequentialResult(
                    results=tuple(results),
                    final_state="FAILED",
                )

        return AsyncSequentialResult(results=tuple(results))


@dataclass(frozen=True)
class AsyncSequentialWorkflowStep:
    """One step in an async sequential workflow."""
    step_name: str
    runtime_agent: AsyncAgentRuntime
    request: Any
