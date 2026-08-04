"""Markdown reporting helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_markdown(report: dict[str, Any], out: Path, comparison: dict[str, Any] | None = None) -> None:
    lines = [
        "# MultiClaw Harness Scorecard",
        "",
        f"Golden set: `{report['golden_set']}`",
        f"Run: `{report['run']}`",
        "",
        "## Aggregate",
        "",
    ]
    for key, val in report["aggregate"].items():
        lines.append(f"- {key}: {val}")
    if report["missing_runs"]:
        lines.append(f"- missing_runs: {', '.join(report['missing_runs'])}")
    if report["extra_runs"]:
        lines.append(f"- extra_runs: {', '.join(report['extra_runs'])}")

    lines.extend(["", "## Case Scores", ""])
    for row in report["cases"]:
        lines.append(f"### {row['case_id']}")
        lines.append(f"- task_family: {row['task_family']}")
        lines.append(f"- passed: {row['passed']}")
        lines.append(f"- overall_score: {row['overall_score']}")
        lines.append(f"- tool_selection_accuracy: {row['tool_selection_accuracy']} ({row['matched_tools']}/{row['expected_tools']})")
        lines.append(f"- efficiency_score: {row['efficiency_score']} ({row['observed_tools']} observed tools)")
        lines.append(f"- reliability_score: {row['reliability_score']}")
        lines.append(f"- outcome_score: {row['outcome_score']}")
        lines.append(f"- budget_score: {row['budget_score']}")
        if row["forbidden_hits"]:
            lines.append(f"- forbidden_hits: {', '.join(row['forbidden_hits'])}")
        if row["budget_violations"]:
            lines.append(f"- budget_violations: {', '.join(row['budget_violations'])}")
        if row["missing_must_include"]:
            lines.append(f"- missing_must_include: {', '.join(row['missing_must_include'])}")
        if row["present_must_not_include"]:
            lines.append(f"- present_must_not_include: {', '.join(row['present_must_not_include'])}")
        lines.append("")

    if comparison:
        lines.extend(["## Regression Comparison", ""])
        for key, val in comparison["aggregate_deltas"].items():
            lines.append(f"- delta_{key}: {val}")
        lines.append("")
        lines.append("### Regressions")
        if comparison["regressions"]:
            for row in comparison["regressions"]:
                lines.append(
                    f"- {row['case_id']}: {row['baseline_overall']} -> {row['candidate_overall']}; "
                    f"forbidden={row['forbidden_hits']}; budgets={row['budget_violations']}"
                )
        else:
            lines.append("- none")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
