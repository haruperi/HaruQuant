"""Shared exceptions for HaruQuant agents."""

from __future__ import annotations


class AgentError(Exception):
    """Base error for agent runtime failures."""


class AgentPolicyError(AgentError):
    """Raised when an agent request violates deterministic policy."""


class AgentEvidenceError(AgentError):
    """Raised when required evidence is missing or invalid."""


__all__ = ["AgentError", "AgentEvidenceError", "AgentPolicyError"]
