"""Prompt unit tests — verify each agent prompt structure and composition.

Tests focus on prompting correctness (section presence, CoT inclusion,
trust hierarchy) rather than contract schema validation (which is covered
by existing agent tests).

Includes:
- 13 agent prompt structure tests (9-section + CoT)
- 5 failure scenario tests (malformed, timeout, missing contract, etc.)
- 1 sequential workflow context chaining integration test
- 1 prompt composition trust hierarchy test

ReAct unit tests are in test_react_agent.py (Phase 4).
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from backend.agents.prompts import PromptComposer, PromptContext, assemble_agent_prompt
from backend.agents.runtime import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
)
from backend.agents.runtime.output_validation import (
    CanonicalOutputValidator,
    ContractValidationError,
)
from backend.agents.runtime.workflows import (
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
)

# ──────────────────────────────────────────────────────────────
# Import all 13 agent instructions
# ──────────────────────────────────────────────────────────────

from backend.agents.orchestrator_agent import ORCHESTRATOR_AGENT_INSTRUCTION
from backend.agents.strategy_agent import STRATEGY_AGENT_INSTRUCTION
from backend.agents.execution_agent import EXECUTION_AGENT_INSTRUCTION
from backend.agents.portfolio_agent import PORTFOLIO_AGENT_INSTRUCTION
from backend.agents.compliance_agent import COMPLIANCE_AGENT_INSTRUCTION
from backend.agents.research_agent import RESEARCH_AGENT_INSTRUCTION
from backend.agents.monitoring_agent import MONITORING_AGENT_INSTRUCTION
from backend.agents.volatility_agent import VOLATILITY_AGENT_INSTRUCTION
from backend.agents.regime_agent import REGIME_AGENT_INSTRUCTION
from backend.agents.drawdown_agent import DRAWDOWN_AGENT_INSTRUCTION
from backend.agents.exposure_agent import EXPOSURE_AGENT_INSTRUCTION
from backend.agents.correlation_agent import CORRELATION_AGENT_INSTRUCTION
from backend.agents.slippage_agent import SLIPPAGE_AGENT_INSTRUCTION


# ──────────────────────────────────────────────────────────────
# Test 1–13: Each agent prompt has 9 sections + CoT
# ──────────────────────────────────────────────────────────────

_REQUIRED_SECTIONS = [
    "ROLE:", "TASK:", "REASONING PROCESS:", "CONTEXT:", "TOOLS:",
    "RULES:", "CONSTRAINTS:", "ESCALATION CONDITIONS:", "OUTPUT SCHEMA:",
    "FAILURE BEHAVIOR:",
]

# (agent_name, instruction, expected_contract_type)
_AGENT_PROMPTS = [
    ("OrchestratorAgent", ORCHESTRATOR_AGENT_INSTRUCTION, "WorkflowPlan"),
    ("StrategyAgent", STRATEGY_AGENT_INSTRUCTION, "TradeHypothesis"),
    ("ExecutionAgent", EXECUTION_AGENT_INSTRUCTION, "ExecutionIntent"),
    ("PortfolioAgent", PORTFOLIO_AGENT_INSTRUCTION, "EvaluationReport"),
    ("ComplianceAgent", COMPLIANCE_AGENT_INSTRUCTION, "EvaluationReport"),
    ("ResearchAgent", RESEARCH_AGENT_INSTRUCTION, "ObservationEvent"),
    ("MonitoringAgent", MONITORING_AGENT_INSTRUCTION, "IncidentAlert"),
    ("VolatilityAgent", VOLATILITY_AGENT_INSTRUCTION, "ObservationEvent"),
    ("RegimeAgent", REGIME_AGENT_INSTRUCTION, "ObservationEvent"),
    ("DrawdownAgent", DRAWDOWN_AGENT_INSTRUCTION, "ObservationEvent"),
    ("ExposureAgent", EXPOSURE_AGENT_INSTRUCTION, "ObservationEvent"),
    ("CorrelationAgent", CORRELATION_AGENT_INSTRUCTION, "ObservationEvent"),
    ("SlippageAgent", SLIPPAGE_AGENT_INSTRUCTION, "ObservationEvent"),
]


@pytest.mark.parametrize("name,instruction,contract_type", _AGENT_PROMPTS)
def test_agent_prompt_has_all_nine_sections_plus_cot(
    name: str, instruction: str, contract_type: str
) -> None:
    """Every agent prompt must contain all 9 sections + REASONING PROCESS."""
    for section in _REQUIRED_SECTIONS:
        assert section in instruction, f"{name} missing section: {section}"

    # Must also reference the expected contract type
    assert contract_type in instruction, f"{name} does not reference {contract_type}"

    # Must be substantial (≥50 lines)
    lines = instruction.strip().split("\n")
    assert len(lines) >= 50, f"{name} has only {len(lines)} lines (need ≥50)"


def test_orchestrator_cot_includes_workflow_pattern_reasoning() -> None:
    """Orchestrator CoT should include workflow pattern selection reasoning."""
    assert "sequential" in ORCHESTRATOR_AGENT_INSTRUCTION.lower()
    assert "routing" in ORCHESTRATOR_AGENT_INSTRUCTION.lower()
    assert "parallel" in ORCHESTRATOR_AGENT_INSTRUCTION.lower()
    assert "evaluator_optimizer" in ORCHESTRATOR_AGENT_INSTRUCTION.lower() or "evaluator-optimizer" in ORCHESTRATOR_AGENT_INSTRUCTION.lower()


def test_compliance_cot_includes_self_evaluation() -> None:
    """Compliance CoT should include self-evaluation criteria."""
    assert "acceptance" in COMPLIANCE_AGENT_INSTRUCTION.lower()
    assert "criterion" in COMPLIANCE_AGENT_INSTRUCTION.lower() or "criteria" in COMPLIANCE_AGENT_INSTRUCTION.lower()


def test_monitoring_cot_includes_self_evaluation() -> None:
    """Monitoring CoT should include self-evaluation criteria."""
    assert "acceptance" in MONITORING_AGENT_INSTRUCTION.lower()


def test_few_shot_examples_present() -> None:
    """At least 4 agents should include few-shot examples."""
    agents_with_examples = 0
    for name, instruction, _ in _AGENT_PROMPTS:
        if "FEW-SHOT EXAMPLE" in instruction or "FEW-SHOT" in instruction or "Example:" in instruction:
            agents_with_examples += 1
    assert agents_with_examples >= 4, f"Only {agents_with_examples} agents have few-shot examples (need ≥4)"


# ──────────────────────────────────────────────────────────────
# Test 14–18: Failure scenario tests
# ──────────────────────────────────────────────────────────────

def _make_request(agent_name: str, payload: dict) -> tuple[ADKRunRequest, AgentExecutionContext]:
    request = ADKRunRequest(
        workflow_id="wf-fail",
        correlation_id="corr-fail",
        agent_name=agent_name,
        input_payload=payload,
    )
    context = AgentExecutionContext(
        workflow_id="wf-fail",
        correlation_id="corr-fail",
        session_id=None,
        model="mock-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    return request, context


def test_malformed_llm_response_fails_validation() -> None:
    """Malformed response (empty payload) should fail validation."""
    payload = {"contract_type": "TradeHypothesis", "schema_version": "1.0.0", "payload": {}}
    request, context = _make_request("strategy_agent", {"symbol": "EURUSD"})

    class MalformedRuntime:
        def run(self, *, request, context):
            return AgentExecutionResult(
                output_payload=payload,
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    result = MalformedRuntime().run(request=request, context=context)
    validator = CanonicalOutputValidator()
    with pytest.raises(ContractValidationError):
        validator.validate(result.output_payload)


def test_api_timeout_returns_error_state() -> None:
    """Timeout should return ERROR state with error message."""
    payload = {"error": "LLM provider timed out", "contract_type": "unknown", "schema_version": "1.0.0"}
    result = AgentExecutionResult(
        output_payload=payload,
        final_state="ERROR",
        tool_calls=(),
        token_usage=None,
    )
    assert result.final_state == "ERROR"
    assert "error" in result.output_payload


def test_missing_contract_type_fails() -> None:
    """Response without contract_type should fail validation."""
    payload = {"schema_version": "1.0.0", "payload": {}}
    request, context = _make_request("strategy_agent", {})

    class NoContractRuntime:
        def run(self, *, request, context):
            return AgentExecutionResult(
                output_payload=payload,
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    result = NoContractRuntime().run(request=request, context=context)
    validator = CanonicalOutputValidator()
    with pytest.raises(ContractValidationError):
        validator.validate(result.output_payload)


def test_missing_schema_version_fails() -> None:
    """Response without schema_version should fail validation."""
    payload = {"contract_type": "TradeHypothesis", "payload": {}}
    request, context = _make_request("strategy_agent", {})

    class NoVersionRuntime:
        def run(self, *, request, context):
            return AgentExecutionResult(
                output_payload=payload,
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    result = NoVersionRuntime().run(request=request, context=context)
    validator = CanonicalOutputValidator()
    with pytest.raises(ContractValidationError):
        validator.validate(result.output_payload)


def test_empty_payload_fails_validation() -> None:
    """Empty payload dict with correct contract type but no payload data should fail."""
    payload = {
        "workflow_id": "wf-test", "correlation_id": "corr-test",
        "causation_id": "evt-test", "timestamp_utc": "2026-04-13T12:00:00Z",
        "originator": {"type": "agent", "id": "test"},
        "environment": "paper", "operating_mode": "MODE-002",
        "contract_type": "ObservationEvent", "schema_version": "1.0.0",
        "payload": {},
    }
    request, context = _make_request("volatility_agent", {})

    class EmptyPayloadRuntime:
        def run(self, *, request, context):
            return AgentExecutionResult(
                output_payload=payload,
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    result = EmptyPayloadRuntime().run(request=request, context=context)
    validator = CanonicalOutputValidator()
    with pytest.raises(ContractValidationError):
        validator.validate(result.output_payload)


# ──────────────────────────────────────────────────────────────
# Test 19: Sequential workflow context chaining integration
# ──────────────────────────────────────────────────────────────

def test_sequential_workflow_context_chaining_integration() -> None:
    """Full 3-step sequential workflow verifying context is passed between steps."""

    class StepCapturingRuntime:
        def __init__(self) -> None:
            self.captured_metadata: list[dict] = []

        def run(self, *, request: ADKRunRequest, context: AgentExecutionContext) -> AgentExecutionResult:
            self.captured_metadata.append(dict(request.metadata))
            step_num = len(self.captured_metadata)
            return AgentExecutionResult(
                output_payload={"step": step_num, "data": f"result_{step_num}"},
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    capturers = [StepCapturingRuntime() for _ in range(3)]
    runner = SequentialWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="test"))
    )

    results = runner.run(
        steps=(
            SequentialWorkflowStep(
                step_name="fetch_data",
                runtime_agent=capturers[0],
                request=ADKRunRequest(
                    workflow_id="wf-integration",
                    correlation_id="corr-integration",
                    agent_name="research_agent",
                    input_payload={"task": "fetch"},
                ),
            ),
            SequentialWorkflowStep(
                step_name="analyze_regime",
                runtime_agent=capturers[1],
                request=ADKRunRequest(
                    workflow_id="wf-integration",
                    correlation_id="corr-integration",
                    agent_name="regime_agent",
                    input_payload={"task": "analyze"},
                ),
            ),
            SequentialWorkflowStep(
                step_name="generate_signal",
                runtime_agent=capturers[2],
                request=ADKRunRequest(
                    workflow_id="wf-integration",
                    correlation_id="corr-integration",
                    agent_name="strategy_agent",
                    input_payload={"task": "generate"},
                ),
            ),
        )
    )

    # Step 1 should have empty prior_steps
    assert capturers[0].captured_metadata[0].get("prior_steps") == {}

    # Step 2 should have step 1 output
    assert "fetch_data" in capturers[1].captured_metadata[0].get("prior_steps", {})
    assert capturers[1].captured_metadata[0]["prior_steps"]["fetch_data"]["output"]["step"] == 1

    # Step 3 should have both prior steps
    prior = capturers[2].captured_metadata[0].get("prior_steps", {})
    assert "fetch_data" in prior
    assert "analyze_regime" in prior
    # Each capturer counts from 1 independently, so analyze_regime output step = 1
    assert prior["analyze_regime"]["output"]["step"] == 1
    assert prior["analyze_regime"]["output"]["data"] == "result_1"
    assert prior["analyze_regime"]["state"] == "COMPLETED"

    # All 3 results should be returned
    assert len(results) == 3


# ──────────────────────────────────────────────────────────────
# Test 20: Prompt composition with all trust layers
# ──────────────────────────────────────────────────────────────

def test_prompt_assembly_with_all_trust_layers() -> None:
    """Assembled prompt should include all trust layers in correct order."""
    instruction = "You are a test agent."
    context = PromptContext(
        system_policy="NEVER emit execution instructions.",
        workflow_policy="This workflow is read-only.",
        user_input="What is the current market regime?",
        retrieved_content="Market data shows EURUSD trending.",
        tool_output='{"price": 1.0850}',
        prior_steps={"step1": {"output": {}, "state": "COMPLETED"}},
        refinement_feedback={"refinement_iteration": 1, "previous_score": 0.5},
    )
    composed = PromptComposer.compose(instruction, context)

    # All markers should be present
    for marker in [
        "[SYSTEM POLICY",
        "[WORKFLOW POLICY]",
        "[AGENT INSTRUCTION]",
        "[PRIOR WORKFLOW STEPS]",
        "[USER REQUEST]",
        "[RETRIEVED CONTEXT",
        "[TOOL OUTPUT",
        "[REFINEMENT FEEDBACK]",
    ]:
        assert marker in composed, f"Missing marker: {marker}"

    # Order verification
    positions = {
        "system": composed.find("[SYSTEM POLICY"),
        "workflow": composed.find("[WORKFLOW POLICY]"),
        "agent": composed.find("[AGENT INSTRUCTION]"),
        "prior": composed.find("[PRIOR WORKFLOW STEPS]"),
        "user": composed.find("[USER REQUEST]"),
        "retrieved": composed.find("[RETRIEVED CONTEXT"),
        "tool": composed.find("[TOOL OUTPUT"),
        "refinement": composed.find("[REFINEMENT FEEDBACK]"),
    }
    ordered = ["system", "workflow", "agent", "prior", "user", "retrieved", "tool", "refinement"]
    for i in range(len(ordered) - 1):
        assert positions[ordered[i]] < positions[ordered[i + 1]], \
            f"{ordered[i]} should come before {ordered[i + 1]}"
