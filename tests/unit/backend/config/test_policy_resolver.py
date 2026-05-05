"""Tests for backend_retiring/config/policies PolicyResolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend_retiring.config.policies import (
    EnforcementLayer,
    FailureBehavior,
    LoggingRequirement,
    PolicyConfig,
    PolicyResolver,
)


@pytest.fixture
def policy_dir(tmp_path: Path) -> Path:
    """Create a temporary policy directory with test files."""
    d = tmp_path / "policies"
    d.mkdir()
    (d / "test_exec.yaml").write_text(
        "policy_name: test_execution\n"
        "scope: execution_workflows\n"
        "owner: risk_team\n"
        "enforcement_layers:\n"
        "  - routing\n"
        "  - orchestrator\n"
        "failure_behavior: reject_and_escalate\n"
        "logging_requirement: audit_log_required\n"
        "exception_process: risk_committee_approval\n"
        "review_cadence: monthly\n"
    )
    (d / "test_data.yaml").write_text(
        "policy_name: test_data\n"
        "scope: data_workflows\n"
        "owner: data_team\n"
        "enforcement_layers:\n"
        "  - mcp_server\n"
        "failure_behavior: reject_and_log\n"
        "logging_requirement: standard_log\n"
        "exception_process: data_owner_approval\n"
        "review_cadence: quarterly\n"
    )
    return d


def test_load_all_policies(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    assert len(resolver.policies) == 2
    assert "test_execution" in resolver.policies
    assert "test_data" in resolver.policies


def test_policy_config_fields(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    p = resolver.get_by_name("test_execution")
    assert p is not None
    assert p.scope == "execution_workflows"
    assert p.owner == "risk_team"
    assert p.failure_behavior == FailureBehavior.REJECT_AND_ESCALATE
    assert p.logging_requirement == LoggingRequirement.AUDIT_LOG_REQUIRED
    assert len(p.enforcement_layers) == 2


def test_resolve_for_scope(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    policies = resolver.resolve_for_scope("execution_workflows")
    assert len(policies) == 1
    assert policies[0].policy_name == "test_execution"


def test_resolve_for_scope_no_match(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    policies = resolver.resolve_for_scope("nonexistent_scope")
    assert len(policies) == 0


def test_should_enforce(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    policies = resolver.should_enforce(
        "execution_workflows", EnforcementLayer.ROUTING
    )
    assert len(policies) == 1


def test_should_enforce_no_match(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    policies = resolver.should_enforce(
        "execution_workflows", EnforcementLayer.STORAGE
    )
    assert len(policies) == 0


def test_on_failure(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    fb = resolver.on_failure("execution_workflows")
    assert fb == FailureBehavior.REJECT_AND_ESCALATE


def test_on_failure_no_match(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    fb = resolver.on_failure("nonexistent_scope")
    assert fb is None


def test_reload(policy_dir: Path) -> None:
    resolver = PolicyResolver(policy_dir)
    assert len(resolver.policies) == 2
    resolver.reload()
    assert len(resolver.policies) == 2


def test_invalid_yaml_skipped(tmp_path: Path) -> None:
    d = tmp_path / "policies"
    d.mkdir()
    (d / "bad.yaml").write_text("not: valid: yaml: :\n")
    resolver = PolicyResolver(d)
    assert len(resolver.policies) == 0


def test_non_dict_yaml_skipped(tmp_path: Path) -> None:
    d = tmp_path / "policies"
    d.mkdir()
    (d / "bad.yaml").write_text("- just\n- a\n- list\n")
    resolver = PolicyResolver(d)
    assert len(resolver.policies) == 0


def test_missing_directory() -> None:
    resolver = PolicyResolver(Path("/nonexistent/path/that/does/not/exist"))
    assert len(resolver.policies) == 0
