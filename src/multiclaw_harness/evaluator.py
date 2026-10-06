"""Trajectory evaluation for agentic workflow runs."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from fnmatch import fnmatchcase
from statistics import mean
from typing import Any

from ._version import __version__
from .schema import (
    BUDGET_FIELDS,
    HarnessInputError,
    Source,
    load_jsonl,
    read_rows,
    tool_name,
    validate_golden,
    validate_runs,
)

__all__ = [
    "WEIGHTS",
    "CaseScore",
    "HarnessInputError",
    "aggregate",
    "compare",
    "evaluate",
    "gate_failures",
    "gate_passed",
    "load_jsonl",
    "run_harness",
    "score_case",
]

# Weighted contribution of each dimension to a case's overall score.
WEIGHTS = {
    "tool_selection_accuracy": 0.30,
    "efficiency_score": 0.18,
    "reliability_score": 0.24,
    "outcome_score": 0.18,
    "budget_score": 0.10,
}
# A case passes only with no forbidden calls, no must_not_include hits, no budget violations, and these minimums.
PASS_MIN_OVERALL = 0.80
PASS_MIN_OUTCOME = 0.70

DIMENSIONS = ["pass_rate", "overall_score", *WEIGHTS]


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
    match_mode: str = "in_order"
    missing_tools: list[str] = field(default_factory=list)
    unexpected_tools: list[str] = field(default_factory=list)
    budget_details: list[str] = field(default_factory=list)
    run_missing: bool = False
    trials: int = 1
    trials_passed: int = 1


def equivalent(observed: str, expected: str, alternatives: Mapping[str, list[str]]) -> bool:
    return observed == expected or observed in alternatives.get(expected, [])


def match_tools(
    expected: list[str], observed: list[str], alternatives: Mapping[str, list[str]], mode: str = "in_order"
) -> list[tuple[int, int]]:
    """Return matched ``(expected_index, observed_index)`` pairs.

    - ``in_order``: longest common subsequence, so inserted or skipped steps don't misalign the rest.
    - ``strict``: position ``i`` must match position ``i``.
    - ``any_order``: maximum one-to-one matching regardless of order.
    """
    eq = [[equivalent(o, e, alternatives) for o in observed] for e in expected]
    if mode == "strict":
        return [(i, i) for i in range(min(len(expected), len(observed))) if eq[i][i]]
    if mode == "any_order":
        owner: dict[int, int] = {}

        def assign(i: int, seen: set[int]) -> bool:
            for j, ok in enumerate(eq[i]):
                if ok and j not in seen:
                    seen.add(j)
                    if j not in owner or assign(owner[j], seen):
                        owner[j] = i
                        return True
            return False

        for i in range(len(expected)):
            assign(i, set())
        return sorted((i, j) for j, i in owner.items())

    n, m = len(expected), len(observed)
    lcs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            lcs[i][j] = lcs[i + 1][j + 1] + 1 if eq[i][j] else max(lcs[i + 1][j], lcs[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if eq[i][j] and lcs[i][j] == lcs[i + 1][j + 1] + 1:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif lcs[i + 1][j] >= lcs[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def contains_phrase(text: str, phrase: str) -> bool:
    """Case-insensitive match anchored at a word start.

    ``refuse`` matches ``refused`` (suffixes allowed) but ``redacted`` does not match ``unredacted``.
    """
    pattern = rf"(?<!\w){re.escape(_normalize(phrase))}"
    return re.search(pattern, _normalize(text)) is not None


def _measure(run: Mapping[str, Any], measured: str, tools: list[str]) -> Any:
    return len(tools) if measured == "tool_calls" else run.get(measured)


def score_case(case: Mapping[str, Any], run: Mapping[str, Any]) -> CaseScore:
    """Score one run trace against one golden case."""
    expected = [str(t) for t in case.get("expected_tools", [])]
    observed = [tool_name(t) or str(t) for t in run.get("tools", [])]
    alternatives = dict(case.get("allowed_alternatives", {}) or {})
    forbidden = [str(t) for t in case.get("forbidden_tools", [])]
    mode = str(case.get("match_mode", "in_order"))
    outcome_text = str(run.get("outcome_text") or "")
    rubric = case.get("rubric", {}) or {}
    budgets = case.get("budgets", {}) or {}

    pairs = match_tools(expected, observed, alternatives, mode)
    matched = len(pairs)
    matched_expected = {i for i, _ in pairs}
    matched_observed = {j for _, j in pairs}
    missing_tools = [tool for i, tool in enumerate(expected) if i not in matched_expected]
    unexpected_tools = [tool for j, tool in enumerate(observed) if j not in matched_observed]

    tool_selection_accuracy = matched / len(expected) if expected else 1.0
    efficiency_score = matched / len(observed) if observed else float(not expected)

    forbidden_hits = [tool for tool in observed if any(fnmatchcase(tool, pattern) for pattern in forbidden)]
    reliability_score = 1.0 - (len(forbidden_hits) / len(observed)) if forbidden_hits else 1.0

    must_include = rubric.get("must_include", [])
    must_not_include = [str(x) for x in rubric.get("must_not_include", [])]
    missing_must_include = []
    for item in must_include:
        options = [item] if isinstance(item, str) else [str(x) for x in item]
        if not any(contains_phrase(outcome_text, option) for option in options):
            missing_must_include.append(" | ".join(options).lower())
    present_must_not_include = [x.lower() for x in must_not_include if contains_phrase(outcome_text, x)]
    include_score = 1.0 - (len(missing_must_include) / len(must_include)) if must_include else 1.0
    must_not_penalty = len(present_must_not_include) / len(must_not_include) if must_not_include else 0.0
    outcome_score = max(0.0, include_score - must_not_penalty)

    budget_violations: list[str] = []
    budget_details: list[str] = []
    for key, limit in budgets.items():
        measured = BUDGET_FIELDS.get(key)
        if measured is None:
            raise HarnessInputError(f"case '{case.get('case_id')}': unknown budget '{key}'")
        value = _measure(run, measured, observed)
        if value is None:
            budget_violations.append(measured)
            budget_details.append(f"{measured} not reported (limit {limit})")
        elif float(value) > float(limit):
            budget_violations.append(measured)
            budget_details.append(f"{measured} {value} > {limit}")
    budget_score = 1.0 - (len(budget_violations) / len(budgets)) if budgets else 1.0

    scores = {
        "tool_selection_accuracy": tool_selection_accuracy,
        "efficiency_score": efficiency_score,
        "reliability_score": reliability_score,
        "outcome_score": outcome_score,
        "budget_score": budget_score,
    }
    scores = {key: round(value, 4) for key, value in scores.items()}
    # Round before comparing so the pass decision matches the scores shown in reports.
    overall = round(sum(WEIGHTS[key] * value for key, value in scores.items()), 4)
    passed = (
        overall >= PASS_MIN_OVERALL
        and scores["outcome_score"] >= PASS_MIN_OUTCOME
        and not forbidden_hits
        and not present_must_not_include
        and not budget_violations
    )

    return CaseScore(
        case_id=str(case["case_id"]),
        task_family=str(case.get("task_family", "unknown")),
        **scores,
        overall_score=overall,
        passed=passed,
        expected_tools=len(expected),
        observed_tools=len(observed),
        matched_tools=matched,
        forbidden_hits=forbidden_hits,
        missing_must_include=missing_must_include,
        present_must_not_include=present_must_not_include,
        budget_violations=budget_violations,
        match_mode=mode,
        missing_tools=missing_tools,
        unexpected_tools=unexpected_tools,
        budget_details=budget_details,
        trials_passed=int(passed),
    )


def _missing_run_score(case: Mapping[str, Any]) -> CaseScore:
    expected = [str(t) for t in case.get("expected_tools", [])]
    return CaseScore(
        case_id=str(case["case_id"]),
        task_family=str(case.get("task_family", "unknown")),
        tool_selection_accuracy=0.0,
        efficiency_score=0.0,
        reliability_score=0.0,
        outcome_score=0.0,
        budget_score=0.0,
        overall_score=0.0,
        passed=False,
        expected_tools=len(expected),
        observed_tools=0,
        matched_tools=0,
        forbidden_hits=[],
        missing_must_include=[],
        present_must_not_include=[],
        budget_violations=[],
        match_mode=str(case.get("match_mode", "in_order")),
        missing_tools=expected,
        unexpected_tools=[],
        budget_details=[],
        run_missing=True,
        trials=0,
        trials_passed=0,
    )


def score_trials(case: Mapping[str, Any], trials: list[Mapping[str, Any]]) -> CaseScore:
    """Score repeated trials of one case. The case reports its worst trial and passes only if every trial passes."""
    if not trials:
        return _missing_run_score(case)
    scores = [score_case(case, trial) for trial in trials]
    worst = min(scores, key=lambda s: (s.passed, s.overall_score))
    return replace(worst, trials=len(scores), trials_passed=sum(s.passed for s in scores))


def aggregate(scores: list[CaseScore]) -> dict[str, Any]:
    if not scores:
        empty = {key: 0.0 for key in DIMENSIONS}
        return {"cases": 0, "passed": 0, **empty, "forbidden_hits": 0, "trials": 0, "trial_pass_rate": 0.0}
    trials = sum(s.trials for s in scores)
    return {
        "cases": len(scores),
        "passed": sum(s.passed for s in scores),
        "pass_rate": round(sum(s.passed for s in scores) / len(scores), 4),
        "overall_score": round(mean(s.overall_score for s in scores), 4),
        **{key: round(mean(getattr(s, key) for s in scores), 4) for key in WEIGHTS},
        "forbidden_hits": sum(len(s.forbidden_hits) for s in scores),
        "trials": trials,
        "trial_pass_rate": round(sum(s.trials_passed for s in scores) / trials, 4) if trials else 0.0,
    }


def _evaluate(golden_label: str, cases: dict[str, dict[str, Any]], run_source: Source) -> dict[str, Any]:
    run_label, run_rows = read_rows(run_source)
    runs = validate_runs(run_label, run_rows)
    scores = [score_trials(cases[case_id], runs.get(case_id, [])) for case_id in sorted(cases)]
    return {
        "harness_version": __version__,
        "golden_set": golden_label,
        "run": run_label,
        "aggregate": aggregate(scores),
        "missing_runs": sorted(set(cases) - set(runs)),
        "extra_runs": sorted(set(runs) - set(cases)),
        "cases": [asdict(score) for score in scores],
    }


def _load_golden(golden: Source) -> tuple[str, dict[str, dict[str, Any]]]:
    label, rows = read_rows(golden)
    return label, validate_golden(label, rows)


def evaluate(golden: Source, run: Source) -> dict[str, Any]:
    """Score a run against a golden set. Each argument is a JSONL path or an iterable of dicts.

    Every golden case appears in ``cases``; a case with no run trace is scored zero and counted as failed.
    """
    return _evaluate(*_load_golden(golden), run)


def compare(base: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Diff a candidate report against a baseline report."""
    b = base["aggregate"]
    c = candidate["aggregate"]
    deltas = {key: round(float(c.get(key, 0.0)) - float(b.get(key, 0.0)), 4) for key in DIMENSIONS}
    cand_cases = {row["case_id"]: row for row in candidate["cases"]}
    regressions = []
    improvements = []
    for prev in base["cases"]:
        case_id = prev["case_id"]
        cand = cand_cases.get(case_id)
        if cand is None:
            regressions.append({"case_id": case_id, "reasons": ["case missing from candidate report"]})
            continue
        reasons = []
        if cand.get("run_missing"):
            reasons.append("run missing")
        if prev["passed"] and not cand["passed"]:
            reasons.append("passed -> failed")
        if cand["overall_score"] < prev["overall_score"]:
            reasons.append(f"overall {prev['overall_score']} -> {cand['overall_score']}")
        if cand["forbidden_hits"]:
            reasons.append(f"forbidden: {', '.join(cand['forbidden_hits'])}")
        if cand.get("present_must_not_include"):
            reasons.append(f"must_not_include: {', '.join(cand['present_must_not_include'])}")
        if cand["budget_violations"]:
            reasons.append(f"budget: {', '.join(cand.get('budget_details') or cand['budget_violations'])}")
        if reasons:
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
                    "present_must_not_include": cand.get("present_must_not_include", []),
                    "missing_tools": cand.get("missing_tools") or [],
                    "unexpected_tools": cand.get("unexpected_tools") or [],
                    "reasons": reasons,
                }
            )
        elif cand["overall_score"] > prev["overall_score"] or (cand["passed"] and not prev["passed"]):
            improvements.append(
                {
                    "case_id": case_id,
                    "baseline_overall": prev["overall_score"],
                    "candidate_overall": cand["overall_score"],
                    "baseline_passed": prev["passed"],
                    "candidate_passed": cand["passed"],
                }
            )
    return {"aggregate_deltas": deltas, "regressions": regressions, "improvements": improvements}


