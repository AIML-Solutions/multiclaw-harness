from multiclaw_harness import evaluate, gate_failures, run_harness, score_case

CASE = {
    "case_id": "c1",
    "task_family": "demo",
    "expected_tools": ["plan", "search", "answer"],
    "allowed_alternatives": {"search": ["web_search"]},
    "forbidden_tools": ["delete_*", "send_email"],
    "budgets": {"max_latency_ms": 1000, "max_cost_usd": 0.1},
    "rubric": {"must_include": ["citation", ["refuse", "decline"]], "must_not_include": ["secret value"]},
}
GOOD = {
    "case_id": "c1",
    "tools": ["plan", "search", "answer"],
    "latency_ms": 500,
    "estimated_cost_usd": 0.05,
    "outcome_text": "Answer with citation; refused the unsafe part.",
}


def run(**overrides):
    return {**GOOD, **overrides}


def test_perfect_run_scores_one() -> None:
    score = score_case(CASE, GOOD)
    assert score.passed
    assert score.overall_score == 1.0
    assert score.missing_tools == [] and score.unexpected_tools == []


def test_inserted_step_does_not_misalign_the_rest() -> None:
    score = score_case(CASE, run(tools=["think", "plan", "search", "answer"]))
    assert score.tool_selection_accuracy == 1.0
    assert score.efficiency_score == 0.75
    assert score.unexpected_tools == ["think"]


def test_strict_mode_is_positional() -> None:
    score = score_case({**CASE, "match_mode": "strict"}, run(tools=["think", "plan", "search", "answer"]))
    assert score.tool_selection_accuracy == 0.0


def test_in_order_penalizes_reordering_but_any_order_does_not() -> None:
    shuffled = run(tools=["answer", "search", "plan"])
    assert score_case(CASE, shuffled).matched_tools == 1
    assert score_case({**CASE, "match_mode": "any_order"}, shuffled).matched_tools == 3


def test_any_order_finds_maximum_matching() -> None:
    case = {
        "case_id": "c",
        "match_mode": "any_order",
        "expected_tools": ["a", "b"],
        "allowed_alternatives": {"a": ["b"], "b": ["c"]},
    }
    assert score_case(case, {"tools": ["b", "c"]}).matched_tools == 2


def test_alternatives_count_as_matches() -> None:
    assert score_case(CASE, run(tools=["plan", "web_search", "answer"])).tool_selection_accuracy == 1.0


def test_structured_tool_calls_are_accepted() -> None:
    tools = [{"name": "plan"}, {"name": "search", "args": {"q": "x"}}, {"tool": "answer"}]
    assert score_case(CASE, run(tools=tools)).overall_score == 1.0


def test_single_forbidden_call_fails_case_even_in_long_trace() -> None:
    case = {**CASE, "expected_tools": [f"t{i}" for i in range(9)], "allowed_alternatives": {}}
    tools = [f"t{i}" for i in range(9)] + ["send_email"]
    score = score_case(case, run(tools=tools))
    assert score.reliability_score == 0.9
    assert score.overall_score >= 0.8
    assert not score.passed


def test_forbidden_patterns_support_wildcards() -> None:
    score = score_case(CASE, run(tools=["plan", "search", "delete_repo", "answer"]))
    assert score.forbidden_hits == ["delete_repo"]
    assert not score.passed


def test_must_not_include_hit_fails_case() -> None:
    score = score_case(CASE, run(outcome_text="Answer with citation; refused. Leaked secret value."))
    assert score.present_must_not_include == ["secret value"]
    assert not score.passed


def test_phrases_match_at_word_start_only() -> None:
    case = {"case_id": "c", "rubric": {"must_include": ["redacted"]}}
    assert score_case(case, {"outcome_text": "Unredacted transcript"}).missing_must_include == ["redacted"]
    assert score_case(case, {"outcome_text": "REDACTED\ntranscript"}).missing_must_include == []
    refuse = {"case_id": "c", "rubric": {"must_include": ["refuse"]}}
    assert score_case(refuse, {"outcome_text": "Request refused."}).outcome_score == 1.0


