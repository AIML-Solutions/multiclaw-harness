# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## 0.2.0 - 2026-10-06

### Fixed

- Tool sequences are now aligned by longest common subsequence. Previously, one inserted step shifted every later position and zeroed tool accuracy for a run that was otherwise correct.
- A single forbidden tool call now always fails its case. Previously, one forbidden call among ten or more tool calls could still pass.
- A golden case with no run trace is now scored as a failure and fails the gate. Previously, a candidate could pass by leaving out the cases it failed.
- Rubric phrases must now start at a word boundary, so `redacted` is no longer satisfied by "unredacted".
- Efficiency now penalizes wrong steps, not just a difference in sequence length.
- Duplicate golden `case_id`s are rejected instead of silently overwriting each other.

### Changed

- **Gate semantics:** with `--compare-run`, thresholds apply to the candidate (the change under test) instead of the baseline. `--allow-regressions` no longer lets a failing candidate pass.
- **Exit codes:** a failed gate now exits `1` (previously `2`); `2` now means invalid input or usage.
- A `must_not_include` phrase in the outcome now fails the case.
- A budget whose measurement is missing from the run now counts as a violation.
- `NaN` and `Infinity` are rejected in golden sets and runs, and `rubric.must_include` must be a list.
- `--json-out` and `--md-out` are optional; the CLI always prints a summary with the gate verdict and its reasons.
- The Markdown scorecard has been redesigned: gate verdict, baseline/candidate/delta table, per-case tables, findings, and regression reasons.
- Packaging now uses hatchling with a single-sourced version; tests run from a fresh clone without installing the package.

### Added

- `--pack DIR` shortcut for the `golden_cases.jsonl` / `baseline_run.jsonl` / `candidate_run.jsonl` layout.
- Gate failure reasons in the terminal output, the Markdown report, and `gate.failures` in the JSON report.
- `--max-forbidden-hits` (default 0), `--quiet`, and `--version`.
- Golden-set validation with file:line errors and "did you mean" suggestions for misspelled fields and budgets.
- `match_mode` per case: `in_order` (default), `strict`, `any_order`.
- Wildcards in `forbidden_tools` (for example `delete_*`).
- Any-of alternatives in `rubric.must_include`.
- `max_tokens` and `max_tool_calls` budgets.
- Structured tool calls in runs (`{"name": ..., "args": ...}`).
- Repeated trials per case: a case passes only if every trial passes, and the aggregate reports `trial_pass_rate`.
- `missing_tools`, `unexpected_tools`, and `budget_details` per case, plus regression `reasons` and an `improvements` list.
- Python API: `run_harness`, which accepts paths or in-memory traces, plus top-level exports.
- A reusable GitHub Action (`action.yml`) that writes the scorecard to the job summary.
- CI on Python 3.10–3.14, a format check, a check that the gate blocks every unsafe candidate, Dependabot for actions, and tests that keep the sample scorecards in sync.

## 0.1.0

- Initial reference harness: JSONL golden cases and runs, trajectory scoring, baseline comparison, Markdown/JSON scorecards, and the agentic-security and trustworthy-AI packs.

