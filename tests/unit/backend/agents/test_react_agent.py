"""Unit tests for ReAct agent runtime with mocked LLM and tools."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.agents.react import (
    ReActAgentRuntime,
    ReActStep,
    parse_react_output,
    REACT_SYSTEM_INSTRUCTION,
)
from backend.agents.runtime.llm_runtime import LLMRuntime, LLMRuntimeError
from backend.agents.runtime.runner import (
    ADKRunRequest,
    AgentExecutionContext,
    AgentExecutionResult,
)


# ──────────────────────────────────────────────────────────────
# Mock LLM Runtime
# ──────────────────────────────────────────────────────────────

class MockLLMRuntime(LLMRuntime):
    """Mock LLM runtime that returns predefined outputs per step."""

    def __init__(self, responses: list[str]) -> None:
        super().__init__(model="mock-model")
        self._responses = responses
        self._index = 0
        self.calls: list[dict] = []

    def _call_llm(self, system_prompt: str, user_message: str) -> dict:
        self.calls.append({"system": system_prompt, "user": user_message})
        if self._index < len(self._responses):
            content = self._responses[self._index]
            self._index += 1
        else:
            content = self._responses[-1]
        return {
            "content": content,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }


def _make_request() -> tuple[ADKRunRequest, AgentExecutionContext]:
    request = ADKRunRequest(
        workflow_id="wf-react",
        correlation_id="corr-react",
        agent_name="test_react_agent",
        input_payload={"goal": "test task"},
    )
    context = AgentExecutionContext(
        workflow_id="wf-react",
        correlation_id="corr-react",
        session_id=None,
        model="mock-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    return request, context


# ──────────────────────────────────────────────────────────────
# Test parse_react_output
# ──────────────────────────────────────────────────────────────

def test_parse_thought_and_action() -> None:
    text = """Thought: I need to check the price first.
Action: get_price({"symbol": "EURUSD"})"""
    step = parse_react_output(text)
    assert "check the price" in step.thought
    assert step.action_name == "get_price"
    assert step.action_args == {"symbol": "EURUSD"}
    assert step.is_final is False


def test_parse_final_answer() -> None:
    text = """Thought: I have enough information.
Final: {"answer": 42}"""
    step = parse_react_output(text)
    assert step.is_final is True
    assert step.final_json == '{"answer": 42}'


def test_parse_unknown_tool() -> None:
    text = """Thought: Let me try.
Action: nonexistent_tool({"x": 1})"""
    step = parse_react_output(text)
    assert step.action_name == "nonexistent_tool"
    assert step.action_args == {"x": 1}


def test_parse_malformed_action() -> None:
    text = """Thought: Hmm.
