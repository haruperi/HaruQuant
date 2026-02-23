#!/usr/bin/env python3
"""Generate and enforce C++ coverage thresholds using gcovr JSON output."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str], cwd: Path) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _gcovr_cmd() -> list[str]:
    # Prefer module execution so PATH does not need to expose gcovr executable.
    cmd = [sys.executable, "-m", "gcovr"]
    # On Windows + Clang setups, gcov is often absent but llvm-cov is available.
    # gcovr supports "llvm-cov gcov" via --gcov-executable.
    has_gcov = shutil.which("gcov") is not None
    has_llvm_cov = shutil.which("llvm-cov") is not None
    if not has_gcov and has_llvm_cov:
        cmd.extend(["--gcov-executable", "llvm-cov gcov"])
    return cmd


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_rel(path: str | Path) -> str:
    value = str(path).replace("\\", "/")
    return value[2:] if value.startswith("./") else value


def _as_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _find_percent_for_file(report: dict[str, Any], rel_path: str) -> float | None:
    target = _normalize_rel(rel_path)
    for item in report.get("files", []):
        file_path = _normalize_rel(item.get("file", ""))
        if file_path == target:
            covered, total = _line_coverage_counts(item)
            percent = None if total <= 0 else 100.0 * covered / total
            return float(percent) if percent is not None else None
    return None


def _line_coverage_counts(file_item: dict[str, Any]) -> tuple[float, float]:
    lines = file_item.get("lines", {})
    # Older gcovr JSON format stores aggregate line stats in a dictionary.
    if isinstance(lines, dict):
        total = float(lines.get("count", 0))
        covered = float(lines.get("covered", 0))
        return covered, total

    # Newer gcovr JSON format stores per-line entries as a list.
    if isinstance(lines, list):
        line_hits: dict[int, bool] = {}
        for entry in lines:
            if not isinstance(entry, dict):
                continue
            line_number = entry.get("line_number")
            if not isinstance(line_number, int):
                continue
            count = entry.get("count", 0)
            try:
                is_covered = float(count) > 0.0
            except (TypeError, ValueError):
                is_covered = False
            line_hits[line_number] = line_hits.get(line_number, False) or is_covered
        total = float(len(line_hits))
        covered = float(sum(1 for v in line_hits.values() if v))
        return covered, total

    return 0.0, 0.0


def _overall_percent(report: dict[str, Any]) -> float | None:
    if "line_percent" in report:
        return float(report["line_percent"])

    total_lines = 0.0
    total_covered = 0.0
    for item in report.get("files", []):
        covered, total = _line_coverage_counts(item)
        total_lines += total
        total_covered += covered
    if total_lines <= 0:
        return None
    return 100.0 * total_covered / total_lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--threshold-file", default="cpp/coverage_thresholds.json")
    parser.add_argument("--global-threshold", type=float, default=None)
    parser.add_argument("--gcovr-html", default=None)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    build_dir = (root / args.build_dir).resolve()
    out_dir = build_dir / "coverage"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "coverage.json"

    gcovr_base_cmd = _gcovr_cmd() + [
        "--root",
        _as_posix(root),
        "--filter",
        _as_posix((root / "cpp").resolve()),
        "--object-directory",
        _as_posix(build_dir),
    ]

    _run(gcovr_base_cmd + ["--json", str(json_path)], cwd=root)

    if args.gcovr_html:
        html_path = Path(args.gcovr_html)
        if not html_path.is_absolute():
            html_path = (root / html_path).resolve()
        html_path.parent.mkdir(parents=True, exist_ok=True)
        _run(gcovr_base_cmd + ["--html-details", str(html_path)], cwd=root)

    report = _load_json(json_path)
    thresholds = _load_json((root / args.threshold_file).resolve())
    file_thresholds: dict[str, float] = thresholds.get("file_thresholds", {})
    config_global_threshold = thresholds.get("global_threshold")
    active_global_threshold = (
        args.global_threshold if args.global_threshold is not None else config_global_threshold
    )

    failures: list[str] = []

    overall = _overall_percent(report)
    if overall is not None:
        print(f"Overall C++ line coverage: {overall:.2f}%")
    else:
        failures.append("Could not compute overall coverage from gcovr report.")

    if active_global_threshold is not None and overall is not None and overall < float(active_global_threshold):
        failures.append(
            f"Overall coverage {overall:.2f}% is below threshold {float(active_global_threshold):.2f}%"
        )

    for rel_path, threshold in file_thresholds.items():
        pct = _find_percent_for_file(report, rel_path)
        if pct is None:
            failures.append(f"Coverage entry not found for '{rel_path}'")
            continue
        print(f"{rel_path}: {pct:.2f}% (threshold {threshold:.2f}%)")
        if pct < float(threshold):
            failures.append(
                f"{rel_path} coverage {pct:.2f}% is below threshold {float(threshold):.2f}%"
            )

    if failures:
        print("\nCoverage gate failed:")
        for line in failures:
            print(f"- {line}")
        return 1

    print("\nCoverage gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
