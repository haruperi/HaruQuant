"""Monitoring agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.monitoring_template import MONITORING_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


@dataclass(frozen=True)
class MonitoringAgentWrapper:
    """Thin wrapper that validates monitoring outputs as IncidentAlert."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "monitoring_agent"
    instruction: str = MONITORING_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "IncidentAlert":
            raise ValueError("MonitoringAgent must emit IncidentAlert outputs")
        return result
