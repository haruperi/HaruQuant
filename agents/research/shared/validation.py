"""Validation helpers for Research Department agents."""

from __future__ import annotations

from agents._shared.base_contracts import AgentRequest
from .contracts import ResearchRequestPayload
from .timeframes import invalid_timeframes, normalize_timeframes


def parse_research_payload(request: AgentRequest) -> ResearchRequestPayload:
    payload = ResearchRequestPayload(**request.payload)
    if not payload.symbol and payload.symbols:
        payload.symbol = payload.symbols[0]
    normalized = normalize_timeframes(payload.timeframes or payload.timeframe)
    invalid = invalid_timeframes(normalized)
    if invalid:
        raise ValueError(f"Unsupported timeframe(s): {', '.join(invalid)}")
    payload.timeframes = normalized
    payload.timeframe = normalized[0]
    return payload
