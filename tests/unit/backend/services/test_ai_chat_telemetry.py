from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch, ANY
from backend.services.ai_chat.ai_gateway import AIGatewayService, ChatStreamRequest, GenerationResult
from backend.services.ai_chat.models import ConversationThreadRecord, ConversationMessageRecord

@pytest.fixture
def mock_services():
    conv_service = MagicMock()
    context_assembler = MagicMock()
    prompt_builder = MagicMock()
    agent_router = MagicMock()
    tool_executor = MagicMock()
    
    # Setup default returns
    thread = MagicMock(spec=ConversationThreadRecord)
    thread.thread_id = "thread_1"
    thread.current_route = "/dashboard"
    thread.messages = [MagicMock(spec=ConversationMessageRecord)]
    thread.messages[-1].message_id = "msg_assistant_1"
    
    conv_service.get_thread.return_value = thread
    
    page_context = MagicMock()
    page_context.payload.context_revision = "rev_1"
    page_context.payload.page_type = "dashboard"
    context_assembler.assemble_context.return_value = page_context
    
    decision = MagicMock()
    decision.response_mode.value = "plain_answer"
    decision.model_tier = "fast"
    decision.task_class = "general"
    decision.response_style = "concise"
    decision.domain_focus = "general"
    agent_router.route.return_value = decision
    
    tool_executor.execute.return_value = ([], set())
    
    prompt = MagicMock()
    prompt.system_prompt = "system"
    prompt.user_prompt = "user"
    prompt_builder.build.return_value = prompt
    
    return {
        "conv_service": conv_service,
        "context_assembler": context_assembler,
        "prompt_builder": prompt_builder,
        "agent_router": agent_router,
        "tool_executor": tool_executor
    }

