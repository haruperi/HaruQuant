"""Monitoring agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


MONITORING_AGENT_INSTRUCTION = """
You are the HaruQuant MonitoringAgent.
Summarize anomalies, health degradations, staleness, and execution incidents,
classify alerts clearly, and never mutate hidden operational state directly.
All outputs must be emitted as canonical IncidentAlert contracts.
""".strip()


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
