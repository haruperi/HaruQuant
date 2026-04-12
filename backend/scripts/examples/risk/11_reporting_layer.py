"""
Example 19: Reporting Layer

Type: live-broker dependent manual demo

Phase 11 task-by-task walkthrough using the actual HaruQuant stack:
1. load stored snapshot artifacts
2. build machine-readable risk report
3. build markdown risk report
4. export JSON and Markdown report artifacts
5. build scenario report
6. build replay report

Run:
    python backend/scripts/examples/risk/11_reporting_layer.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from apps.risk.reports import (
    build_replay_report,
    build_risk_snapshot_report,
    build_scenario_report,
    render_risk_report_markdown,
)


def print_example_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_phase10_module():
    path = os.path.join(os.path.dirname(__file__), "10_storage_and_snapshot_store.py")
    spec = importlib.util.spec_from_file_location("phase10_storage_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExampleContext:
    def __init__(self):
        phase10 = load_phase10_module()
        self.base = phase10.ExampleContext()
        self.run_id = None
        self.snapshot_id = None
        self.snapshot_bundle = None
        self.replay_frames = None
        self.risk_report = None
        self.scenario_report = None
        self.replay_report = None
        self.exports = None

    def setup(self) -> None:
        self.base.setup()
        self.run_id = self.base.store.create_run(
            label="phase11-reporting-example",
            description="Stored risk artifacts for reporting walkthrough",
            source="example",
            context={"phase": 11},
        )
        self.snapshot_id = self.base.store.store_snapshot_bundle(
            run_id=self.run_id,
            snapshot=self.base.snapshot,
            scorecard=self.base.scorecard,
            recommendations=self.base.recommendations,
        )
        self.base.store.store_replay_frame(
            run_id=self.run_id,
            frame=self.base.frame,
            snapshot_id=self.snapshot_id,
        )
        self.snapshot_bundle = self.base.store.load_snapshot_bundle(self.snapshot_id)
        self.replay_frames = self.base.store.load_replay_frames(self.run_id)

    def close(self) -> None:
        self.base.close()


def example_01_load_stored_snapshot_artifacts(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Load Stored Snapshot Artifacts")
    print(f"  snapshot_id={ctx.snapshot_id}")
    print(f"  metric_rows={len(ctx.snapshot_bundle['metric_rows'])}")
    print(f"  score_rows={len(ctx.snapshot_bundle['score_rows'])}")
    print(f"  replay_frames={len(ctx.replay_frames)}")


def example_02_build_machine_readable_risk_report(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Build Machine-Readable Risk Report")
    run = ctx.base.store.load_run(ctx.run_id)
    ctx.risk_report = build_risk_snapshot_report(ctx.snapshot_bundle, run=run)
    print(f"  governance={ctx.risk_report['governance_summary']}")
    print(f"  regime={ctx.risk_report['regime_summary']}")


def example_03_build_markdown_risk_report(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Build Markdown Risk Report")
    markdown = render_risk_report_markdown(ctx.risk_report)
    preview = markdown.splitlines()[:10]
    for line in preview:
        print(f"  {line}")


def example_04_export_report_artifacts(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Export Report Artifacts")
    ctx.exports = ctx.base.store.export_snapshot_reports(ctx.snapshot_id)
    for artifact in ctx.exports["artifacts"]:
        print(f"  {artifact['artifact_type']}: {artifact['artifact_ref']}")


def example_05_build_scenario_report(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Build Scenario Report")
    run = ctx.base.store.load_run(ctx.run_id)
    ctx.scenario_report = build_scenario_report(ctx.snapshot_bundle, run=run)
    print(
        f"  worst={ctx.scenario_report['worst_scenario_name']} "
        f"loss={ctx.scenario_report['worst_scenario_loss']}"
    )


def example_06_build_replay_report(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Build Replay Report")
    run = ctx.base.store.load_run(ctx.run_id)
    ctx.replay_report = build_replay_report(ctx.replay_frames, run=run)
    print(f"  frame_count={ctx.replay_report['frame_count']}")
    print(f"  summary={ctx.replay_report['summary']}")


def main() -> None:
    print_example_header("PHASE 11 REPORTING LAYER")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_load_stored_snapshot_artifacts(ctx)
        example_02_build_machine_readable_risk_report(ctx)
        example_03_build_markdown_risk_report(ctx)
        example_04_export_report_artifacts(ctx)
        example_05_build_scenario_report(ctx)
        example_06_build_replay_report(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
