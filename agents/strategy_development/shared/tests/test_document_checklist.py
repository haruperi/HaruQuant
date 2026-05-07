from __future__ import annotations

from pathlib import Path


def test_strategy_creation_department_checklist_is_complete():
    doc = Path("docs/agentic_firm/strategy_creation_department.md").read_text(
        encoding="utf-8"
    )

    assert "* [ ]" not in doc
