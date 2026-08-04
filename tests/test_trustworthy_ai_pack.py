from pathlib import Path

from multiclaw_harness.evaluator import compare, evaluate

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "packs/trustworthy-ai"


def test_trustworthy_ai_baseline_passes() -> None:
    report = evaluate(PACK / "golden_cases.jsonl", PACK / "baseline_run.jsonl")
    assert report["aggregate"]["cases"] == 6
    assert report["aggregate"]["pass_rate"] == 1.0
    assert report["aggregate"]["overall_score"] == 1.0


def test_trustworthy_ai_candidate_fails_all_cases() -> None:
    report = evaluate(PACK / "golden_cases.jsonl", PACK / "candidate_run.jsonl")
    assert report["aggregate"]["cases"] == 6
    assert report["aggregate"]["pass_rate"] == 0.0
    forbidden = {hit for row in report["cases"] for hit in row["forbidden_hits"]}
    assert "skip_calibration_check" in forbidden
    assert "invent_explanation" in forbidden
    assert "ignore_drift_signal" in forbidden
    assert "apply_override_without_record" in forbidden
    assert "use_stale_data_without_warning" in forbidden
    assert "ship_without_model_card_update" in forbidden


def test_trustworthy_ai_regressions_are_reported() -> None:
    baseline = evaluate(PACK / "golden_cases.jsonl", PACK / "baseline_run.jsonl")
    candidate = evaluate(PACK / "golden_cases.jsonl", PACK / "candidate_run.jsonl")
    comparison = compare(baseline, candidate)
    assert len(comparison["regressions"]) == 6
    assert comparison["aggregate_deltas"]["pass_rate"] == -1.0
    assert comparison["aggregate_deltas"]["reliability_score"] < 0
    assert comparison["aggregate_deltas"]["budget_score"] < 0
