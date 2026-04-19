"""Phase 4 AI gateway and streaming orchestration for HaruQuant chat."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Iterable
from uuid import uuid4

from backend.config.agent_model import get_model_for_tier
from backend.services.ai_chat.agent_router import ChatAgentRouter
from backend.services.ai_chat.context_service import PageContextAssembler
from backend.services.ai_chat.conversation_service import ConversationService
from backend.services.ai_chat.prompt_builder import ChatPromptBuilder

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_OPENAI = False


@dataclass(frozen=True)
class ChatStreamRequest:
    user_id: int
    thread_id: str
    prompt: str
    request_id: str | None = None
    include_debug: bool = False


class AIGatewayService:
    """Own the Phase 4 chat request lifecycle and streaming response path."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        context_assembler: PageContextAssembler,
        prompt_builder: ChatPromptBuilder | None = None,
        agent_router: ChatAgentRouter | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.context_assembler = context_assembler
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.agent_router = agent_router or ChatAgentRouter()

    def stream_response(self, request: ChatStreamRequest) -> tuple[dict[str, object], Iterable[str], str]:
        request_id = request.request_id or f"chatreq_{uuid4().hex}"
        thread = self.conversation_service.get_thread(user_id=request.user_id, thread_id=request.thread_id)
        page_context = self.context_assembler.assemble_context(
            route=thread.current_route or "/dashboard",
            user_id=request.user_id,
        )
        decision = self.agent_router.route(request.prompt)
        built_prompt = self.prompt_builder.build(
            thread=thread,
            page_context=page_context,
            user_prompt=request.prompt,
            response_mode=decision.response_mode.value,
        )

        self.conversation_service.add_message(
            user_id=request.user_id,
            thread_id=request.thread_id,
            role="user",
            content=request.prompt,
            request_id=request_id,
            context_revision=page_context.payload.context_revision,
        )

        full_text = self._generate_text(
            system_prompt=built_prompt.system_prompt,
            user_prompt=built_prompt.user_prompt,
            model=get_model_for_tier(decision.model_tier),
            page_context=page_context,
            response_mode=decision.response_mode.value,
        )
        self.conversation_service.add_message(
            user_id=request.user_id,
            thread_id=request.thread_id,
            role="assistant",
            content=full_text,
            request_id=request_id,
            context_revision=page_context.payload.context_revision,
        )
        refreshed_thread = self.conversation_service.get_thread(
            user_id=request.user_id,
            thread_id=request.thread_id,
        )
        metadata = {
            "request_id": request_id,
            "thread_id": request.thread_id,
            "response_mode": decision.response_mode.value,
            "task_class": decision.task_class,
            "model": get_model_for_tier(decision.model_tier),
            "context_revision": page_context.payload.context_revision,
        }
        if request.include_debug:
            metadata["debug"] = {
                "router_rationale": decision.rationale,
                "prompt": built_prompt.debug,
            }
        return metadata, self._chunk_text(full_text), refreshed_thread.messages[-1].message_id

    def _generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        page_context,
        response_mode: str,
    ) -> str:
        if self._can_use_openai():
            streamed = self._generate_openai_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
            )
            if streamed.strip():
                return streamed
        return self._generate_fallback_text(
            user_prompt=user_prompt,
            page_context=page_context,
            response_mode=response_mode,
        )

    def _can_use_openai(self) -> bool:
        return HAS_OPENAI and bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL"))

    def _generate_openai_text(self, *, system_prompt: str, user_prompt: str, model: str) -> str:
        client_kwargs = {"api_key": os.environ.get("OPENAI_API_KEY", "ollama")}
        if os.environ.get("OPENAI_BASE_URL"):
            client_kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
        client = OpenAI(**client_kwargs)
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
            if delta:
                parts.append(delta)
        return "".join(parts)

    def _generate_fallback_text(self, *, user_prompt: str, page_context, response_mode: str) -> str:
        bullets = page_context.payload.summary.bullets[:3]
        lead = page_context.payload.summary.headline
        response_lines = [
            lead,
            f"Mode: {response_mode}.",
        ]
        if bullets:
            response_lines.append("Current context:")
            response_lines.extend(f"- {bullet}" for bullet in bullets)
        response_lines.append("Working answer:")
        response_lines.append(
            "Based on the current HaruQuant page context, start from the latest system state, validate the relevant strategy or session entities, and only then compare against recent conversation history."
        )
        response_lines.append(
            f"User request received: {user_prompt.splitlines()[-1]}"
        )
        return "\n".join(response_lines)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 48) -> Iterable[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
