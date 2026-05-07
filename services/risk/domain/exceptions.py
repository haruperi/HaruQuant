"""Risk Department exceptions."""

from __future__ import annotations


class RiskError(Exception):
    """Base risk error."""


class RiskConfigError(RiskError):
    """Raised when risk configuration cannot be validated."""


class RiskTokenError(RiskError):
    """Raised when approval token validation fails."""
