"""Tests for MCP metadata loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.mcp.metadata_loader import MetadataConfig, MetadataLoader


@pytest.fixture
def mcp_dir(tmp_path: Path) -> Path:
    """Create a temporary MCP directory with metadata files."""
    d = tmp_path / "mcp"
    d.mkdir()
    s1 = d / "test_server_a"
    s1.mkdir()
    (s1 / "metadata.yaml").write_text(
        "metadata_schema_version: '1.0'\n"
        "domain: test domain A\n"
        "owner: test_team\n"
        "side_effect_risk: A\n"
        "allowed_callers:\n"
        "  - caller1\n"
        "  - caller2\n"
        "credentials: []\n"
        "audit_requirements: all calls logged\n"
        "failure_modes:\n"
        "  - error1 -> retry\n"
        "rate_limits:\n"
        "  queries: 100/minute\n"
        "timeout_budget:\n"
        "  query: 5s\n"
        "escalation_owner: oncall\n"
        "contract_version: 1.0.0\n"
        "deprecation_notes: null\n"
    )
    s2 = d / "test_server_b"
    s2.mkdir()
    (s2 / "metadata.yaml").write_text(
        "metadata_schema_version: '1.0'\n"
        "domain: test domain B\n"
        "owner: other_team\n"
        "side_effect_risk: C\n"
        "allowed_callers:\n"
        "  - caller3\n"
        "credentials: []\n"
        "audit_requirements: standard log\n"
        "failure_modes:\n"
        "  - error2 -> fail\n"
        "rate_limits: {}\n"
        "timeout_budget: {}\n"
        "escalation_owner: other_oncall\n"
        "contract_version: 2.0.0\n"
        "deprecation_notes: deprecated in v3\n"
    )
    # Server without metadata
    s3 = d / "no_metadata_server"
    s3.mkdir()
    return d


def test_load_all(mcp_dir: Path) -> None:
    loader = MetadataLoader(mcp_dir)
    loader.load_all()
    assert len(loader.metadata) == 2
    assert "test_server_a" in loader.metadata
    assert "test_server_b" in loader.metadata


def test_metadata_config_fields(mcp_dir: Path) -> None:
    loader = MetadataLoader(mcp_dir)
    loader.load_all()
    cfg = loader.get("test_server_a")
    assert cfg is not None
    assert cfg.domain == "test domain A"
    assert cfg.owner == "test_team"
    assert cfg.side_effect_risk == "A"
    assert cfg.allowed_callers == ["caller1", "caller2"]
    assert cfg.contract_version == "1.0.0"


def test_get_nonexistent(mcp_dir: Path) -> None:
    loader = MetadataLoader(mcp_dir)
    loader.load_all()
    assert loader.get("nonexistent") is None


def test_validate_all_warnings(mcp_dir: Path) -> None:
    loader = MetadataLoader(mcp_dir)
    loader.load_all()
    warnings = loader.validate_all()
    # Both servers have all required fields, so no warnings
    assert len(warnings) == 0


def test_validate_warnings_for_incomplete(tmp_path: Path) -> None:
    d = tmp_path / "mcp"
    d.mkdir()
    s = d / "incomplete"
    s.mkdir()
    (s / "metadata.yaml").write_text(
        "metadata_schema_version: '1.0'\n"
        "domain: incomplete\n"
        "owner: nobody\n"
        "side_effect_risk: A\n"
        "credentials: []\n"
    )
    loader = MetadataLoader(d)
    loader.load_all()
    warnings = loader.validate_all()
    assert any("allowed_callers" in w for w in warnings)
    assert any("audit_requirements" in w for w in warnings)
    assert any("failure_modes" in w for w in warnings)


def test_invalid_yaml_skipped(tmp_path: Path) -> None:
    d = tmp_path / "mcp"
    d.mkdir()
    s = d / "bad"
    s.mkdir()
    (s / "metadata.yaml").write_text("not: valid: yaml: :\n")
    loader = MetadataLoader(d)
    loader.load_all()
    assert len(loader.metadata) == 0


def test_non_dict_yaml_skipped(tmp_path: Path) -> None:
    d = tmp_path / "mcp"
    d.mkdir()
    s = d / "bad"
    s.mkdir()
    (s / "metadata.yaml").write_text("- just\n- a\n- list\n")
    loader = MetadataLoader(d)
    loader.load_all()
    assert len(loader.metadata) == 0
