"""Phase 0 AI chatbot contracts and service scaffolds."""

from .context_service import (
    DEFAULT_ROUTE_CONTEXT_REGISTRY,
    PageContextAssembler,
    RouteContextDescriptor,
)
from .models import (
    ConversationMessageRecord,
    ConversationThreadRecord,
    MemorySummary,
    PinnedFact,
)
from .policy import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AuthorityBand,
    ChatResponseMode,
    ToolPermissionTier,
)

__all__ = [
    "ALLOWED_TIERS_BY_AUTHORITY_BAND",
    "AuthorityBand",
    "ChatResponseMode",
    "ConversationMessageRecord",
    "ConversationThreadRecord",
    "DEFAULT_ROUTE_CONTEXT_REGISTRY",
    "MemorySummary",
    "PageContextAssembler",
    "PinnedFact",
    "RouteContextDescriptor",
    "ToolPermissionTier",
]
