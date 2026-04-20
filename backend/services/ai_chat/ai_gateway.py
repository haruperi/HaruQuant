"""Phase 4 AI gateway and streaming orchestration for HaruQuant chat."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable
from uuid import uuid4

from backend.config.agent_model import get_model_for_tier
from backend.services.ai_chat.agent_router import ChatAgentRouter
from backend.services.ai_chat.context_service import PageContextAssembler
from backend.services.ai_chat.conversation_service import ConversationService
from backend.services.ai_chat.prompt_builder import ChatPromptBuilder
from backend.services.ai_chat.policy import AuthorityBand
from backend.services.tool_executor import ToolExecutionResult, ToolExecutor

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
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.context_assembler = context_assembler
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.agent_router = agent_router or ChatAgentRouter()
        self.tool_executor = tool_executor or ToolExecutor(db_manager=context_assembler.db_manager)

    def stream_response(self, request: ChatStreamRequest) -> tuple[dict[str, object], Iterable[str], str]:
        request_id = request.request_id or f"chatreq_{uuid4().hex}"
        thread = self.conversation_service.get_thread(user_id=request.user_id, thread_id=request.thread_id)
        page_context = self.context_assembler.assemble_context(
            route=thread.current_route or "/dashboard",
            user_id=request.user_id,
        )
        decision = self.agent_router.route(request.prompt)
        tool_context = self._build_tool_context(page_context=page_context, prompt=request.prompt)
        requested_tools = self._select_tools(
            prompt=request.prompt,
            page_type=page_context.payload.page_type,
            context=tool_context,
        )
        tool_results, denied_tools = self.tool_executor.execute(
            user_id=request.user_id,
            requested_tools=requested_tools,
            context=tool_context,
            authority_band=AuthorityBand.READ_ONLY,
        )
        built_prompt = self.prompt_builder.build(
            thread=thread,
            page_context=page_context,
            user_prompt=self._compose_grounded_user_prompt(
                prompt=request.prompt,
                tool_results=tool_results,
                denied_tools=denied_tools,
            ),
            response_mode=(
                decision.response_mode.value
                if tool_results
                else decision.response_mode.value
            ),
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
            response_mode="tool_assisted" if tool_results else decision.response_mode.value,
            tool_results=tool_results,
        )
        self.conversation_service.add_message(
            user_id=request.user_id,
            thread_id=request.thread_id,
            role="assistant",
            content=full_text,
            request_id=request_id,
            context_revision=page_context.payload.context_revision,
            tool_calls=[result.tool_name for result in tool_results if result.success],
        )
        refreshed_thread = self.conversation_service.get_thread(
            user_id=request.user_id,
            thread_id=request.thread_id,
        )
        metadata = {
            "request_id": request_id,
            "thread_id": request.thread_id,
            "response_mode": "tool_assisted" if tool_results else decision.response_mode.value,
            "task_class": decision.task_class,
            "model": get_model_for_tier(decision.model_tier),
            "context_revision": page_context.payload.context_revision,
            "tools_used": [result.tool_name for result in tool_results if result.success],
            "tools_denied": list(denied_tools),
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
        tool_results: list[ToolExecutionResult],
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
            tool_results=tool_results,
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

    def _generate_fallback_text(
        self,
        *,
        user_prompt: str,
        page_context,
        response_mode: str,
        tool_results: list[ToolExecutionResult],
    ) -> str:
        bullets = page_context.payload.summary.bullets[:3]
        lead = page_context.payload.summary.headline
        response_lines = [
            lead,
            f"Mode: {response_mode}.",
        ]
        if tool_results:
            response_lines.append("Grounded tools used:")
            response_lines.extend(
                f"- {result.tool_name}: {self._summarize_tool_payload(result.payload)}"
                for result in tool_results
                if result.success
            )
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

    def _select_tools(
        self,
        *,
        prompt: str,
        page_type: str,
        context: dict[str, object],
    ) -> tuple[str, ...]:
        selected: list[str] = []
        normalized = prompt.lower()
        if page_type in {"dashboard", "portfolio_risk", "live_trading"}:
            selected.extend(["portfolio_summary", "risk_snapshot"])
            if context.get("session_id") is not None or "position" in normalized:
                selected.append("open_positions")
            if any(word in normalized for word in ("alert", "warning", "error", "incident", "log")):
                selected.append("alert_history")
        if page_type == "strategy_detail" or context.get("strategy_id") is not None:
            selected.append("strategy_parameters")
        if page_type == "backtest_detail" or context.get("backtest_id") is not None:
            selected.append("backtest_summary")
        if page_type == "optimization_detail" or context.get("optimization_id") is not None:
            selected.append("optimization_results")
        if context.get("symbol") is not None or any(word in normalized for word in ("symbol", "dataset", "timeframe")):
            selected.append("symbol_stats")
        return tuple(dict.fromkeys(selected))

    def _build_tool_context(self, *, page_context, prompt: str) -> dict[str, object]:
        payload = page_context.payload.payload
        route = page_context.payload.route
        session_id = payload.get("session_id")
        strategy_id = payload.get("strategy_id")
        backtest_id = payload.get("backtest_id")
        optimization_id = payload.get("optimization_id")
        symbol = self._extract_symbol(prompt)
        if symbol is None:
            for entity in page_context.payload.entity_refs:
                if entity.type.lower() in {"symbol", "asset"}:
                    symbol = entity.label or entity.id
                    break
        return {
            "route": route,
            "page_type": page_context.payload.page_type,
            "session_id": session_id,
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "optimization_id": optimization_id,
            "symbol": symbol,
        }

    @staticmethod
    def _extract_symbol(prompt: str) -> str | None:
        match = re.search(r"\b([A-Z]{2,6})\b", prompt)
        return match.group(1) if match else None

    @staticmethod
    def _compose_grounded_user_prompt(
        *,
        prompt: str,
        tool_results: list[ToolExecutionResult],
        denied_tools: tuple[str, ...],
    ) -> str:
        lines = [prompt.strip()]
        if tool_results:
            lines.append("Tool grounding:")
            for result in tool_results:
                status = "ok" if result.success else f"error={result.error}"
                lines.append(f"- {result.tool_name} ({status}): {result.payload}")
        if denied_tools:
            lines.append(f"Denied tools: {', '.join(denied_tools)}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_tool_payload(payload: dict[str, object]) -> str:
        for preferred_key in (
            "aggregate_open_profit",
            "open_position_count",
            "best_score",
            "active_version",
            "alert_count",
            "dataset_count",
            "status",
        ):
            if preferred_key in payload:
                return f"{preferred_key}={payload[preferred_key]}"
        return ", ".join(f"{key}={value}" for key, value in list(payload.items())[:3]) or "no payload"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 48) -> Iterable[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
