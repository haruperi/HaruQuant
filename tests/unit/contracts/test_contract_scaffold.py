from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPO_ROOT / "contracts"

EXPECTED_CONTRACT_FAMILIES = [
    "workflow_intent",
    "workflow_plan",
    "trade_hypothesis",
    "trade_proposal",
    "risk_assessment_request",
    "risk_assessment_decision",
    "execution_intent",
    "execution_receipt",
    "observation_event",
    "evaluation_report",
    "incident_alert",
    "override_request",
    "override_decision",
    "replay_bundle",
]

EXPECTED_FILES = [
    "README.md",
    "CHANGELOG.md",
    "schema.json",
    "model.py",
]


def test_contract_family_scaffolds_exist():
    for family in EXPECTED_CONTRACT_FAMILIES:
        family_root = CONTRACTS_ROOT / family

        assert family_root.is_dir(), f"missing contract family directory: {family}"

        for filename in EXPECTED_FILES:
            assert (family_root / filename).is_file(), f"missing {filename} in {family}"

        assert (family_root / "examples" / "valid").is_dir(), f"missing valid examples dir in {family}"
        assert (family_root / "examples" / "invalid").is_dir(), f"missing invalid examples dir in {family}"
