"""Static code quality rules for Strategy Creation Department."""

from __future__ import annotations

from .constants import FORBIDDEN_CODE_MARKERS, REQUIRED_STRATEGY_FILES, STANDARD_SIGNAL_COLUMNS


def detect_forbidden_markers(files: dict[str, str]) -> list[str]:
    found: list[str] = []
    combined = "\n".join(files.values())
    for marker in FORBIDDEN_CODE_MARKERS:
        if marker in combined:
            found.append(marker)
    return found


def missing_required_files(file_manifest: list[str]) -> list[str]:
    return [path for path in REQUIRED_STRATEGY_FILES if path not in file_manifest]
