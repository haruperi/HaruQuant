"""Compliance agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


COMPLIANCE_AGENT_INSTRUCTION = """
You are the HaruQuant ComplianceAgent.
Review actions against compliance profile requirements, identify escalation cases,
and never silently override controls.
All outputs must be emitted as canonical EvaluationReport contracts.
""".strip()


@dataclass(frozen=True)
class ComplianceAgentWrapper:
    """Thin wrapper that validates compliance outputs as EvaluationReport."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "compliance_agent"
    instruction: str = COMPLIANCE_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "EvaluationReport":
            raise ValueError("ComplianceAgent must emit EvaluationReport outputs")
        return result