Action: get_price(not valid json)"""
    step = parse_react_output(text)
    assert step.action_name == "get_price"
    assert step.action_args == {"_raw_args": "not valid json"}


def test_parse_no_action() -> None:
    text = "I'm not sure what to do."
    step = parse_react_output(text)
    assert step.thought == "I'm not sure what to do."
    assert step.action_name == ""
    assert step.is_final is False


# ──────────────────────────────────────────────────────────────
# Test ReActAgentRuntime
# ──────────────────────────────────────────────────────────────

def test_react_completes_with_final_answer() -> None:
    """ReAct loop stops when Final is produced."""
    llm = MockLLMRuntime([
        'Thought: I need the price.\nAction: get_price({"symbol": "EURUSD"})',
        'Thought: I have the price.\nFinal: {"price": 1.0850, "symbol": "EURUSD"}',
    ])
    tools = {"get_price": lambda symbol: {"price": 1.0850, "symbol": symbol}}
    react = ReActAgentRuntime(llm, tools=tools, max_steps=5)

    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert result.final_state == "COMPLETED"
    # The final JSON is in the output payload
    assert result.output_payload.get("price") == 1.0850
    assert len(react.step_log) == 2
    assert react.step_log[1].is_final is True
    assert result.token_usage is not None
    assert result.token_usage["total_tokens"] == 300  # 2 steps × 150 tokens


def test_react_enforces_max_steps() -> None:
    """ReAct loop produces best-effort answer when max steps exceeded."""
    llm = MockLLMRuntime([
        'Thought: Step 1.\nAction: get_data({"key": "a"})',
        'Thought: Step 2.\nAction: get_data({"key": "b"})',
        'Thought: Step 3.\nAction: get_data({"key": "c"})',
    ])
    tools = {"get_data": lambda key: {"value": key}}
    react = ReActAgentRuntime(llm, tools=tools, max_steps=2)

    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert result.final_state == "COMPLETED"
    assert "error" in result.output_payload
    assert "Max steps" in result.output_payload["error"]
    assert len(react.step_log) == 2


def test_react_handles_unknown_tool() -> None:
    """ReAct loop handles unknown tool gracefully."""
    llm = MockLLMRuntime([
        'Thought: Let me use a bad tool.\nAction: nonexistent({"x": 1})',
        'Thought: That failed. Let me try something else.\nFinal: {"error": "tool not found"}',
    ])
    tools: dict[str, object] = {}
    react = ReActAgentRuntime(llm, tools=tools, max_steps=5)

    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert result.final_state == "COMPLETED"
    assert len(react.step_log) == 2
    assert "Unknown tool" in react.step_log[0].observation


def test_react_handles_llm_error() -> None:
    """ReAct loop fails closed when LLM call fails."""
    class FailingLLMRuntime(LLMRuntime):
        def __init__(self) -> None:
            super().__init__(model="mock-fail")
        def _call_llm(self, system_prompt: str, user_message: str) -> dict:
            raise LLMRuntimeError("Simulated API failure")

    react = ReActAgentRuntime(FailingLLMRuntime(), tools={}, max_steps=5)
    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert result.final_state == "ERROR"
    assert "error" in result.output_payload


def test_react_provides_tool_descriptions() -> None:
    """ReAct system prompt includes tool descriptions."""
    def get_price(symbol: str) -> dict:
        """Get current price for a symbol."""
        return {"price": 1.0}

    llm = MockLLMRuntime(['Thought: Done.\nFinal: {}'])
    react = ReActAgentRuntime(llm, tools={"get_price": get_price}, max_steps=5)
    request, context = _make_request()
    result = react.run(request=request, context=context)

    # Verify tool description was in the system prompt
    assert any("Get current price" in c.get("system", "") for c in llm.calls)


def test_react_tracks_token_usage() -> None:
    """ReAct loop accumulates token usage across steps."""
    llm = MockLLMRuntime([
        'Thought: Step 1.\nAction: get_x({})',
        'Thought: Step 2.\nFinal: {"done": true}',
    ])
    tools = {"get_x": lambda: {"x": 1}}
    react = ReActAgentRuntime(llm, tools=tools, max_steps=5)

    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert result.token_usage is not None
    # Each MockLLMRuntime returns 150 tokens (100 prompt + 50 completion)
    # 2 steps = 300 total
    assert result.token_usage["total_tokens"] == 300


def test_react_step_log_is_available() -> None:
    """ReAct runtime provides step log with thoughts, actions, and observations."""
    llm = MockLLMRuntime([
        'Thought: Fetch data.\nAction: fetch({"key": "test"})',
        'Thought: Process result.\nFinal: {"result": "ok"}',
    ])
    tools = {"fetch": lambda key: {"value": key}}
    react = ReActAgentRuntime(llm, tools=tools, max_steps=5)

    request, context = _make_request()
    result = react.run(request=request, context=context)

    assert len(react.step_log) == 2
    assert "Fetch data" in react.step_log[0].thought
    assert react.step_log[0].action_name == "fetch"
    assert react.step_log[0].observation == '{"value": "test"}'
    assert react.step_log[1].is_final is True


# ──────────────────────────────────────────────────────────────
# Test ReActSystemInstruction
# ──────────────────────────────────────────────────────────────

def test_react_instruction_has_required_sections() -> None:
    """ReAct system instruction contains all required sections."""
    required = ["ROLE:", "TASK:", "REASONING PROCESS", "RULES:", "CONSTRAINTS:",
                "ESCALATION CONDITIONS:", "OUTPUT SCHEMA:", "FAILURE BEHAVIOR:"]
    for section in required:
        assert section in REACT_SYSTEM_INSTRUCTION, f"Missing section: {section}"