def test_ai_gateway_collects_telemetry(mock_services) -> None:
    gateway = AIGatewayService(
        conversation_service=mock_services["conv_service"],
        context_assembler=mock_services["context_assembler"],
        prompt_builder=mock_services["prompt_builder"],
        agent_router=mock_services["agent_router"],
        tool_executor=mock_services["tool_executor"]
    )
    
    gen_result = GenerationResult(
        text="Hello world",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    
    request = ChatStreamRequest(user_id=1, thread_id="thread_1", prompt="hi")
    
    with patch.object(gateway, "_generate_text", return_value=gen_result):
        with patch("time.perf_counter", side_effect=[0.0, 0.5]): # 500ms latency
            metadata, chunks, msg_id = gateway.stream_response(request)
            
            assert "telemetry" in metadata
            assert metadata["generation_source"] == "fallback"
            telemetry = metadata["telemetry"]
            assert telemetry["latency_ms"] == 500
            assert telemetry["prompt_tokens"] == 100
            assert telemetry["completion_tokens"] == 50
            assert telemetry["total_tokens"] == 150
            # cost for flash model (default for fast tier): 
            # (100/1M * 0.075) + (50/1M * 0.3) = 0.0000075 + 0.000015 = 0.0000225
            assert telemetry["cost_usd"] == 0.000023 # rounded to 6 decimal places
            
            # Verify persistence
            mock_services["conv_service"].add_message.assert_any_call(
                user_id=1,
                thread_id="thread_1",
                role="assistant",
                content="Hello world",
                request_id=ANY,
                context_revision="rev_1",
                tool_calls=[],
                signal_proposal_id=None,
                action_draft_id=None,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost=0.000023,
                latency_ms=500
            )

def test_calculate_cost_handling() -> None:
    # Test different models
    assert AIGatewayService._calculate_cost(model="gpt-4o", prompt_tokens=1000000, completion_tokens=1000000) == 12.5
    assert AIGatewayService._calculate_cost(model="gpt-4o-mini", prompt_tokens=1000000, completion_tokens=1000000) == 0.75
    assert AIGatewayService._calculate_cost(model="gemini-3.1-flash-lite-preview", prompt_tokens=1000000, completion_tokens=1000000) == 0.375
    assert AIGatewayService._calculate_cost(model="unknown", prompt_tokens=1000000, completion_tokens=1000000) == 0.0

def test_ai_gateway_uses_fallback_model_when_request_budget_exceeded(mock_services) -> None:
    cost_enforcer = MagicMock()
    cost_enforcer.check_request_budget.side_effect = [False, True]
    cost_enforcer.get_fallback_model.return_value = "gemini-3.1-flash-lite-preview"
    cost_enforcer.get_current_cost.return_value = 0.02
    cost_enforcer.check_workflow_budget.return_value = True

    gateway = AIGatewayService(
        conversation_service=mock_services["conv_service"],
        context_assembler=mock_services["context_assembler"],
        prompt_builder=mock_services["prompt_builder"],
        agent_router=mock_services["agent_router"],
        tool_executor=mock_services["tool_executor"],
        cost_enforcer=cost_enforcer,
    )

    gen_result = GenerationResult(text="Hello world", prompt_tokens=100, completion_tokens=50, total_tokens=150)

    with patch.object(gateway, "_generate_text", return_value=gen_result) as generate_mock:
        metadata, _chunks, _msg_id = gateway.stream_response(
            ChatStreamRequest(user_id=1, thread_id="thread_1", prompt="hi")
        )

    assert generate_mock.call_args.kwargs["model"] == "gemini-3.1-flash-lite-preview"
    assert metadata["cost_policy"]["budget_downgraded"] is True


def test_ai_gateway_reports_runtime_generation_source(mock_services) -> None:
    gateway = AIGatewayService(
        conversation_service=mock_services["conv_service"],
        context_assembler=mock_services["context_assembler"],
        prompt_builder=mock_services["prompt_builder"],
        agent_router=mock_services["agent_router"],
        tool_executor=mock_services["tool_executor"],
    )

    runtime = MagicMock()
    runtime.provider_name = "litellm"
    runtime._call_llm.return_value = {
        "content": "Live model reply",
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
    }

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", return_value=runtime):
        metadata, chunks, _msg_id = gateway.stream_response(
            ChatStreamRequest(user_id=1, thread_id="thread_1", prompt="hi")
        )

    assert metadata["generation_source"] == "llm_runtime"
    assert metadata["provider_name"] == "litellm"
    assert "".join(chunks) == "Live model reply"


def test_ai_gateway_polishes_runtime_reply_that_leaks_internal_labels(mock_services) -> None:
    gateway = AIGatewayService(
        conversation_service=mock_services["conv_service"],
        context_assembler=mock_services["context_assembler"],
        prompt_builder=mock_services["prompt_builder"],
        agent_router=mock_services["agent_router"],
        tool_executor=mock_services["tool_executor"],
    )

    runtime = MagicMock()
    runtime.provider_name = "litellm"
    runtime._call_llm.return_value = {
        "content": "Mode: answer\nStyle: summary\nRequest ID: abc123\nSummary:\nThe dashboard is flat because no active strategies are contributing this week.",
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
    }

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", return_value=runtime):
        metadata, chunks, _msg_id = gateway.stream_response(
            ChatStreamRequest(user_id=1, thread_id="thread_1", prompt="hi")
        )

    content = "".join(chunks)
    assert metadata["generation_source"] == "llm_runtime"
    assert "Mode:" not in content
    assert "Style:" not in content
    assert "Request ID:" not in content
    assert content == "The dashboard is flat because no active strategies are contributing this week."


def test_ai_gateway_polishes_runtime_reply_that_leaks_section_headers(mock_services) -> None:
    gateway = AIGatewayService(
        conversation_service=mock_services["conv_service"],
        context_assembler=mock_services["context_assembler"],
        prompt_builder=mock_services["prompt_builder"],
        agent_router=mock_services["agent_router"],
        tool_executor=mock_services["tool_executor"],
    )

    runtime = MagicMock()
    runtime.provider_name = "litellm"
    runtime._call_llm.return_value = {
        "content": "### Summary\nThe strategy made money.\n\n### Metrics\n- Net profit: $340.75\n\n### Implications\nLong trades are carrying performance.",
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
    }

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", return_value=runtime):
        metadata, chunks, _msg_id = gateway.stream_response(
            ChatStreamRequest(user_id=1, thread_id="thread_1", prompt="hi")
        )

    content = "".join(chunks)
    assert metadata["generation_source"] == "llm_runtime"
    assert "### Summary" not in content
    assert "### Metrics" not in content
    assert "### Implications" not in content
    assert "The strategy made money." in content
    assert "- Net profit: $340.75" in content
