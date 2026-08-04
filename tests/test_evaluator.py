from pathlib import Path

from multiclaw_harness.evaluator import compare, evaluate, gate_passed

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_passes() -> None:
    report = evaluate(ROOT / "examples/golden_cases.jsonl", ROOT / "examples/baseline_run.jsonl")
    assert report["aggregate"]["cases"] == 4
    assert report["aggregate"]["pass_rate"] == 1.0
    assert report["aggregate"]["overall_score"] == 1.0
    assert gate_passed(report, min_pass_rate=0.95, min_overall=0.90, allow_regressions=False)


def test_candidate_regressions_are_detected() -> None:
    baseline = evaluate(ROOT / "examples/golden_cases.jsonl", ROOT / "examples/baseline_run.jsonl")
    candidate = evaluate(ROOT / "examples/golden_cases.jsonl", ROOT / "examples/candidate_run.jsonl")
    comparison = compare(baseline, candidate)
    assert candidate["aggregate"]["pass_rate"] == 0.0
    assert len(comparison["regressions"]) == 4
    forbidden = {hit for row in comparison["regressions"] for hit in row["forbidden_hits"]}
    assert "execute_unapproved_shell" in forbidden
    assert "commit_env_file" in forbidden


def test_budget_violations_affect_gate() -> None:
    candidate = evaluate(ROOT / "examples/golden_cases.jsonl", ROOT / "examples/candidate_run.jsonl")
    assert not gate_passed(candidate, min_pass_rate=0.95, min_overall=0.90, allow_regressions=False)
    violations = {hit for row in candidate["cases"] for hit in row["budget_violations"]}
    assert "latency_ms" in violations
    assert "estimated_cost_usd" in violations
