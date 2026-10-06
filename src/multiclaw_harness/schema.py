"""Loading and validation for golden-case and run JSONL files.

Validation fails closed: a typo such as ``forbiden_tools`` or ``max_latency`` would otherwise silently
disable a safety check, so unknown keys and malformed values are rejected with a pointer to the offending
file and line.
"""

from __future__ import annotations

import difflib
import json
from collections.abc import Iterable, Mapping
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

MATCH_MODES = ("in_order", "strict", "any_order")

# Golden-case budget key -> run field it limits. ``tool_calls`` is derived from the run's ``tools`` list.
BUDGET_FIELDS = {
    "max_latency_ms": "latency_ms",
    "max_cost_usd": "estimated_cost_usd",
    "max_tokens": "total_tokens",
    "max_tool_calls": "tool_calls",
}

GOLDEN_KEYS = {
    "case_id",
    "task_family",
    "input",
    "match_mode",
    "expected_tools",
    "allowed_alternatives",
    "forbidden_tools",
    "budgets",
    "rubric",
    "provenance",
    "metadata",
    "tags",
    "notes",
}
RUBRIC_KEYS = {"must_include", "must_not_include"}


class HarnessInputError(ValueError):
    """Raised when a golden set or run file is malformed."""


Source = str | Path | Iterable[Mapping[str, Any]]


Rows = list[tuple[int, dict[str, Any]]]


def _read_jsonl(path: str | Path) -> Rows:
    path = Path(path)
    rows: Rows = []
    try:
        fh = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise HarnessInputError(f"cannot read {path}: {exc.strerror or exc}") from exc
    with fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HarnessInputError(f"{path}:{n}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise HarnessInputError(f"{path}:{n}: each line must be a JSON object")
            rows.append((n, row))
    return rows


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines and ``#`` comment lines."""
    return [row for _, row in _read_jsonl(path)]


def read_rows(source: Source) -> tuple[str, Rows]:
    """Return ``(label, [(line, row), ...])`` for a JSONL path or an in-memory iterable of dicts."""
    if isinstance(source, (str, Path)):
        return str(source), _read_jsonl(source)
    rows: Rows = []
    for n, row in enumerate(source, 1):
        if not isinstance(row, Mapping):
            raise HarnessInputError(f"<memory>:{n}: each row must be a mapping")
        rows.append((n, dict(row)))
    return "<memory>", rows


def _suggest(key: str, choices: Iterable[str]) -> str:
    match = difflib.get_close_matches(key, sorted(choices), n=1)
    return f" (did you mean '{match[0]}'?)" if match else ""


def _str_list(value: Any, field: str, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise HarnessInputError(f"{where}: '{field}' must be a list of strings")
    return value


def _phrase(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _case_id(row: Mapping[str, Any], where: str) -> str:
    case_id = row.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise HarnessInputError(f"{where}: 'case_id' is required and must be a non-empty string")
    return case_id


def validate_golden(label: str, rows: Rows) -> dict[str, dict[str, Any]]:
    """Validate golden cases and return them keyed by ``case_id``."""
    cases: dict[str, dict[str, Any]] = {}
    for line, row in rows:
        where = f"{label}:{line}"
        case_id = _case_id(row, where)
        if case_id in cases:
            raise HarnessInputError(f"{where}: duplicate case_id '{case_id}'")

        for key in row:
            if key not in GOLDEN_KEYS:
                raise HarnessInputError(
                    f"{where}: unknown field '{key}'{_suggest(key, GOLDEN_KEYS)}; put custom data under 'metadata'"
                )

        mode = row.get("match_mode", "in_order")
        if mode not in MATCH_MODES:
            raise HarnessInputError(f"{where}: 'match_mode' must be one of {', '.join(MATCH_MODES)}")

        expected = _str_list(row.get("expected_tools", []), "expected_tools", where)
        forbidden = _str_list(row.get("forbidden_tools", []), "forbidden_tools", where)

        alternatives = row.get("allowed_alternatives", {}) or {}
        if not isinstance(alternatives, dict):
            raise HarnessInputError(f"{where}: 'allowed_alternatives' must be an object of tool -> [alternatives]")
        for tool, alts in alternatives.items():
            if tool not in expected:
                raise HarnessInputError(
                    f"{where}: allowed_alternatives key '{tool}' is not in expected_tools{_suggest(tool, expected)}"
                )
            _str_list(alts, f"allowed_alternatives.{tool}", where)

        allowed = set(expected) | {alt for alts in alternatives.values() for alt in alts}
        conflicts = sorted(tool for tool in allowed if any(fnmatchcase(tool, pattern) for pattern in forbidden))
        if conflicts:
            raise HarnessInputError(f"{where}: tools are both expected and forbidden: {', '.join(conflicts)}")

        budgets = row.get("budgets", {}) or {}
        if not isinstance(budgets, dict):
            raise HarnessInputError(f"{where}: 'budgets' must be an object")
        for key, limit in budgets.items():
            if key not in BUDGET_FIELDS:
                raise HarnessInputError(
                    f"{where}: unknown budget '{key}'{_suggest(key, BUDGET_FIELDS)}; "
                    f"supported: {', '.join(BUDGET_FIELDS)}"
                )
            if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit < 0:
                raise HarnessInputError(f"{where}: budget '{key}' must be a non-negative number")

        rubric = row.get("rubric", {}) or {}
        if not isinstance(rubric, dict):
            raise HarnessInputError(f"{where}: 'rubric' must be an object")
        for key in rubric:
            if key not in RUBRIC_KEYS:
                raise HarnessInputError(f"{where}: unknown rubric field '{key}'{_suggest(key, RUBRIC_KEYS)}")
        for item in rubric.get("must_include", []):
            any_of = isinstance(item, list) and item and all(_phrase(x) for x in item)
            if not (_phrase(item) or any_of):
                raise HarnessInputError(
                    f"{where}: rubric.must_include items must be non-empty strings or lists of alternative strings"
                )
        must_not = _str_list(rubric.get("must_not_include", []), "rubric.must_not_include", where)
        if not all(_phrase(x) for x in must_not):
            raise HarnessInputError(f"{where}: rubric.must_not_include phrases must be non-empty")

        cases[case_id] = row
    return cases


def tool_name(call: Any) -> str | None:
    """Accept a bare tool name or a structured call such as ``{"name": "search", "args": {...}}``."""
    if isinstance(call, str):
        return call
    if isinstance(call, Mapping):
        name = call.get("name", call.get("tool"))
        if isinstance(name, str):
            return name
    return None


def validate_runs(label: str, rows: Rows) -> dict[str, list[dict[str, Any]]]:
    """Validate run rows and group them by ``case_id``. Repeated ``case_id`` rows are trials of one case."""
    runs: dict[str, list[dict[str, Any]]] = {}
    for line, row in rows:
        where = f"{label}:{line}"
        case_id = _case_id(row, where)
        tools = row.get("tools", [])
        if not isinstance(tools, list):
            raise HarnessInputError(f"{where}: 'tools' must be a list")
        names = []
        for call in tools:
            name = tool_name(call)
            if name is None:
                raise HarnessInputError(f"{where}: each tool call must be a string or an object with a 'name'")
            names.append(name)
        for field in ("latency_ms", "estimated_cost_usd", "total_tokens"):
            value = row.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise HarnessInputError(f"{where}: '{field}' must be a number")
        outcome = row.get("outcome_text", "")
        if outcome is not None and not isinstance(outcome, str):
            raise HarnessInputError(f"{where}: 'outcome_text' must be a string")
        runs.setdefault(case_id, []).append({**row, "tools": names})
    return runs
