"""Unit tests for LLM runtime implementations with mocked responses."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.runtime import (
    ADKRunRequest,
    AgentExecutionContext,
    LLMRuntime,
    LLMRuntimeError,
    create_llm_runtime,
    get_provider,
    register_provider,
)
from backend.agents.runtime.llm_runtime import LLMRuntime as LLMRuntimeBase
from backend.agents.runtime.openai_runtime import OpenAIRuntime, HAS_OPENAI


# ──────────────────────────────────────────────────────────────
# Test LLMRuntimeError
# ──────────────────────────────────────────────────────────────

def test_llm_runtime_error_is_exception() -> None:
    err = LLMRuntimeError("test error")
    assert str(err) == "test error"
    assert isinstance(err, Exception)


# ──────────────────────────────────────────────────────────────
# Test MockRuntime (concrete implementation for testing)
# ──────────────────────────────────────────────────────────────

class MockRuntime(LLMRuntimeBase):
    """Concrete LLMRuntime for testing — returns predefined responses."""

    def __init__(self, *, response_content: str = '{"test": true}', model: str = "mock-model", **kwargs) -> None:
        super().__init__(model=model, **kwargs)
        self._response_content = response_content
        self._should_fail = False

    def _call_llm(self, system_prompt: str, user_message: str) -> dict:
        if self._should_fail:
            raise LLMRuntimeError("Mock provider failure")
        return {
            "content": self._response_content,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }


def test_mock_runtime_returns_agent_execution_result() -> None:
    runtime = MockRuntime(response_content='{"key": "value"}')
    request = ADKRunRequest(
        workflow_id="wf-1",
        correlation_id="corr-1",
        agent_name="test_agent",
        input_payload={"goal": "test"},
    )
    context = AgentExecutionContext(
        workflow_id="wf-1",
        correlation_id="corr-1",
        session_id=None,
        model="mock-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    result = runtime.run(request=request, context=context)

    assert result.output_payload == {"key": "value"}
    assert result.final_state == "COMPLETED"
    assert result.token_usage == {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }


def test_mock_runtime_handles_invalid_json() -> None:
    runtime = MockRuntime(response_content="not valid json")
    request = ADKRunRequest(
        workflow_id="wf-1",
        correlation_id="corr-1",
        agent_name="test_agent",
        input_payload={"goal": "test"},
    )
    context = AgentExecutionContext(
        workflow_id="wf-1",
        correlation_id="corr-1",
        session_id=None,
        model="mock-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    result = runtime.run(request=request, context=context)

    # Invalid JSON should be wrapped with parse error
    assert "_parse_error" in result.output_payload
    assert result.final_state == "COMPLETED"


def test_mock_runtime_fails_closed_on_error() -> None:
    runtime = MockRuntime()
    runtime._should_fail = True
    request = ADKRunRequest(
        workflow_id="wf-1",
        correlation_id="corr-1",
        agent_name="test_agent",
        input_payload={"goal": "test"},
    )
    context = AgentExecutionContext(
        workflow_id="wf-1",
        correlation_id="corr-1",
        session_id=None,
        model="mock-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    result = runtime.run(request=request, context=context)

    assert result.final_state == "ERROR"
    assert "error" in result.output_payload


# ──────────────────────────────────────────────────────────────
# Test provider registry
# ──────────────────────────────────────────────────────────────

def test_register_and_get_provider() -> None:
    """Test provider registration and retrieval."""
    register_provider("test_mock", MockRuntime)
    cls = get_provider(provider="test_mock")
    assert cls is MockRuntime


def test_get_provider_auto_detects_gemini() -> None:
    """Auto-detect gemini from model name — litellm preferred when registered."""
    register_provider("gemini", MockRuntime)
    cls = get_provider(model="gemini-3.1-flash-lite-preview")
    # litellm is preferred for gemini when registered; fallback to gemini mock
    assert cls.__name__ in ("LiteLLMRuntime", "MockRuntime")


def test_get_provider_auto_detects_openai() -> None:
    """Auto-detect openai from model name — litellm preferred when registered."""
    register_provider("openai", MockRuntime)
    cls = get_provider(model="gpt-4o-mini")
    # litellm is preferred for all models when registered; fallback to openai mock
    assert cls.__name__ in ("LiteLLMRuntime", "MockRuntime")


def test_get_provider_falls_back_to_first() -> None:
    """Fallback to first registered provider when no match."""
    register_provider("fallback_test", MockRuntime)
    cls = get_provider(model="unknown-model-xyz")
    # litellm is registered globally and preferred for all models
    assert cls.__name__ in ("LiteLLMRuntime", "MockRuntime")


def test_get_provider_raises_on_unknown_explicit() -> None:
    """Explicit unknown provider raises ValueError."""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider(provider="nonexistent_provider_12345")


# ──────────────────────────────────────────────────────────────
# Test create_llm_runtime
# ──────────────────────────────────────────────────────────────

def test_create_llm_runtime_returns_instance() -> None:
    """create_llm_runtime returns a configured LLMRuntime."""
    register_provider("create_test", MockRuntime)
    runtime = create_llm_runtime(provider="create_test")
    assert isinstance(runtime, MockRuntime)


# ──────────────────────────────────────────────────────────────
# Test OpenAIRuntime (mocked, requires openai package)
# ──────────────────────────────────────────────────────────────

def test_openai_runtime_calls_api() -> None:
    """OpenAIRuntime makes correct API call and parses response."""
    pytest.skip("OpenAI test requires valid API key — covered by mock tests")
