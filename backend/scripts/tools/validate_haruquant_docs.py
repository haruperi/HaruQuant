from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = REPO_ROOT / "docs" / "haruquant"

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

REQUIRED_CANONICAL_FILES = [
    "docs/haruquant/README.md",
    "docs/haruquant/Playbook.md",
    "docs/haruquant/agents/Catalog.md",
    "docs/haruquant/workflows/Catalog.md",
    "docs/haruquant/tools/Tool_Catalog.md",
    "docs/haruquant/plans/ND881_Implementation_Plan.md",
    "docs/haruquant/traceability/AI_Trading_Traceability.md",
]

STALE_FILE_NAMES = [
    "Agentic_AI_Playbook.md",
    "Agent_Catalog.md",
    "Workflow_Catalog.md",
    "Tool_Resource_Prompt_Catalog.md",
    "Approval_and_Escalation_Standard.md",
    "Design_Specification_System_Architecture.md",
    "Software_Requirements_Specification.md",
    "Security_Architecture.md",
    "Observability_and_Audit_Spec.md",
    "Benchmark_and_Eval_Spec.md",
    "HaruQuant_ND881_Implementation_Plan.md",
    "Lesson_2_Unsupervised_Learning_Implementation_Plan.md",
    "Strategy_Catalog_Agentic_Reconciliation_Implementation_Plan.md",
    "AI_Trading_Strategies_Traceability_Register.md",
]


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("tel:")
    )


def strip_anchor(target: str) -> str:
    return target.split("#", 1)[0].strip()


def normalize_repo_absolute(target: str) -> Path | None:
    path = Path(target)
    try:
        path.resolve()
    except OSError:
        return None
    try:
        path.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return path


def resolve_link(source_file: Path, target: str) -> Path | None:
    cleaned = strip_anchor(target)
    if not cleaned or is_external_link(cleaned):
        return None
    if cleaned.startswith("#"):
        return None

    path = normalize_repo_absolute(cleaned)
    if path is not None:
        return path

    candidate = (source_file.parent / cleaned).resolve()
    return candidate


def validate_required_files() -> list[str]:
    issues: list[str] = []
    for rel_path in REQUIRED_CANONICAL_FILES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            issues.append(f"missing canonical file: {rel_path}")
    return issues


def validate_stale_references(markdown_files: list[Path]) -> list[str]:
    issues: list[str] = []
    for file_path in markdown_files:
        content = file_path.read_text(encoding="utf-8")
        for stale_name in STALE_FILE_NAMES:
            if stale_name in content:
                rel_path = file_path.relative_to(REPO_ROOT)
                issues.append(f"stale canonical reference in {rel_path}: {stale_name}")
    return issues


def validate_links(markdown_files: list[Path]) -> list[str]:
    issues: list[str] = []
    for file_path in markdown_files:
        content = file_path.read_text(encoding="utf-8")
        rel_path = file_path.relative_to(REPO_ROOT)
        for _, raw_target in MARKDOWN_LINK_RE.findall(content):
            target = raw_target.strip()
            if not target or target.startswith("#") or is_external_link(target):
                continue

            resolved = resolve_link(file_path, target)
            if resolved is None:
                continue
            if not resolved.exists():
                issues.append(f"broken link in {rel_path}: {target}")
    return issues


def main() -> int:
    if not DOCS_ROOT.exists():
        print("docs root missing: docs/haruquant")
        return 1

    markdown_files = sorted(DOCS_ROOT.rglob("*.md"))
    issues: list[str] = []
    issues.extend(validate_required_files())
    issues.extend(validate_stale_references(markdown_files))
    issues.extend(validate_links(markdown_files))

    if issues:
        print("HaruQuant docs validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"HaruQuant docs validation passed: {len(markdown_files)} markdown files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
