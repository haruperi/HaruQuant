"""Hypothesis Designer agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.strategy_blueprint.model import StrategyBlueprint
from backend.services.strategy.design import StrategyBlueprintValidator

from .prompts.hypothesis_designer_template import HYPOTHESIS_DESIGNER_AGENT_INSTRUCTION
from .runtime import ADKRunRequest, ADKRunResult, ADKRunnerService, AgentRuntime


@dataclass(frozen=True)
class HypothesisDesignerAgentWrapper:
    """Thin wrapper that normalizes and validates StrategyBlueprint outputs."""

    runner: ADKRunnerService
    blueprint_validator: StrategyBlueprintValidator

    agent_name: str = "hypothesis_designer_agent"
    instruction: str = HYPOTHESIS_DESIGNER_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        normalized = self.blueprint_validator.normalize_candidate(
            result.output_payload,
            source_idea=str(request.input_payload.get("idea", request.input_payload.get("task", ""))),
        )
        validated = StrategyBlueprint.model_validate(normalized)
        if validated.contract_type != "StrategyBlueprint":
            raise ValueError("HypothesisDesignerAgent must emit StrategyBlueprint outputs")
        return ADKRunResult(
            runner_name=result.runner_name,
            runtime_version=result.runtime_version,
            agent_name=result.agent_name,
            workflow_id=result.workflow_id,
            correlation_id=result.correlation_id,
            session_id=result.session_id,
            model=result.model,
            prompt_version_id=result.prompt_version_id,
            prompt_hash=result.prompt_hash,
            latency_ms=result.latency_ms,
            output_payload=validated.model_dump(mode="json"),
            final_state=result.final_state,
            tool_calls=result.tool_calls,
            token_usage=result.token_usage,
            repair_attempted=result.repair_attempted,
            repair_succeeded=result.repair_succeeded,
            validation_error=result.validation_error,
            redacted_paths=result.redacted_paths,
            retrieval_safety=result.retrieval_safety,
        )
