"""MCP server metadata loader and validator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

from backend.common.logger import logger


class MetadataConfig(BaseModel):
    """MCP server metadata schema (Playbook §5.9)."""
    metadata_schema_version: str = Field(..., description="Schema version")
    domain: str = Field(..., description="Domain purpose")
    owner: str = Field(..., description="Team owner")
    side_effect_risk: str = Field(..., description="Side-effect risk level (A-E)")
    allowed_callers: List[str] = Field(default_factory=list, description="Allowed callers")
    credentials: List[str] = Field(default_factory=list, description="Credentials used")
    audit_requirements: str = Field("", description="Audit requirements")
    failure_modes: List[str] = Field(default_factory=list, description="Failure modes and handling")
    rate_limits: Dict[str, Any] = Field(default_factory=dict, description="Rate limits")
    timeout_budget: Dict[str, Any] = Field(default_factory=dict, description="Timeout budget")
    escalation_owner: str = Field("", description="Escalation owner")
    contract_version: str = Field("1.0.0", description="Contract version")
    deprecation_notes: Optional[str] = Field(None, description="Deprecation notes")


class MetadataLoader:
    """Load and validate MCP server metadata at startup."""

    def __init__(self, mcp_dir: Optional[Path] = None) -> None:
        if mcp_dir is None:
            mcp_dir = Path(__file__).resolve().parent
        self._mcp_dir = mcp_dir
        self._metadata: Dict[str, MetadataConfig] = {}

    @property
    def metadata(self) -> Dict[str, MetadataConfig]:
        return dict(self._metadata)

    def load_all(self) -> None:
        """Load metadata.yaml from all MCP server directories."""
        for server_dir in sorted(self._mcp_dir.iterdir()):
            if not server_dir.is_dir():
                continue
            meta_file = server_dir / "metadata.yaml"
            if meta_file.exists():
                self._load_single(server_dir.name, meta_file)

    def _load_single(self, server_name: str, path: Path) -> None:
        """Load and validate a single metadata file."""
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                logger.warning(f"Invalid metadata in {path}: not a dict")
                return
            config = MetadataConfig(**data)
            self._metadata[server_name] = config
        except (ValidationError, yaml.YAMLError) as exc:
            logger.error(f"Failed to load metadata for {server_name}: {exc}")

    def get(self, server_name: str) -> Optional[MetadataConfig]:
        """Get metadata for a specific MCP server."""
        return self._metadata.get(server_name)

    def validate_all(self) -> List[str]:
        """Validate all loaded metadata, return list of warnings."""
        warnings = []
        for name, config in self._metadata.items():
            if not config.allowed_callers:
                warnings.append(f"{name}: no allowed_callers defined")
            if not config.audit_requirements:
                warnings.append(f"{name}: no audit_requirements defined")
            if not config.failure_modes:
                warnings.append(f"{name}: no failure_modes defined")
        return warnings
