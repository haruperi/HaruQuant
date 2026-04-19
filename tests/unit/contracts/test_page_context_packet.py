from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.page_context_packet.model import (
    ContextAuthority,
    ContextFreshness,
    ContextSummary,
    PageContextPacket,
    PageContextPayload,
)


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "backend" / "contracts" / "page_context_packet" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_page_context_packet_accepts_valid_example():
    contract = PageContextPacket.model_validate(_load_example("valid", "strategy_detail.json"))

    assert contract.contract_type == "PageContextPacket"
    assert contract.payload.page_type == "strategy_detail"
    assert contract.payload.entity_refs[0].type == "strategy"


def test_page_context_packet_rejects_invalid_page_type():
    with pytest.raises(ValidationError):
        PageContextPacket.model_validate(_load_example("invalid", "bad_page_type.json"))


def test_page_context_payload_requires_route():
    with pytest.raises(ValidationError):
        PageContextPayload(
            route="",
            page_type="generic",
            context_revision="ctx_001",
            freshness=ContextFreshness(
                observed_at="2026-04-19T12:00:00Z",
                staleness_seconds=0,
            ),
            authority=ContextAuthority(source="svc", trust_level="fallback"),
            summary=ContextSummary(headline="Fallback", bullets=[]),
            payload={},
        )
