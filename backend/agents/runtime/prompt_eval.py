"""Prompt evaluation harness for golden, adversarial, and regression tasks."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from backend.common.logger import logger
from .runner import ADKRunRequest, ADKRunnerService, AgentRuntime


@dataclass(frozen=True)
class PromptEvalCase:
    """One prompt evaluation fixture case."""

    category: str
    name: str
    input_payload: dict[str, Any]
    expected: dict[str, Any]


@dataclass(frozen=True)
class PromptEvalCaseResult:
    """Result for one executed prompt evaluation case."""

    case_name: str
    category: str
    passed: bool
    final_state: str
    reason: str


@dataclass(frozen=True)
class PromptEvalReport:
    """Aggregate prompt evaluation report."""

    prompt_version_id: str | None
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: tuple[PromptEvalCaseResult, ...]

    @property
    def passed(self) -> bool:
        return self.failed_cases == 0


def load_prompt_eval_cases(eval_dir: Path) -> tuple[PromptEvalCase, ...]:
    """Load newline-delimited JSON eval cases from a standard eval directory."""
    cases: list[PromptEvalCase] = []
    for category in ("golden_tasks", "adversarial_tasks", "regression_tasks", "domain_hard_cases"):
        category_dir = eval_dir / category
        if not category_dir.exists():
            continue
        for path in sorted(category_dir.glob("*.json")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                cases.append(
                    PromptEvalCase(
                        category=category,
                        name=str(raw["name"]),
                        input_payload=dict(raw.get("input", {})),
                        expected=dict(raw.get("expected", {})),
                    )
                )
    return tuple(cases)


class PromptEvalHarness:
    """Execute prompt eval cases through the agent runner."""

    def __init__(
        self,
        *,
        runner: ADKRunnerService,
        runtime_agent: AgentRuntime,
        agent_name: str,
    ) -> None:
        self._runner = runner
        self._runtime_agent = runtime_agent
        self._agent_name = agent_name

    def run_cases(
        self,
        *,
        cases: tuple[PromptEvalCase, ...],
        prompt_version_id: str | None = None,
    ) -> PromptEvalReport:
        results: list[PromptEvalCaseResult] = []
        for index, case in enumerate(cases, 1):
            result = self._runner.run(
                agent=self._runtime_agent,
                request=ADKRunRequest(
                    workflow_id=f"eval_wf_{index}",
                    correlation_id=f"eval_corr_{index}",
                    agent_name=self._agent_name,
                    input_payload=case.input_payload,
                    prompt_version_id=prompt_version_id,
                    metadata={"eval_category": case.category, "eval_case": case.name},
                ),
            )
            passed, reason = _case_passed(case.expected, result.output_payload, result.final_state)
            results.append(
                PromptEvalCaseResult(
                    case_name=case.name,
                    category=case.category,
                    passed=passed,
                    final_state=result.final_state,
                    reason=reason,
                )
            )
        passed_count = sum(1 for item in results if item.passed)
        return PromptEvalReport(
            prompt_version_id=prompt_version_id,
            total_cases=len(results),
            passed_cases=passed_count,
            failed_cases=len(results) - passed_count,
            case_results=tuple(results),
        )


def _case_passed(
    expected: dict[str, Any],
    output_payload: dict[str, Any],
    final_state: str,
) -> tuple[bool, str]:
    if expected.get("should_reject") is True:
        rejected = final_state != "COMPLETED" or output_payload.get("rejected") is True or "error" in output_payload
        return rejected, "expected rejection" if rejected else "unsafe case was not rejected"
    if expected.get("should_escalate") is True:
        escalated = output_payload.get("escalated") is True or final_state in {"ESCALATED", "ERROR"}
        return escalated, "expected escalation" if escalated else "case was not escalated"
    for key, value in expected.items():
        if key.endswith("_min"):
            actual_key = key.removesuffix("_min")
            if float(output_payload.get(actual_key, 0.0)) < float(value):
                return False, f"{actual_key} below minimum"
            continue
        if key in output_payload and output_payload[key] != value:
            return False, f"{key} mismatch"
    return final_state == "COMPLETED", "completed" if final_state == "COMPLETED" else final_state
