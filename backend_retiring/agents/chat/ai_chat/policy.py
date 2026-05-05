"""Phase 0 policy enums and frozen capability bands for the AI chatbot."""

from __future__ import annotations

from enum import Enum


class ToolPermissionTier(str, Enum):
    READ_ONLY = "T1_READ_ONLY"
    SIMULATED = "T2_SIMULATED"
    DRAFT_ACTION = "T3_DRAFT_ACTION"
    LIVE_ACTION = "T4_LIVE_ACTION"


class ChatResponseMode(str, Enum):
    ANSWER = "answer"
    TOOL_ASSISTED = "tool_assisted"
    SIGNAL_PROPOSAL = "signal_proposal"
    ACTION_DRAFT = "action_draft"


class AuthorityBand(str, Enum):
    READ_ONLY = "read_only"
    SIGNAL_ONLY = "signal_only"
    SUPERVISED_DRAFTS = "supervised_drafts"
    PAPER_AUTOMATION = "paper_automation"
    LIVE_EXECUTION_PROHIBITED = "live_execution_prohibited"


ALLOWED_TIERS_BY_AUTHORITY_BAND: dict[AuthorityBand, tuple[ToolPermissionTier, ...]] = {
    AuthorityBand.READ_ONLY: (ToolPermissionTier.READ_ONLY,),
    AuthorityBand.SIGNAL_ONLY: (ToolPermissionTier.READ_ONLY,),
    AuthorityBand.SUPERVISED_DRAFTS: (
        ToolPermissionTier.READ_ONLY,
        ToolPermissionTier.DRAFT_ACTION,
    ),
    AuthorityBand.PAPER_AUTOMATION: (
        ToolPermissionTier.READ_ONLY,
        ToolPermissionTier.SIMULATED,
        ToolPermissionTier.DRAFT_ACTION,
    ),
    AuthorityBand.LIVE_EXECUTION_PROHIBITED: (),
}


__all__ = [
    "ALLOWED_TIERS_BY_AUTHORITY_BAND",
    "AuthorityBand",
    "ChatResponseMode",
    "ToolPermissionTier",
]
