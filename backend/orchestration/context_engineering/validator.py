"""Context inclusion checklist validator (Playbook §9.4)."""

from __future__ import annotations

from typing import Any, Dict, List


class ContextValidator:
    """Validate context before sending to a model (Playbook §9.4)."""

    def validate(self, context: Dict[str, Any]) -> List[str]:
        """Return list of validation issues (empty = valid)."""
        issues: List[str] = []
        if not context:
            issues.append("context is empty")
            return issues

        if len(str(context)) > 32000:
            issues.append("context too verbose")

        keys = list(context.keys())
        if len(keys) != len(set(keys)):
            issues.append("context has duplicated keys")

        return issues

    def checklist(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """Run inclusion checklist."""
        return {
            "is_necessary": len(context) > 0,
            "is_fresh": context.get("_timestamp", 0) > 0,
            "is_trusted": context.get("_source_trust_level", 0) < 5,
            "not_duplicated": len(context) == len(set(context.keys())),
            "not_too_verbose": len(str(context)) <= 32000,
            "no_higher_priority_conflict": not context.get("_conflict_detected", False),
        }
