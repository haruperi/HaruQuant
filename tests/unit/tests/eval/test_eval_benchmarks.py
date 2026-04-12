"""Tests for evaluation benchmark file loading."""

from __future__ import annotations

import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "eval"


def _load_json_lines(path: Path) -> list[dict]:
    items = []
    for line in path.read_text().strip().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def test_golden_tasks_exist() -> None:
    golden = EVAL_DIR / "golden_tasks"
    assert golden.is_dir()
    files = list(golden.glob("*.json"))
    assert len(files) >= 3


def test_adversarial_tasks_exist() -> None:
    adv = EVAL_DIR / "adversarial_tasks"
    assert adv.is_dir()
    files = list(adv.glob("*.json"))
    assert len(files) >= 3


def test_regression_tasks_exist() -> None:
    reg = EVAL_DIR / "regression_tasks"
    assert reg.is_dir()
    files = list(reg.glob("*.json"))
    assert len(files) >= 1


def test_domain_hard_cases_exist() -> None:
    hard = EVAL_DIR / "domain_hard_cases"
    assert hard.is_dir()
    files = list(hard.glob("*.json"))
    assert len(files) >= 1


def test_promotion_criteria_exists() -> None:
    pc = EVAL_DIR / "promotion_criteria.yaml"
    assert pc.is_file()
    content = pc.read_text()
    assert "regression_pass" in content
    assert "benchmark_pass" in content


def test_golden_tasks_are_valid_json() -> None:
    golden = EVAL_DIR / "golden_tasks"
    for f in golden.glob("*.json"):
        items = _load_json_lines(f)
        assert len(items) > 0
        for item in items:
            assert "name" in item
            assert "input" in item
            assert "expected" in item


def test_adversarial_tasks_are_valid_json() -> None:
    adv = EVAL_DIR / "adversarial_tasks"
    for f in adv.glob("*.json"):
        items = _load_json_lines(f)
        assert len(items) > 0
        for item in items:
            assert "name" in item
            assert "should_reject" in item.get("expected", {}) or "should_escalate" in item.get("expected", {})
