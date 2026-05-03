"""Phase 0 AI chatbot contracts and service scaffolds."""

from .agent_router import ChatAgentRouter, ChatRouteDecision
from .agent_consultation_service import AgentConsultationService
from .ai_gateway import AIGatewayService, ChatStreamRequest
from .clarification_policy import ClarificationDecision, ClarificationPolicy
from .conversation_orchestrator import ConversationOrchestrator
from .conversation_planner import ConversationPlanner, RuntimeLLMPlannerClient, StructuredChatPlan
from .artifact_service import ChatArtifact, ChatArtifactService, ChatArtifactValidation
from .page_action_planner import PageActionPlanner, PageActionPlanningResult
from .conversation_state_service import ConversationStateService
from .conversation_service import ConversationService
from .context_service import (
    DEFAULT_ROUTE_CONTEXT_REGISTRY,
    PageContextAssembler,
    RouteContextDescriptor,
)
from .prompt_builder import BuiltPrompt, ChatPromptBuilder
from .response_composer import ResponseComposer
from .models import (
    ActionDraftRecord,
    ChatToolAttachment,
    ConversationPlan,
    ConversationEntityState,
    ConversationMessageRecord,
    ConversationThreadRecord,
    ConversationState,
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
from .tool_attachment_registry import ChatToolAttachmentRegistry, ChatToolDefinition
from .tool_attachment_runtime import ChatToolAttachmentRuntime

__all__ = [
    "ALLOWED_TIERS_BY_AUTHORITY_BAND",
    "ActionDraftRecord",
    "AgentConsultationService",
    "AIGatewayService",
    "AuthorityBand",
    "BuiltPrompt",
    "ChatAgentRouter",
    "ChatPromptBuilder",
    "ChatResponseMode",
    "ChatRouteDecision",
    "ChatStreamManager",
    "ChatStreamRequest",
    "ChatToolAttachment",
    "ChatToolAttachmentRegistry",
    "ChatToolAttachmentRuntime",
    "ChatToolDefinition",
    "ClarificationDecision",
    "ClarificationPolicy",
    "ConversationOrchestrator",
    "ConversationPlanner",
    "ChatArtifact",
    "ChatArtifactService",
    "ChatArtifactValidation",
    "PageActionPlanner",
    "PageActionPlanningResult",
    "ConversationEntityState",
    "ConversationPlan",
    "ConversationState",
    "ConversationStateService",
    "ConversationService",
    "ConversationMessageRecord",
    "ConversationThreadRecord",
    "DEFAULT_ROUTE_CONTEXT_REGISTRY",
    "MemorySummary",
    "PageContextAssembler",
    "PinnedFact",
    "RouteContextDescriptor",
    "ResponseComposer",
    "RuntimeLLMPlannerClient",
    "SignalProposalRecord",
    "StructuredChatPlan",
    "ToolPermissionTier",
]
