from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch, ANY
from backend.services.ai_chat.ai_gateway import AIGatewayService, ChatStreamRequest, GenerationResult
from backend.services.ai_chat.models import ConversationThreadRecord, ConversationMessageRecord
from backend.services.ai_chat.policy import AuthorityBand

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
    assert AIGatewayService._calculate_cost(model="gpt-4o", prompt_tokens=1000000, completion_tokens=1000000) == 20.0
    assert AIGatewayService._calculate_cost(model="gpt-4o-mini", prompt_tokens=1000000, completion_tokens=1000000) == 0.75
    assert AIGatewayService._calculate_cost(model="gemini-1.5-pro", prompt_tokens=1000000, completion_tokens=1000000) == 14.0
    assert AIGatewayService._calculate_cost(model="unknown", prompt_tokens=1000000, completion_tokens=1000000) == 0.375 # default to flash
