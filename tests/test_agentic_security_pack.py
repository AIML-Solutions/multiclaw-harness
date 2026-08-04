from pathlib import Path

from multiclaw_harness.evaluator import compare, evaluate

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "packs/agentic-security"


def test_agentic_security_baseline_passes() -> None:
    report = evaluate(PACK / "golden_cases.jsonl", PACK / "baseline_run.jsonl")
    assert report["aggregate"]["cases"] == 6
    assert report["aggregate"]["pass_rate"] == 1.0
    assert report["aggregate"]["overall_score"] == 1.0


def test_agentic_security_candidate_fails_all_cases() -> None:
    report = evaluate(PACK / "golden_cases.jsonl", PACK / "candidate_run.jsonl")
    assert report["aggregate"]["cases"] == 6
    assert report["aggregate"]["pass_rate"] == 0.0
    forbidden = {hit for row in report["cases"] for hit in row["forbidden_hits"]}
    assert "disable_policy_gate" in forbidden
    assert "read_env_vars" in forbidden
    assert "run_privileged_container" in forbidden
    assert "follow_retrieved_instruction" in forbidden
    assert "bypass_approval_gate" in forbidden
    assert "curl_pipe_shell" in forbidden


def test_agentic_security_regressions_are_reported() -> None:
    baseline = evaluate(PACK / "golden_cases.jsonl", PACK / "baseline_run.jsonl")
    candidate = evaluate(PACK / "golden_cases.jsonl", PACK / "candidate_run.jsonl")
    comparison = compare(baseline, candidate)
    assert len(comparison["regressions"]) == 6
    assert comparison["aggregate_deltas"]["pass_rate"] == -1.0
    assert comparison["aggregate_deltas"]["reliability_score"] < 0
