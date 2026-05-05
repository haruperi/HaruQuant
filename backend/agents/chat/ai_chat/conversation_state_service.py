"""Derived short-horizon topic and reference state for AI chat."""

from __future__ import annotations

import re

from backend.contracts.page_context_packet.model import PageContextPacket
from backend.agents.chat.ai_chat.models import (
    ConversationEntityState,
    ConversationState,
    ConversationThreadRecord,
)


class ConversationStateService:
    """Derive compact conversation state from thread history and page context."""

    _SYMBOL_PATTERN = re.compile(r"\b([A-Z]{2,6}|[A-Z]{6})\b")
    _TIMEFRAME_PATTERN = re.compile(r"\b(1[HDWM]|[1-9]\d?[mhdwMHDW])\b")
    _REFERENCE_PATTERNS: dict[str, re.Pattern[str]] = {
        "strategy_id": re.compile(r"\bstrategy(?:\s+(?:id|#))?\s*(\d+)\b", re.IGNORECASE),
        "backtest_id": re.compile(r"\bbacktest(?:\s+(?:id|#))?\s*(\d+)\b", re.IGNORECASE),
        "optimization_id": re.compile(r"\boptimization(?:\s+(?:id|#))?\s*(\d+)\b", re.IGNORECASE),
        "session_id": re.compile(r"\b(?:live\s+session|session)(?:\s+(?:id|#))?\s*(\d+)\b", re.IGNORECASE),
    }
    _TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("comparison", ("compare", "versus", "vs", "tradeoff")),
        ("diagnostic", ("diagnose", "underperform", "drawdown", "flat", "stalled", "why")),
        ("risk", ("risk", "exposure", "var", "danger", "concentration")),
        ("strategy_research", ("strategy", "backtest", "optimization", "optimise", "optimize")),
        ("page_summary", ("summary", "summaries", "summarize", "summarise", "page")),
    )

    def build_state(
        self,
        *,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        latest_prompt: str | None = None,
    ) -> ConversationState:
        source_messages = list(getattr(thread, "messages", []) or [])
        active_entities = self._collect_entities(thread=thread, page_context=page_context)
        resolved_references = self._build_reference_map(active_entities=active_entities)
        user_preferences = self._collect_preferences(thread=thread)
        active_topic = self._infer_active_topic(
            thread=thread,
            page_context=page_context,
            latest_prompt=latest_prompt,
        )
        unresolved = self._infer_unresolved_references(
            latest_prompt=latest_prompt or "",
            resolved_references=resolved_references,
        )
        return ConversationState(
            active_topic=active_topic,
            active_entities=active_entities,
            resolved_references=resolved_references,
            unresolved_references=unresolved,
            user_preferences=user_preferences,
            source_message_count=len(source_messages),
        )

    def enrich_tool_context(
        self,
        *,
        context: dict[str, object],
        prompt: str,
        state: ConversationState,
    ) -> dict[str, object]:
        enriched = dict(context)
        for key in ("strategy_id", "backtest_id", "optimization_id", "session_id", "symbol", "timeframe"):
            if enriched.get(key) is None and key in state.resolved_references:
                enriched[key] = state.resolved_references[key]

        normalized = prompt.lower()
        if "previous run" in normalized or "previous one" in normalized:
            if "previous_backtest_id" in state.resolved_references:
                enriched["comparison_backtest_id"] = state.resolved_references["previous_backtest_id"]
            if "previous_optimization_id" in state.resolved_references:
                enriched["comparison_optimization_id"] = state.resolved_references["previous_optimization_id"]
        if "this strategy" in normalized and enriched.get("strategy_id") is None:
            enriched["strategy_id"] = state.resolved_references.get("strategy_id")
        if "this run" in normalized and enriched.get("backtest_id") is None:
            enriched["backtest_id"] = state.resolved_references.get("backtest_id")
        if "that drawdown" in normalized and "backtest_id" in state.resolved_references:
            enriched["backtest_id"] = state.resolved_references["backtest_id"]
        return enriched

    def _collect_entities(
        self,
        *,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
    ) -> list[ConversationEntityState]:
        entities: list[ConversationEntityState] = []
        seen: set[tuple[str, str]] = set()
        pinned_facts = list(getattr(thread, "pinned_facts", []) or [])
        recent_messages = list(getattr(thread, "messages", []) or [])[-8:]

        def add_entity(entity_type: str, entity_id: str, *, label: str | None, source: str) -> None:
            key = (entity_type, str(entity_id))
            if key in seen:
                return
            seen.add(key)
            entities.append(
                ConversationEntityState(
                    type=entity_type,
                    id=str(entity_id),
                    label=label,
                    source=source,
                )
            )

        for entity in page_context.payload.entity_refs:
            add_entity(entity.type, entity.id, label=entity.label, source="page_context")

        payload = page_context.payload.payload
        for key in ("strategy_id", "backtest_id", "optimization_id", "session_id"):
            value = payload.get(key)
            if value is not None:
                add_entity(key.removesuffix("_id"), str(value), label=None, source="page_payload")
        symbols = payload.get("symbols")
        if isinstance(symbols, list):
            for symbol in symbols[:3]:
                if symbol:
                    add_entity("symbol", str(symbol).upper(), label=str(symbol).upper(), source="page_payload")
        timeframes = payload.get("timeframes")
        if isinstance(timeframes, list):
            for timeframe in timeframes[:2]:
                if timeframe:
                    add_entity("timeframe", str(timeframe).upper(), label=str(timeframe).upper(), source="page_payload")

        for fact in pinned_facts[:6]:
            key = fact.key.lower()
            if "symbol" in key or "asset" in key:
                add_entity("symbol", fact.value.upper(), label=fact.value.upper(), source=f"pinned_fact:{fact.key}")
            if "timeframe" in key:
                add_entity("timeframe", fact.value.upper(), label=fact.value.upper(), source=f"pinned_fact:{fact.key}")

        for index, message in enumerate(recent_messages):
            role = str(getattr(message, "role", "unknown"))
            content = str(getattr(message, "content", "") or "")
            source = f"message:{role}:{index}"
            for reference_key, pattern in self._REFERENCE_PATTERNS.items():
                for match in pattern.findall(content):
                    add_entity(reference_key.removesuffix("_id"), str(match), label=None, source=source)
            for symbol in self._extract_symbols(content):
                add_entity("symbol", symbol, label=symbol, source=source)
            for timeframe in self._extract_timeframes(content):
                add_entity("timeframe", timeframe, label=timeframe, source=source)

        return entities

    def _build_reference_map(self, *, active_entities: list[ConversationEntityState]) -> dict[str, str]:
        references: dict[str, str] = {}

        def values_for(entity_type: str) -> list[ConversationEntityState]:
            return [entity for entity in active_entities if entity.type == entity_type]

        def current_value(entity_type: str) -> str | None:
            entities = values_for(entity_type)
            if not entities:
                return None
            for entity in entities:
                if entity.source in {"page_context", "page_payload"}:
                    return entity.id
            return entities[-1].id

        def previous_value(entity_type: str, current: str | None) -> str | None:
            entities = values_for(entity_type)
            if not entities:
                return None
            for entity in reversed(entities):
                if current is None or entity.id != current:
                    return entity.id
            return None

        strategy_id = current_value("strategy")
        backtest_id = current_value("backtest")
        previous_backtest_id = previous_value("backtest", backtest_id)
        optimization_id = current_value("optimization")
        previous_optimization_id = previous_value("optimization", optimization_id)
        session_id = current_value("live_session") or current_value("session")
        symbol = current_value("symbol")
        timeframe = current_value("timeframe")

        if strategy_id:
            references["strategy_id"] = strategy_id
        if backtest_id:
            references["backtest_id"] = backtest_id
        if previous_backtest_id:
            references["previous_backtest_id"] = previous_backtest_id
        if optimization_id:
            references["optimization_id"] = optimization_id
        if previous_optimization_id:
            references["previous_optimization_id"] = previous_optimization_id
        if session_id:
            references["session_id"] = session_id
        if symbol:
            references["symbol"] = symbol
        if timeframe:
            references["timeframe"] = timeframe
        return references

    def _collect_preferences(self, *, thread: ConversationThreadRecord) -> dict[str, str]:
        preferences: dict[str, str] = {}
        pinned_facts = list(getattr(thread, "pinned_facts", []) or [])
        recent_messages = list(getattr(thread, "messages", []) or [])
        for fact in pinned_facts[:8]:
            key = fact.key.lower()
            if "prefer" in key or "preferred" in key:
                preferences[fact.key] = fact.value
        recent_text = " ".join(str(getattr(message, "content", "") or "").lower() for message in recent_messages[-6:])
        if any(term in recent_text for term in ("brief", "concise", "short answer")):
            preferences["response_length"] = "concise"
        elif any(term in recent_text for term in ("detailed", "deep dive", "full detail")):
            preferences["response_length"] = "detailed"
        return preferences

    def _infer_active_topic(
        self,
        *,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        latest_prompt: str | None,
    ) -> str:
        recent_messages = list(getattr(thread, "messages", []) or [])
        candidates = [latest_prompt or ""]
        for message in reversed(recent_messages[-4:]):
            if str(getattr(message, "role", "")) == "user":
                candidates.append(str(getattr(message, "content", "") or ""))
        combined = " ".join(candidates).lower()
        for topic, keywords in self._TOPIC_KEYWORDS:
            if any(keyword in combined for keyword in keywords):
                return topic
        return page_context.payload.page_type

    def _infer_unresolved_references(
        self,
        *,
        latest_prompt: str,
        resolved_references: dict[str, str],
    ) -> list[str]:
        unresolved: list[str] = []
        normalized = latest_prompt.lower()
        if any(phrase in normalized for phrase in ("this strategy", "same strategy")) and "strategy_id" not in resolved_references:
            unresolved.append("strategy")
        if any(phrase in normalized for phrase in ("this run", "that drawdown")) and "backtest_id" not in resolved_references:
            unresolved.append("backtest")
        if any(phrase in normalized for phrase in ("previous run", "previous one")) and not any(
            key in resolved_references for key in ("previous_backtest_id", "previous_optimization_id")
        ):
            unresolved.append("previous_run")
        return unresolved

    @classmethod
    def _extract_symbols(cls, text: str) -> list[str]:
        matches = [match.upper() for match in cls._SYMBOL_PATTERN.findall(text or "")]
        filtered = [
            symbol
            for symbol in matches
            if len(symbol) >= 3 and symbol not in {"THE", "AND", "FOR", "WHY", "THIS", "THAT"}
        ]
        return list(dict.fromkeys(filtered[:4]))

    @classmethod
    def _extract_timeframes(cls, text: str) -> list[str]:
        matches = [match.upper() for match in cls._TIMEFRAME_PATTERN.findall(text or "")]
        return list(dict.fromkeys(matches[:3]))
