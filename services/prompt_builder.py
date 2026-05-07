"""Prompt composition for the AI Chat gateway."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from services.schemas.chat import (
    ChatPromptCompositionLog,
    ChatPromptLayerLog,
    ChatRouteDecision,
    ChatThreadDetail,
    ChatTurnRequest,
    PageContext,
)


MAX_CONTEXT_CHARS = 12000
MAX_RECENT_MESSAGES = 24


@dataclass(frozen=True)
class PromptBuildResult:
    messages: list[dict[str, str]]
    composition: ChatPromptCompositionLog


class PromptBuilder:
    """Builds layered, auditable prompts from thread, memory, and page context."""

    def build(
        self,
        *,
        request: ChatTurnRequest,
        request_id: str,
        thread: ChatThreadDetail,
        page_context: PageContext,
        route: ChatRouteDecision,
        tool_evidence: str | None = None,
    ) -> PromptBuildResult:
        layers: list[ChatPromptLayerLog] = []
        messages: list[dict[str, str]] = []

        system = self._system_prompt(route=route)
        messages.append({"role": "system", "content": system})
        layers.append(_layer("system", system, authority="highest", summary="Firm governance and answer contract."))

        memory = thread.memory_summary.summary_text if thread.memory_summary else ""
        if memory:
            messages.append({"role": "system", "content": f"Conversation memory summary:\n{memory}"})
        layers.append(_layer("memory_summary", memory, authority="conversation_memory", included=bool(memory)))

        pinned = "\n".join(f"- {fact.key}: {fact.value} ({fact.source})" for fact in thread.pinned_facts[:24])
        if pinned:
            messages.append({"role": "system", "content": f"Pinned conversation facts:\n{pinned}"})
        layers.append(_layer("pinned_facts", pinned, authority="user_saved", included=bool(pinned)))

        context_payload, context_truncated = _compact_json(page_context.model_dump(), max_chars=MAX_CONTEXT_CHARS)
        page_text = (
            "Current page context, refreshed for this turn. Prefer this over stale thread memory "
            "when answering page-specific questions.\n"
            f"{context_payload}"
        )
        messages.append({"role": "system", "content": page_text})
        layers.append(
            _layer(
                "page_context",
                context_payload,
                authority="current_ui_state",
                summary=f"{page_context.page_type} at {page_context.route}",
            )
        )

        if request.attached_tools:
            tools_text = "\n".join(f"- {tool_id}: user-attached read-only capability hint" for tool_id in request.attached_tools)
            messages.append({"role": "system", "content": f"Attached tools requested by the user:\n{tools_text}"})
            layers.append(_layer("attached_tools", tools_text, authority="user_requested", included=True))
        else:
            layers.append(_layer("attached_tools", "", authority="user_requested", included=False))

        if tool_evidence:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Read-only HaruQuant tool evidence for this turn. Use it as provenance, "
                        "and mention unavailable tools instead of guessing.\n"
                        f"{tool_evidence}"
                    ),
                }
            )
        layers.append(_layer("read_only_tool_evidence", tool_evidence or "", authority="haruquant_read_only_tools", included=bool(tool_evidence)))

        recent_messages = [
            message
            for message in thread.messages
            if message.role in {"user", "assistant"} and message.request_id != request.request_id
        ][-MAX_RECENT_MESSAGES:]
        recent_text = "\n".join(f"{message.role}: {message.content}" for message in recent_messages)
        for message in recent_messages:
            messages.append({"role": message.role, "content": message.content})
        layers.append(_layer("recent_messages", recent_text, authority="conversation_history", included=bool(recent_messages)))

        messages.append({"role": "user", "content": request.prompt})
        layers.append(_layer("user_prompt", request.prompt, authority="user", summary="Current user request."))

        token_estimate = sum(layer.token_estimate for layer in layers)
        composition = ChatPromptCompositionLog(
            request_id=request_id,
            route=route,
            layers=layers,
            message_count=len(messages),
            token_estimate=token_estimate,
            truncated=context_truncated,
        )
        return PromptBuildResult(messages=messages, composition=composition)

    def _system_prompt(self, *, route: ChatRouteDecision) -> str:
        return (
            "You are HaruQuant AI, a production assistant inside a governed trading application. "
            "The user is talking to the CEO/CIO-style orchestrator, not directly to specialist departments. "
            "PlannerAgent decides the route and safe evidence gathering; CEOAgent owns the final executive voice. "
            "Use current page context, conversation memory, and visible evidence. "
            "Be concise, operational, and explicit about uncertainty. "
            "Do not claim to execute trades or irreversible actions from chat. "
            "When tools are requested, describe the intended read-only use and avoid side effects. "
            f"Route intent: {route.intent}. Response mode: {route.response_mode}."
        )


def _layer(
    name: str,
    content: str,
    *,
    authority: str,
    included: bool = True,
    summary: str | None = None,
) -> ChatPromptLayerLog:
    return ChatPromptLayerLog(
        name=name,
        authority=authority,
        included=included,
        char_count=len(content),
        token_estimate=max(1, len(content) // 4) if content else 0,
        summary=summary,
    )


def _compact_json(payload: dict[str, Any], *, max_chars: int) -> tuple[str, bool]:
    encoded = json.dumps(payload, default=str, ensure_ascii=True, separators=(",", ":"))
    if len(encoded) <= max_chars:
        return encoded, False
    compacted = {
        "context_schema_version": payload.get("context_schema_version"),
        "route": payload.get("route"),
        "page_type": payload.get("page_type"),
        "page_title": payload.get("page_title"),
        "context_revision": payload.get("context_revision"),
        "freshness": payload.get("freshness"),
        "authority": payload.get("authority"),
        "summary": payload.get("summary"),
        "payload_compacted": True,
    }
    return json.dumps(compacted, default=str, ensure_ascii=True, separators=(",", ":")), True


__all__ = ["PromptBuildResult", "PromptBuilder"]
