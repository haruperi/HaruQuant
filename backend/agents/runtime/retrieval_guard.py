"""Comprehensive safety checks for retrieved research context.

Detects prompt injection, command injection, encoding tricks, social
engineering, and contamination markers across 6 threat categories.
Each detected pattern is classified by severity (low/medium/high).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.common.logger import logger

# ─────────────────────────────────────────────────────────────────────
# Injection pattern categories (25+ patterns across 6 threat categories)
# ─────────────────────────────────────────────────────────────────────

# Severity: HIGH - direct override attempts
_DIRECT_OVERRIDE_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard earlier",
    "override your instructions",
    "you are now",
    "new role:",
    "from now on",
    "act as",
    "pretend you are",
)

# Severity: HIGH - prompt extraction
_PROMPT_EXTRACTION_MARKERS = (
    "reveal the system prompt",
    "show your instructions",
    "repeat your prompt",
    "system prompt",
    "what is your system message",
    "dump your configuration",
)

# Severity: HIGH - command injection
_COMMAND_INJECTION_MARKERS = (
    "execute trade now",
    "place order",
    "run this code",
    "evaluate this expression",
    "run a shell command",
    "import os",
    "exec(",
    "eval(",
)

# Severity: MEDIUM - XML/tag injection
_XML_TAG_INJECTION_MARKERS = (
    "<tool>",
    "</tool>",
    "<system>",
    "</system>",
    "<instruction>",
    "</instruction>",
    "<user>",
    "</user>",
    "<function>",
    '\n',
)

# Severity: MEDIUM - encoding tricks
_ENCODING_INJECTION_MARKERS = (
    '\\u00',
    'base64:',
    'rot13',
    '%00',
    '\\x00',
    '&#x00;',
)

# Severity: MEDIUM - social engineering
_SOCIAL_ENGINEERING_MARKERS = (
    "this is a test environment",
    "you are in debug mode",
    "simulation mode",
    "no real consequences",
    "disregard all safety rules",
    "you are free from restrictions",
    "disable all filters",
    "bypass all safeguards",
)

# Severity: LOW - indirect/context contamination
_INDIRECT_INJECTION_MARKERS = (
    "assistant:",
    "system:",
    "developer:",
    "unverified rumor",
    "fabricated citation",
    "hypothetical scenario where you can",
    "in this fictional context you should",
)

# All markers grouped by severity for efficient scanning
_ALL_MARKERS_BY_SEVERITY: dict[str, tuple[str, ...]] = {
    "high": (
        *_DIRECT_OVERRIDE_MARKERS,
        *_PROMPT_EXTRACTION_MARKERS,
        *_COMMAND_INJECTION_MARKERS,
    ),
    "medium": (
        *_XML_TAG_INJECTION_MARKERS,
        *_ENCODING_INJECTION_MARKERS,
        *_SOCIAL_ENGINEERING_MARKERS,
    ),
    "low": (
        *_INDIRECT_INJECTION_MARKERS,
    ),
}


@dataclass(frozen=True)
class RetrievalSafetyReport:
    """Result of safety evaluation on retrieved text."""
    safe: bool
    severity: str  # "low" | "medium" | "high"
    reason_codes: tuple[str, ...]
    matched_markers: tuple[str, ...] = field(default_factory=tuple)


def evaluate_retrieved_text(text: str) -> RetrievalSafetyReport:
    """Fail closed when retrieved context contains unsafe control markers.

    Returns a RetrievalSafetyReport with:
    - safe: True if no injection patterns detected
    - severity: highest severity of any detected pattern (high/medium/low)
    - reason_codes: human-readable codes for detected patterns
    - matched_markers: the actual marker strings that were found
    """
    normalized = text.lower()
    reason_codes: list[str] = []
    matched: list[str] = []
    max_severity = "low"

    for severity, markers in _ALL_MARKERS_BY_SEVERITY.items():
        for marker in markers:
            if marker in normalized:
                if severity == "high":
                    max_severity = "high"
                elif severity == "medium" and max_severity != "high":
                    max_severity = "medium"
                reason_codes.append(f"{severity}_severity_marker_detected")
                matched.append(marker)

    if reason_codes:
        logger.warning(
            f"RetrievalGuard: unsafe content detected, severity={max_severity}, "
            f"reasons={reason_codes[:5]}, matched={matched[:3]}"
        )

    return RetrievalSafetyReport(
        safe=not reason_codes,
        severity=max_severity if reason_codes else "none",
        reason_codes=tuple(dict.fromkeys(reason_codes)),  # dedupe
        matched_markers=tuple(dict.fromkeys(matched)),  # dedupe
    )


def get_marker_count() -> int:
    """Return total number of unique injection markers for reporting."""
    all_markers = set()
    for markers in _ALL_MARKERS_BY_SEVERITY.values():
        all_markers.update(markers)
    return len(all_markers)


def get_marker_categories() -> dict[str, int]:
    """Return counts of markers by severity for reporting."""
    return {sev: len(markers) for sev, markers in _ALL_MARKERS_BY_SEVERITY.items()}
