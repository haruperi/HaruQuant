"""AI chat service exports.

Exports are resolved lazily so low-level modules can import
`backend_retiring.agents.chat.ai_chat.models` without importing the full gateway/tool stack.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "ActionDraftRecord": (".models", "ActionDraftRecord"),
    "AgentConsultationService": (".agent_consultation_service", "AgentConsultationService"),
    "AIGatewayService": (".ai_gateway", "AIGatewayService"),
    "AuthorityBand": (".policy", "AuthorityBand"),
    "BuiltPrompt": (".prompt_builder", "BuiltPrompt"),
    "CEOChatOrchestrator": (".ceo_chat_orchestrator", "CEOChatOrchestrator"),
    "CEOChatTurnResult": (".ceo_chat_orchestrator", "CEOChatTurnResult"),
    "ChatAgentRouter": (".agent_router", "ChatAgentRouter"),
    "ChatArtifact": (".artifact_service", "ChatArtifact"),
    "ChatArtifactService": (".artifact_service", "ChatArtifactService"),
    "ChatArtifactValidation": (".artifact_service", "ChatArtifactValidation"),
    "ChatPromptBuilder": (".prompt_builder", "ChatPromptBuilder"),
    "ChatResponseMode": (".policy", "ChatResponseMode"),
    "ChatRouteDecision": (".agent_router", "ChatRouteDecision"),
    "ChatStreamManager": (".stream_manager", "ChatStreamManager"),
    "ChatStreamRequest": (".ai_gateway", "ChatStreamRequest"),
    "ChatToolAttachment": (".models", "ChatToolAttachment"),
    "ChatToolAttachmentRegistry": (".tool_attachment_registry", "ChatToolAttachmentRegistry"),
    "ChatToolAttachmentRuntime": (".tool_attachment_runtime", "ChatToolAttachmentRuntime"),
    "ChatToolDefinition": (".tool_attachment_registry", "ChatToolDefinition"),
    "ClarificationDecision": (".clarification_policy", "ClarificationDecision"),
    "ClarificationPolicy": (".clarification_policy", "ClarificationPolicy"),
    "ConversationEntityState": (".models", "ConversationEntityState"),
    "ConversationMessageRecord": (".models", "ConversationMessageRecord"),
    "ConversationOrchestrator": (".conversation_orchestrator", "ConversationOrchestrator"),
    "ConversationPlan": (".models", "ConversationPlan"),
    "ConversationPlanner": (".conversation_planner", "ConversationPlanner"),
    "ConversationService": (".conversation_service", "ConversationService"),
    "ConversationState": (".models", "ConversationState"),
    "ConversationStateService": (".conversation_state_service", "ConversationStateService"),
    "ConversationThreadRecord": (".models", "ConversationThreadRecord"),
    "DEFAULT_ROUTE_CONTEXT_REGISTRY": (".context_service", "DEFAULT_ROUTE_CONTEXT_REGISTRY"),
    "MemorySummary": (".models", "MemorySummary"),
    "PageActionPlanner": (".page_action_planner", "PageActionPlanner"),
    "PageActionPlanningResult": (".page_action_planner", "PageActionPlanningResult"),
    "PageContextAssembler": (".context_service", "PageContextAssembler"),
    "PinnedFact": (".models", "PinnedFact"),
    "ResponseComposer": (".response_composer", "ResponseComposer"),
    "RouteContextDescriptor": (".context_service", "RouteContextDescriptor"),
    "RuntimeLLMPlannerClient": (".conversation_planner", "RuntimeLLMPlannerClient"),
    "SignalProposalRecord": (".models", "SignalProposalRecord"),
    "StructuredChatPlan": (".conversation_planner", "StructuredChatPlan"),
    "ToolPermissionTier": (".policy", "ToolPermissionTier"),
    "ALLOWED_TIERS_BY_AUTHORITY_BAND": (".policy", "ALLOWED_TIERS_BY_AUTHORITY_BAND"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard module protocol
        raise AttributeError(name) from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = sorted(_EXPORTS)
