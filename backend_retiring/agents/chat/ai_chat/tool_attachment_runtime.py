"""Runtime helpers for applying attached chat tools to a turn."""

from __future__ import annotations

from backend_retiring.contracts.page_context_packet.model import PageContextPacket
from backend_retiring.agents.chat.ai_chat.models import ChatToolAttachment
from backend_retiring.agents.chat.ai_chat.tool_attachment_registry import ChatToolAttachmentRegistry


class ChatToolAttachmentRuntime:
    """Resolve selected chat tools and compute their context status."""

    def __init__(self, registry: ChatToolAttachmentRegistry | None = None) -> None:
        self.registry = registry or ChatToolAttachmentRegistry()

    def resolve_attachments(
        self,
        *,
        selected_tool_ids: list[str] | tuple[str, ...],
        page_context: PageContextPacket,
        tool_context: dict[str, object],
    ) -> list[ChatToolAttachment]:
        attachments: list[ChatToolAttachment] = []
        for definition in self.registry.resolve(selected_tool_ids):
            missing_context = [
                required
                for required in definition.required_context
                if not self._has_context(required, page_context=page_context, tool_context=tool_context)
            ]
            attachments.append(definition.to_attachment(missing_context=missing_context))
        return attachments

    @staticmethod
    def collect_backend_tools(attachments: list[ChatToolAttachment]) -> tuple[str, ...]:
        tools: list[str] = []
        for attachment in attachments:
            tools.extend(attachment.allowed_backend_tools)
        return tuple(dict.fromkeys(tools))

    @staticmethod
    def system_prompt_fragment(attachments: list[ChatToolAttachment]) -> str:
        if not attachments:
            return "No chat tools are attached."
        lines = ["Attached chat tools:"]
        for attachment in attachments:
            missing = (
                f" Missing required context: {', '.join(attachment.missing_context)}."
                if attachment.missing_context
                else ""
            )
            lines.append(
                f"- {attachment.display_name} ({attachment.capability_type}, {attachment.side_effect_policy}): "
                f"{attachment.system_prompt_fragment}{missing}"
            )
        return "\n".join(lines)

    @staticmethod
    def _has_context(required: str, *, page_context: PageContextPacket, tool_context: dict[str, object]) -> bool:
        if required in tool_context:
            return bool(tool_context.get(required))
        if required == "page_intelligence.actionAffordances":
            page_intelligence = page_context.payload.payload.get("page_intelligence")
            return (
                isinstance(page_intelligence, dict)
                and isinstance(page_intelligence.get("actionAffordances"), list)
                and len(page_intelligence["actionAffordances"]) > 0
            )
        if required.startswith("page_intelligence."):
            key = required.split(".", 1)[1]
            page_intelligence = page_context.payload.payload.get("page_intelligence")
            return isinstance(page_intelligence, dict) and bool(page_intelligence.get(key))
        return False


__all__ = ["ChatToolAttachmentRuntime"]
