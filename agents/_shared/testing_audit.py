from __future__ import annotations

import importlib
from pathlib import Path


PERMISSION_MARKERS = (
    "blocked_actions",
    "allowed_actions",
    "permission_profile",
    "forbidden",
    "requires_board_approval",
    "RiskGovernor",
    "kill_switch",
    "policy",
)

AUDIT_MARKERS = (
    "audit",
    "evidence_refs",
    "write_json_artifact",
    "request_id",
    "workflow_id",
    "policy_version",
    "prompt_version",
    "AgentRunResult",
    "AgentResponse",
)


def agent_root_from_test(test_file: str) -> Path:
    return Path(test_file).resolve().parents[1]


def package_name(agent_root: Path) -> str:
    return ".".join(agent_root.relative_to(Path.cwd()).parts)


def module_text(agent_root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in agent_root.glob("*.py")
        if path.name != "__init__.py"
    )


def assert_permission_boundary_declared(test_file: str) -> None:
    agent_root = agent_root_from_test(test_file)
    text = module_text(agent_root)
    implementation_exists = (agent_root / "service.py").exists() or (
        agent_root / "agent.py"
    ).exists()
    assert implementation_exists
    assert (agent_root / "tests" / "test_deterministic_policy.py").exists()
    assert (agent_root / "tests" / "test_permissions.py").exists()
    assert any(marker in text for marker in PERMISSION_MARKERS) or (
        agent_root / "deterministic_policy.py"
    ).exists()


def assert_audit_or_evidence_declared(test_file: str) -> None:
    agent_root = agent_root_from_test(test_file)
    text = module_text(agent_root)
    assert (agent_root / "tests" / "test_audit.py").exists()
    assert any(marker in text for marker in AUDIT_MARKERS) or (
        agent_root / "evaluator.py"
    ).exists()


def assert_evaluator_module_declared(test_file: str) -> None:
    agent_root = agent_root_from_test(test_file)
    evaluator = agent_root / "evaluator.py"
    assert evaluator.exists()
    importlib.import_module(f"{package_name(agent_root)}.evaluator")
