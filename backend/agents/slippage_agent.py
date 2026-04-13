"""Slippage sub-agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.slippage_template import SLIPPAGE_AGENT_INSTRUCTION
from .runtime import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime, CanonicalOutputValidator


@dataclass(frozen=True)
class SlippageAgentWrapper:
    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "slippage_agent"
    instruction: str = SLIPPAGE_AGENT_INSTRUCTION

    def execute(self, *, runtime_agent: AgentRuntime, request: ADKRunRequest) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "ObservationEvent":
            raise ValueError("SlippageAgent must emit ObservationEvent outputs")
        return result