def gate_failures(
    report: Mapping[str, Any],
    min_pass_rate: float = 0.95,
    min_overall: float = 0.90,
    allow_regressions: bool = False,
    max_forbidden_hits: int = 0,
) -> list[str]:
    """Return human-readable reasons the gate fails; an empty list means it passes.

    When the report carries a ``candidate``, thresholds apply to the candidate (the change under test).
    """
    target = report.get("candidate") or report
    label = "candidate" if report.get("candidate") else "run"
    agg = target["aggregate"]
    failures = []
    if not agg.get("cases"):
        failures.append("golden set has no cases")
    missing = target.get("missing_runs") or []
    if missing:
        failures.append(f"{label} has no trace for {len(missing)} golden case(s): {', '.join(missing)}")
    if float(agg.get("pass_rate", 0.0)) < min_pass_rate:
        failures.append(f"{label} pass_rate {agg.get('pass_rate', 0.0)} < {min_pass_rate}")
    if float(agg.get("overall_score", 0.0)) < min_overall:
        failures.append(f"{label} overall_score {agg.get('overall_score', 0.0)} < {min_overall}")
    hits = sum(len(row.get("forbidden_hits", [])) for row in target.get("cases", []))
    if hits > max_forbidden_hits:
        failures.append(f"{label} made {hits} forbidden tool call(s) (max {max_forbidden_hits})")
    comparison = report.get("comparison")
    if comparison and comparison.get("regressions") and not allow_regressions:
        ids = [row["case_id"] for row in comparison["regressions"]]
        failures.append(f"{len(ids)} regression(s) vs baseline: {', '.join(ids)}")
    return failures


