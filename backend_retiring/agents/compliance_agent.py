"""Compliance agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.compliance_template import COMPLIANCE_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


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