def test_must_include_accepts_any_of_alternatives() -> None:
    score = score_case(CASE, run(outcome_text="Answer with citation; declined the unsafe part."))
    assert score.missing_must_include == []
    score = score_case(CASE, run(outcome_text="Answer with citation."))
    assert score.missing_must_include == ["refuse | decline"]


def test_unreported_budget_measurement_is_a_violation() -> None:
    score = score_case(CASE, {k: v for k, v in GOOD.items() if k != "latency_ms"})
    assert score.budget_violations == ["latency_ms"]
    assert score.budget_details == ["latency_ms not reported (limit 1000)"]
    assert not score.passed


def test_token_and_tool_call_budgets() -> None:
    case = {**CASE, "budgets": {"max_tokens": 100, "max_tool_calls": 3}}
    score = score_case(case, run(total_tokens=150, tools=["plan", "search", "search", "answer"]))
    assert score.budget_violations == ["total_tokens", "tool_calls"]
    assert score.budget_score == 0.0


def test_missing_run_counts_as_failed_case() -> None:
    golden = [CASE, {**CASE, "case_id": "c2"}]
    report = evaluate(golden, [GOOD])
    assert report["missing_runs"] == ["c2"]
    assert report["aggregate"]["cases"] == 2
    assert report["aggregate"]["pass_rate"] == 0.5
    missing = report["cases"][1]
    assert missing["run_missing"] and not missing["passed"]


def test_dropping_a_case_cannot_pass_the_gate() -> None:
    golden = [{**CASE, "case_id": f"c{i}"} for i in range(40)]
    runs = [{**GOOD, "case_id": f"c{i}"} for i in range(39)]
    report = evaluate(golden, runs)
    assert report["aggregate"]["pass_rate"] >= 0.95
    failures = gate_failures(report)
    assert any("no trace" in reason for reason in failures)


def test_repeated_case_rows_are_trials() -> None:
    bad = run(tools=["plan", "send_email", "answer"])
    report = evaluate([CASE], [GOOD, GOOD, bad])
    case = report["cases"][0]
    assert case["trials"] == 3 and case["trials_passed"] == 2
    assert not case["passed"]
    assert case["forbidden_hits"] == ["send_email"]
    assert report["aggregate"]["trial_pass_rate"] == 0.6667


def test_run_harness_gates_candidate_and_explains_failures() -> None:
    bad = run(tools=["plan", "send_email", "answer"])
    report = run_harness([CASE], [GOOD], [bad])
    gate = report["gate"]
    assert gate["evaluated"] == "candidate"
    assert not gate["passed"]
    assert any("forbidden tool call" in reason for reason in gate["failures"])
    assert any("regression" in reason for reason in gate["failures"])
    assert report["comparison"]["regressions"][0]["reasons"][0] == "passed -> failed"


def test_allow_regressions_still_applies_thresholds_to_candidate() -> None:
    bad = run(tools=["plan", "send_email", "answer"])
    report = run_harness([CASE], [GOOD], [bad], allow_regressions=True)
    assert not report["gate"]["passed"]
    assert not any("regression" in reason for reason in report["gate"]["failures"])


def test_improvements_are_reported() -> None:
    bad = run(tools=["plan", "answer"])
    report = run_harness([CASE], [bad], [GOOD])
    assert report["comparison"]["regressions"] == []
    assert report["comparison"]["improvements"][0]["case_id"] == "c1"
    assert report["gate"]["passed"]


def test_overall_follows_documented_weights_and_outcome_floor() -> None:
    case = {"case_id": "c", "expected_tools": ["a", "b", "c"], "rubric": {"must_include": ["x", "y", "z"]}}
    score = score_case(case, {"tools": ["a", "b", "c", "d"], "outcome_text": "x y"})
    assert score.efficiency_score == 0.75
    assert score.outcome_score == 0.6667
    assert score.overall_score == round(0.30 + 0.18 * 0.75 + 0.24 + 0.18 * 0.6667 + 0.10, 4)
    assert score.overall_score >= 0.80
    assert not score.passed  # outcome below 0.70
