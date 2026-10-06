import pytest

from multiclaw_harness import HarnessInputError, evaluate, load_jsonl

CASE = {"case_id": "c1", "expected_tools": ["a", "b"], "forbidden_tools": ["x"]}


def check_error(golden, match, runs=()):
    with pytest.raises(HarnessInputError, match=match):
        evaluate(golden, list(runs))


def test_unknown_field_is_rejected_with_suggestion() -> None:
    check_error([{**CASE, "forbiden_tools": ["y"]}], "did you mean 'forbidden_tools'")


def test_unknown_budget_is_rejected_with_suggestion() -> None:
    check_error([{**CASE, "budgets": {"max_latency": 10}}], "did you mean 'max_latency_ms'")


def test_unknown_rubric_field_is_rejected() -> None:
    check_error([{**CASE, "rubric": {"must_includes": ["x"]}}], "did you mean 'must_include'")


def test_empty_rubric_phrase_is_rejected() -> None:
    check_error([{**CASE, "rubric": {"must_not_include": [" "]}}], "must be non-empty")
    check_error([{**CASE, "rubric": {"must_include": [[]]}}], "must be non-empty strings")


def test_scalar_must_include_is_rejected() -> None:
    check_error([{**CASE, "rubric": {"must_include": "abc"}}], "'rubric.must_include' must be a list")


def test_non_finite_numbers_are_rejected(tmp_path) -> None:
    check_error([CASE], "'latency_ms' must be a finite number", runs=[{"case_id": "c1", "latency_ms": float("nan")}])
    check_error([{**CASE, "budgets": {"max_cost_usd": float("inf")}}], "finite, non-negative")
    path = tmp_path / "run.jsonl"
    path.write_text('{"case_id": "c1", "latency_ms": NaN}\n', encoding="utf-8")
    with pytest.raises(HarnessInputError, match=r"run.jsonl:1: invalid JSON: NaN is not valid JSON"):
        load_jsonl(path)


def test_bad_match_mode_is_rejected() -> None:
    check_error([{**CASE, "match_mode": "fuzzy"}], "match_mode")


def test_alternative_for_unknown_tool_is_rejected() -> None:
    check_error([{**CASE, "allowed_alternatives": {"c": ["d"]}}], "not in expected_tools")


def test_tool_both_expected_and_forbidden_is_rejected() -> None:
    check_error([{**CASE, "forbidden_tools": ["a"]}], "both expected and forbidden: a")
    check_error([{**CASE, "forbidden_tools": ["b*"]}], "both expected and forbidden: b")


def test_duplicate_golden_case_is_rejected() -> None:
    check_error([CASE, CASE], "duplicate case_id 'c1'")


def test_missing_case_id_is_rejected() -> None:
    check_error([{"expected_tools": []}], "'case_id' is required")


def test_run_with_bad_tools_is_rejected() -> None:
    check_error([CASE], "'tools' must be a list", runs=[{"case_id": "c1", "tools": "a,b"}])
    check_error([CASE], "must be a string or an object", runs=[{"case_id": "c1", "tools": [1]}])
    check_error([CASE], "'latency_ms' must be a finite number", runs=[{"case_id": "c1", "latency_ms": "fast"}])


def test_jsonl_errors_report_file_and_line(tmp_path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text('# comment\n\n{"case_id": "c1"}\n{not json}\n', encoding="utf-8")
    with pytest.raises(HarnessInputError, match=r"golden.jsonl:4: invalid JSON"):
        load_jsonl(path)


def test_jsonl_skips_comments_and_blank_lines(tmp_path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text('# comment\n\n{"case_id": "c1"}\n', encoding="utf-8")
    assert [row["case_id"] for row in load_jsonl(path)] == ["c1"]


def test_validation_errors_point_at_the_line(tmp_path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text('{"case_id": "c1"}\n{"case_id": "c2", "budget": {}}\n', encoding="utf-8")
    with pytest.raises(HarnessInputError, match=r"golden.jsonl:2: unknown field 'budget'"):
        evaluate(path, [])


def test_missing_file_is_a_clear_error(tmp_path) -> None:
    with pytest.raises(HarnessInputError, match="cannot read"):
        load_jsonl(tmp_path / "nope.jsonl")
