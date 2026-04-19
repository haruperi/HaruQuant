"""Phase 0 contract-freeze endpoints for the AI chatbot."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.ai_chat import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AuthorityBand,
    PageContextAssembler,
)


router = APIRouter()


@router.get("/phase0/contracts")
def get_ai_chat_phase0_contracts() -> dict:
    """Expose frozen Phase 0 contract metadata for implementation alignment."""

    return {
        "feature": "haruquant_ai_chatbot",
        "phase": 0,
        "contracts": {
            "page_context": "PageContextPacket@1.0.0",
            "chat_event": "ChatLifecycleEvent@1.0.0",
            "conversation_thread_model": "ConversationThreadRecord",
        },
        "authority_bands": {
            band.value: [tier.value for tier in ALLOWED_TIERS_BY_AUTHORITY_BAND[band]]
            for band in AuthorityBand
        },
        "supported_page_types": sorted(
            {
                descriptor.page_type
                for descriptor in PageContextAssembler().registry
            }
            | {"generic"}
        ),
    }


@router.get("/phase0/route-contexts")
def get_ai_chat_route_contexts() -> list[dict[str, str]]:
    """Expose the frozen route-to-context registry for page-aware assembly."""

    assembler = PageContextAssembler()
    return [
        {
            "route_pattern": descriptor.route_pattern,
            "page_type": descriptor.page_type,
            "builder_name": descriptor.builder_name,
        }
        for descriptor in assembler.registry
    ]
