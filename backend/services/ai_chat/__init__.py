"""Phase 0 AI chatbot contracts and service scaffolds."""

from .agent_router import ChatAgentRouter, ChatRouteDecision
from .ai_gateway import AIGatewayService, ChatStreamRequest
from .conversation_service import ConversationService
from .context_service import (
    DEFAULT_ROUTE_CONTEXT_REGISTRY,
    PageContextAssembler,
    RouteContextDescriptor,
)
from .prompt_builder import BuiltPrompt, ChatPromptBuilder
from .models import (
    ActionDraftRecord,
    ConversationMessageRecord,
    ConversationThreadRecord,
    MemorySummary,
    PinnedFact,
    SignalProposalRecord,
)
from .policy import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AuthorityBand,
    ChatResponseMode,
    ToolPermissionTier,
)
from .stream_manager import ChatStreamManager

__all__ = [
    "ALLOWED_TIERS_BY_AUTHORITY_BAND",
    "ActionDraftRecord",
    "AIGatewayService",
    "AuthorityBand",
    "BuiltPrompt",
    "ChatAgentRouter",
    "ChatPromptBuilder",
    "ChatResponseMode",
    "ChatRouteDecision",
    "ChatStreamManager",
    "ChatStreamRequest",
    "ConversationService",
    "ConversationMessageRecord",
    "ConversationThreadRecord",
    "DEFAULT_ROUTE_CONTEXT_REGISTRY",
    "MemorySummary",
    "PageContextAssembler",
    "PinnedFact",
    "RouteContextDescriptor",
    "SignalProposalRecord",
    "ToolPermissionTier",
]
