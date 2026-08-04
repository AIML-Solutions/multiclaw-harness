"""Trajectory evaluation for agentic workflow runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    task_family: str
    tool_selection_accuracy: float
    efficiency_score: float
    reliability_score: float
    outcome_score: float
    budget_score: float
    overall_score: float
    passed: bool
    expected_tools: int
    observed_tools: int
    matched_tools: int
    forbidden_hits: list[str]
    missing_must_include: list[str]
    present_must_not_include: list[str]
    budget_violations: list[str]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{n}: {exc}") from exc
    return rows


def equivalent(observed: str, expected: str, alternatives: dict[str, list[str]]) -> bool:
    return observed == expected or observed in alternatives.get(expected, [])


def score_case(case: dict[str, Any], run: dict[str, Any]) -> CaseScore:
    expected = list(case.get("expected_tools", []))
    observed = list(run.get("tools", []))
    alternatives = dict(case.get("allowed_alternatives", {}))
    forbidden = set(case.get("forbidden_tools", []))
    outcome_text = str(run.get("outcome_text", "")).lower()
    rubric = case.get("rubric", {}) or {}
    budgets = case.get("budgets", {}) or {}

    matched = 0
    for i, expected_tool in enumerate(expected):
        if i < len(observed) and equivalent(str(observed[i]), str(expected_tool), alternatives):
            matched += 1

    tool_selection_accuracy = matched / len(expected) if expected else 1.0
    extra_steps = max(0, len(observed) - len(expected))
    missing_steps = max(0, len(expected) - len(observed))
    inefficiency = extra_steps + missing_steps
    efficiency_score = max(0.0, 1.0 - (inefficiency / max(len(expected), 1)))

    forbidden_hits = [tool for tool in observed if tool in forbidden]
    reliability_score = 1.0 if not forbidden_hits else max(0.0, 1.0 - (len(forbidden_hits) / max(len(observed), 1)))

    must_include = [str(x).lower() for x in rubric.get("must_include", [])]
    must_not_include = [str(x).lower() for x in rubric.get("must_not_include", [])]
    missing_must_include = [x for x in must_include if x not in outcome_text]
    present_must_not_include = [x for x in must_not_include if x in outcome_text]
    include_score = 1.0 - (len(missing_must_include) / max(len(must_include), 1)) if must_include else 1.0
    must_not_penalty = len(present_must_not_include) / max(len(must_not_include), 1) if must_not_include else 0.0
    outcome_score = max(0.0, include_score - must_not_penalty)

    budget_violations = []
    max_latency_ms = budgets.get("max_latency_ms")
    max_cost_usd = budgets.get("max_cost_usd")
    if max_latency_ms is not None and float(run.get("latency_ms", 0)) > float(max_latency_ms):
        budget_violations.append("latency_ms")
    if max_cost_usd is not None and float(run.get("estimated_cost_usd", 0)) > float(max_cost_usd):
        budget_violations.append("estimated_cost_usd")
    budget_score = 1.0 if not budget_violations else max(0.0, 1.0 - (len(budget_violations) / 2))

    overall = (
        0.30 * tool_selection_accuracy
        + 0.18 * efficiency_score
        + 0.24 * reliability_score
        + 0.18 * outcome_score
        + 0.10 * budget_score
    )
    passed = overall >= 0.80 and reliability_score >= 0.90 and outcome_score >= 0.70 and not budget_violations

    return CaseScore(
        case_id=str(case["case_id"]),
        task_family=str(case.get("task_family", "unknown")),
        tool_selection_accuracy=round(tool_selection_accuracy, 4),
        efficiency_score=round(efficiency_score, 4),
        reliability_score=round(reliability_score, 4),
        outcome_score=round(outcome_score, 4),
        budget_score=round(budget_score, 4),
        overall_score=round(overall, 4),
        passed=passed,
        expected_tools=len(expected),
        observed_tools=len(observed),
        matched_tools=matched,
        forbidden_hits=[str(x) for x in forbidden_hits],
        missing_must_include=missing_must_include,
        present_must_not_include=present_must_not_include,
        budget_violations=budget_violations,
    )


def aggregate(scores: list[CaseScore]) -> dict[str, Any]:
    if not scores:
        return {"cases": 0, "pass_rate": 0.0}
    return {
        "cases": len(scores),
        "pass_rate": round(sum(s.passed for s in scores) / len(scores), 4),
        "overall_score": round(mean(s.overall_score for s in scores), 4),
        "tool_selection_accuracy": round(mean(s.tool_selection_accuracy for s in scores), 4),
        "efficiency_score": round(mean(s.efficiency_score for s in scores), 4),
        "reliability_score": round(mean(s.reliability_score for s in scores), 4),
        "outcome_score": round(mean(s.outcome_score for s in scores), 4),
        "budget_score": round(mean(s.budget_score for s in scores), 4),
    }


def evaluate(golden_path: Path, run_path: Path) -> dict[str, Any]:
    cases = {row["case_id"]: row for row in load_jsonl(golden_path)}
    runs = {row["case_id"]: row for row in load_jsonl(run_path)}
    missing_runs = sorted(set(cases) - set(runs))
    extra_runs = sorted(set(runs) - set(cases))
    scores = [score_case(cases[case_id], runs[case_id]) for case_id in sorted(cases) if case_id in runs]
    return {
        "golden_set": str(golden_path),
        "run": str(run_path),
        "aggregate": aggregate(scores),
        "missing_runs": missing_runs,
        "extra_runs": extra_runs,
        "cases": [asdict(score) for score in scores],
    }


def compare(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    b = base["aggregate"]
    c = candidate["aggregate"]
    keys = [
        "pass_rate",
        "overall_score",
        "tool_selection_accuracy",
        "efficiency_score",
        "reliability_score",
        "outcome_score",
        "budget_score",
    ]
    deltas = {key: round(float(c.get(key, 0.0)) - float(b.get(key, 0.0)), 4) for key in keys}
    base_cases = {row["case_id"]: row for row in base["cases"]}
    cand_cases = {row["case_id"]: row for row in candidate["cases"]}
    regressions = []
    for case_id, cand in cand_cases.items():
        prev = base_cases.get(case_id)
        if not prev:
            continue
        drifted = cand["overall_score"] < prev["overall_score"] or (prev["passed"] and not cand["passed"])
        has_policy_failure = cand["forbidden_hits"] or cand["budget_violations"]
        if drifted or has_policy_failure:
            regressions.append(
                {
                    "case_id": case_id,
                    "baseline_overall": prev["overall_score"],
                    "candidate_overall": cand["overall_score"],
                    "baseline_passed": prev["passed"],
                    "candidate_passed": cand["passed"],
                    "forbidden_hits": cand["forbidden_hits"],
                    "budget_violations": cand["budget_violations"],
                    "missing_must_include": cand["missing_must_include"],
                }
            )
    return {"aggregate_deltas": deltas, "regressions": regressions}


def gate_passed(report: dict[str, Any], min_pass_rate: float, min_overall: float, allow_regressions: bool) -> bool:
    agg = report["aggregate"]
    if float(agg.get("pass_rate", 0.0)) < min_pass_rate:
        return False
    if float(agg.get("overall_score", 0.0)) < min_overall:
        return False
    comparison = report.get("comparison")
    return not (comparison and comparison.get("regressions") and not allow_regressions)
