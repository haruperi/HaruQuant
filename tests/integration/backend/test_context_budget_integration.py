"""Integration tests for context budget enforcement (Playbook §9.4)."""

from __future__ import annotations

from backend_retiring.orchestration.context_engineering.budget import ContextBudget
from backend_retiring.orchestration.context_engineering.compression import ContextCompression
from backend_retiring.orchestration.context_engineering.validator import ContextValidator


def test_context_budget_enforced_across_steps():
    """Context budget is enforced across multiple workflow steps."""
    budget = ContextBudget(max_tokens=1000, reserved_tokens=0, per_step_budget=200)

    steps = [100, 200, 300, 250]
    for tokens in steps:
        assert budget.allocate(tokens) is True

    # 850 used, 150 available. Next step of 200 exceeds budget
    assert budget.allocate(200) is False
    # But 150 would fit
    assert budget.allocate(150) is True


def test_compression_keeps_within_budget():
    """Compression reduces context to fit within budget."""
    budget = ContextBudget(max_tokens=10, reserved_tokens=0)
    compressor = ContextCompression(max_items=5, abstraction_levels=2)

    # Create oversized context
    items = [{"token": f"t{i}"} for i in range(20)]
    compressed = compressor.compress(items)
    assert len(compressed) <= 5


def test_validator_rejects_oversized_context():
    """Validator rejects context that is too verbose."""
    validator = ContextValidator()
    large_context = {"data": "x" * 40000}
    issues = validator.validate(large_context)
    assert "context too verbose" in issues
