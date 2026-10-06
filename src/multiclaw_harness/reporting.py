"""Markdown and terminal rendering for harness reports."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .evaluator import DIMENSIONS, PASS_MIN_OUTCOME, PASS_MIN_OVERALL

CASE_COLUMNS = ["tool_selection_accuracy", "efficiency_score", "reliability_score", "outcome_score", "budget_score"]
SHORT = {
    "tool_selection_accuracy": "tools",
    "efficiency_score": "efficiency",
    "reliability_score": "reliability",
    "outcome_score": "outcome",
    "budget_score": "budget",
}


def _num(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _delta(value: float) -> str:
    return "0" if value == 0 else f"{value:+.3f}"


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|")


def case_problems(row: Mapping[str, Any]) -> list[str]:
    """Explain why a case scored below perfect, most severe first."""
    if row.get("run_missing"):
        return ["no run trace for this case"]
    problems = []
    if row["forbidden_hits"]:
        problems.append(f"forbidden tools called: {', '.join(row['forbidden_hits'])}")
    if row["present_must_not_include"]:
        problems.append(f"outcome contains prohibited text: {', '.join(row['present_must_not_include'])}")
    if row["budget_violations"]:
        problems.append(f"over budget: {'; '.join(row.get('budget_details') or row['budget_violations'])}")
    if row.get("missing_tools"):
        problems.append(f"missing tools: {', '.join(row['missing_tools'])}")
    unexpected = [tool for tool in row.get("unexpected_tools", []) if tool not in row["forbidden_hits"]]
    if unexpected:
        problems.append(f"unexpected tools: {', '.join(unexpected)}")
    if row["missing_must_include"]:
        problems.append(f"outcome missing: {', '.join(row['missing_must_include'])}")
    if row.get("trials", 1) > 1 and row.get("trials_passed") != row.get("trials"):
        problems.append(f"only {row['trials_passed']}/{row['trials']} trials passed (worst trial shown)")
    if not row["passed"] and not problems:
        problems.append(f"overall below {PASS_MIN_OVERALL} or outcome below {PASS_MIN_OUTCOME}")
    return problems


def _gate_lines(report: Mapping[str, Any]) -> list[str]:
    gate = report.get("gate")
    if not gate:
        return []
    if gate["passed"]:
        return [f"**Gate: ✅ PASS** ({gate['evaluated']} meets all thresholds)", ""]
    lines = [f"**Gate: ❌ FAIL** ({gate['evaluated']})", ""]
    lines.extend(f"- {reason}" for reason in gate["failures"])
    lines.append("")
    return lines


def _aggregate_table(report: Mapping[str, Any]) -> list[str]:
    base = report["aggregate"]
    cand = report.get("candidate", {}).get("aggregate")
    deltas = (report.get("comparison") or {}).get("aggregate_deltas", {})
    keys = ["cases", "passed", *DIMENSIONS, "forbidden_hits"]
    if base.get("trials", base["cases"]) != base["cases"] or (cand and cand.get("trials") != cand.get("cases")):
        keys += ["trials", "trial_pass_rate"]
    if cand:
        lines = ["| metric | baseline | candidate | delta |", "|---|---:|---:|---:|"]
        for key in keys:
            delta = _delta(deltas[key]) if key in deltas else ""
            lines.append(f"| {key} | {_num(base.get(key, ''))} | {_num(cand.get(key, ''))} | {delta} |")
    else:
        lines = ["| metric | value |", "|---|---:|"]
        lines.extend(f"| {key} | {_num(base.get(key, ''))} |" for key in keys)
    return [*lines, ""]


def _case_section(title: str, run_report: Mapping[str, Any]) -> list[str]:
    lines = [f"## {title}", "", f"Run: `{run_report['run']}`", ""]
    header = ["case", "family", "result", "overall", *(SHORT[c] for c in CASE_COLUMNS)]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|---|---|---|" + "---:|" * (len(header) - 3))
    for row in run_report["cases"]:
        result = "✅ pass" if row["passed"] else ("⚠️ missing" if row.get("run_missing") else "❌ fail")
        tools = f"{_num(row['tool_selection_accuracy'])} ({row['matched_tools']}/{row['expected_tools']})"
        cells = [
            f"`{_cell(row['case_id'])}`",
            _cell(row["task_family"]),
            result,
            _num(row["overall_score"]),
            tools,
            *(_num(row[c]) for c in CASE_COLUMNS[1:]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    flagged = [row for row in run_report["cases"] if case_problems(row)]
    if flagged:
        lines.extend(["<details><summary>Findings</summary>", ""])
        for row in flagged:
            lines.append(f"**`{row['case_id']}`**")
            lines.append("")
            lines.extend(f"- {_cell(problem)}" for problem in case_problems(row))
            lines.append("")
        lines.extend(["</details>", ""])
    if run_report.get("extra_runs"):
        lines.extend([f"Run rows with no golden case (ignored): {', '.join(run_report['extra_runs'])}", ""])
    return lines


def render_markdown(report: Mapping[str, Any], comparison: Mapping[str, Any] | None = None) -> str:
    comparison = comparison or report.get("comparison")
    lines = ["# MultiClaw Harness Scorecard", ""]
    lines.extend(_gate_lines(report))
    lines.append(f"Golden set: `{report['golden_set']}`")
    lines.append("")
    lines.extend(["## Aggregate", ""])
    lines.extend(_aggregate_table(report))

    candidate = report.get("candidate")
    lines.extend(_case_section("Baseline cases" if candidate else "Cases", report))
    if candidate:
        lines.extend(_case_section("Candidate cases", candidate))

    if comparison:
        lines.extend(["## Regressions vs baseline", ""])
        if comparison["regressions"]:
            lines.extend(["| case | baseline | candidate | why |", "|---|---:|---:|---|"])
            for row in comparison["regressions"]:
                lines.append(
                    f"| `{_cell(row['case_id'])}` | {_num(row.get('baseline_overall', ''))} | "
                    f"{_num(row.get('candidate_overall', ''))} | {_cell('; '.join(row['reasons']))} |"
                )
        else:
            lines.append("None.")
        lines.append("")
        if comparison.get("improvements"):
            lines.extend(["## Improvements vs baseline", ""])
            lines.extend(
                f"- `{row['case_id']}`: {_num(row['baseline_overall'])} -> {_num(row['candidate_overall'])}"
                for row in comparison["improvements"]
            )
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_markdown(report: Mapping[str, Any], out: Path, comparison: Mapping[str, Any] | None = None) -> None:
    out.write_text(render_markdown(report, comparison), encoding="utf-8")


def _run_summary(name: str, run_report: Mapping[str, Any]) -> list[str]:
    agg = run_report["aggregate"]
    lines = [
        f"{name:<10}{run_report['run']}",
        (
            f"  {agg['passed']}/{agg['cases']} passed  pass_rate {_num(agg['pass_rate'])}  "
            f"overall {_num(agg['overall_score'])}  forbidden_hits {agg['forbidden_hits']}"
        ),
    ]
    if agg.get("trials", agg["cases"]) != agg["cases"]:
        lines.append(f"  {agg['trials']} trials  trial_pass_rate {_num(agg['trial_pass_rate'])}")
    width = max((len(row["case_id"]) for row in run_report["cases"]), default=0)
    for row in run_report["cases"]:
        if not row["passed"]:
            problems = case_problems(row)
            lines.append(f"  FAIL {row['case_id']:<{width}}  {_num(row['overall_score'])}  {problems[0]}")
            lines.extend(f"       {'':<{width}}         {problem}" for problem in problems[1:])
    if run_report.get("extra_runs"):
        lines.append(f"  warning: run rows with no golden case: {', '.join(run_report['extra_runs'])}")
    return lines


def render_summary(report: Mapping[str, Any]) -> str:
    """Plain-text summary for terminals and CI logs."""
    lines = [f"MultiClaw Harness {report.get('harness_version', '')}".rstrip()]
    lines.append(f"golden    {report['golden_set']} ({report['aggregate']['cases']} cases)")
    lines.append("")
    candidate = report.get("candidate")
    lines.extend(_run_summary("baseline" if candidate else "run", report))
    if candidate:
        lines.append("")
        lines.extend(_run_summary("candidate", candidate))
        regressions = report["comparison"]["regressions"]
        lines.append("")
        lines.append(f"regressions vs baseline: {len(regressions)}")
        width = max((len(row["case_id"]) for row in regressions), default=0)
        for row in regressions:
            lines.append(f"  {row['case_id']:<{width}}  {'; '.join(row['reasons'])}")
        improvements = report["comparison"].get("improvements") or []
        if improvements:
            lines.append(f"improvements vs baseline: {', '.join(row['case_id'] for row in improvements)}")
    gate = report.get("gate")
    if gate:
        lines.append("")
        lines.append("GATE PASS" if gate["passed"] else "GATE FAIL")
        lines.extend(f"  - {reason}" for reason in gate["failures"])
    return "\n".join(lines)
