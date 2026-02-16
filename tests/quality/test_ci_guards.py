"""Quality guardrails for Phase 0.1 repository/toolchain baseline.

These tests are intentionally lightweight and file-based so they run fast in CI
and fail early when foundational project wiring regresses.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_canonical_repository_layout_exists() -> None:
    required_dirs = ["apps", "cpp", "bridge", "config", "scripts", "docs", "tests"]
    missing = [name for name in required_dirs if not (REPO_ROOT / name).is_dir()]
    assert not missing, f"Missing required top-level directories: {missing}"


def test_cpp_build_files_exist() -> None:
    assert (REPO_ROOT / "CMakeLists.txt").is_file(), "Missing root CMakeLists.txt"
    assert (REPO_ROOT / "cpp" / "CMakeLists.txt").is_file(), "Missing cpp/CMakeLists.txt"


def test_python_packaging_and_typecheck_config_exist() -> None:
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.is_file(), "Missing pyproject.toml"

    content = _read(pyproject)
    assert "[project]" in content, "pyproject.toml must define [project]"
    assert 'name = "haruquant"' in content, "pyproject.toml must define project name"
    assert "[tool.black]" in content, "pyproject.toml must define [tool.black]"
    assert "[tool.mypy]" in content, "pyproject.toml must define [tool.mypy]"


def test_lint_stack_has_black_plus_mypy_and_linter() -> None:
    pyproject = _read(REPO_ROOT / "pyproject.toml")
    precommit_path = REPO_ROOT / ".pre-commit-config.yaml"
    precommit = _read(precommit_path) if precommit_path.is_file() else ""
    flake8_cfg_exists = (REPO_ROOT / ".flake8").is_file()

    # Linter requirement can be satisfied by ruff or flake8-based setup.
    has_ruff = "[tool.ruff]" in pyproject or "id: ruff" in precommit
    has_flake8 = flake8_cfg_exists or "id: flake8" in precommit

    assert "[tool.black]" in pyproject
    assert "[tool.mypy]" in pyproject
    assert has_ruff or has_flake8, "Expected either ruff or flake8 lint configuration"


def test_pre_commit_quality_gates_exist() -> None:
    precommit = REPO_ROOT / ".pre-commit-config.yaml"
    assert precommit.is_file(), "Missing .pre-commit-config.yaml"
    content = _read(precommit)

    expected_hooks = ["id: black", "id: isort", "id: mypy"]
    missing = [hook for hook in expected_hooks if hook not in content]
    assert not missing, f"Missing expected pre-commit hooks: {missing}"


def test_ci_or_build_entrypoints_present() -> None:
    """Accept hosted CI config or local build entrypoints used by CI wrappers."""
    candidates = [
        REPO_ROOT / ".github" / "workflows",
        REPO_ROOT / "azure-pipelines.yml",
        REPO_ROOT / ".gitlab-ci.yml",
        REPO_ROOT / "appveyor.yml",
        REPO_ROOT / "Jenkinsfile",
        REPO_ROOT / "scripts" / "build_cpp.py",
    ]
    assert any(path.exists() for path in candidates), (
        "Expected CI configuration or build entrypoint (e.g. scripts/build_cpp.py)"
    )
