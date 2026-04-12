from __future__ import annotations

import pytest

from backend.common.ids import generate_id, generate_prefixed_id


def test_generate_prefixed_id_uses_prefix_format():
    value = generate_prefixed_id("wf")

    assert value.startswith("wf_")
    assert value == value.lower()
    assert len(value.split("_", 1)[1]) == 16


def test_generate_id_uses_canonical_prefixes():
    workflow_id = generate_id("workflow")
    receipt_id = generate_id("receipt")

    assert workflow_id.startswith("wf_")
    assert receipt_id.startswith("rcpt_")


def test_generate_id_returns_unique_values():
    values = {generate_id("correlation") for _ in range(10)}

    assert len(values) == 10


def test_generate_id_rejects_unknown_kind():
    with pytest.raises(ValueError):
        generate_id("unknown")