def gate_passed(
    report: Mapping[str, Any],
    min_pass_rate: float,
    min_overall: float,
    allow_regressions: bool,
    max_forbidden_hits: int = 0,
) -> bool:
    return not gate_failures(report, min_pass_rate, min_overall, allow_regressions, max_forbidden_hits)


def run_harness(
    golden: Source,
    run: Source,
    compare_run: Source | None = None,
    *,
    min_pass_rate: float = 0.95,
    min_overall: float = 0.90,
    allow_regressions: bool = False,
    max_forbidden_hits: int = 0,
) -> dict[str, Any]:
    """Evaluate a run (and optionally a candidate against it) and attach the gate verdict under ``report["gate"]``."""
    golden_label, cases = _load_golden(golden)
    report = _evaluate(golden_label, cases, run)
    if compare_run is not None:
        candidate = _evaluate(golden_label, cases, compare_run)
        report["comparison_candidate"] = candidate["run"]
        report["comparison"] = compare(report, candidate)
        report["candidate"] = candidate
    failures = gate_failures(report, min_pass_rate, min_overall, allow_regressions, max_forbidden_hits)
    report["gate"] = {
        "passed": not failures,
        "evaluated": "candidate" if compare_run is not None else "run",
        "failures": failures,
        "thresholds": {
            "min_pass_rate": min_pass_rate,
            "min_overall": min_overall,
            "allow_regressions": allow_regressions,
            "max_forbidden_hits": max_forbidden_hits,
        },
    }
    return report
