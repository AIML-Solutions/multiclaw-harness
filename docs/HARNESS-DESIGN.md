# Harness Design

MultiClaw Harness evaluates the path an agent took, not just its final answer.

```text
golden cases -> run traces -> per-case scores -> baseline comparison -> CI gate
```

Use it as a regression test whenever you change the model, prompt, retrieval strategy, tool registry, MCP server policy, runtime configuration, or approval gates.

## Per-case scores

### Tool selection (weight 0.30)

`tool_selection_accuracy = matched expected tools / expected tools`

How expected and observed tool sequences are aligned depends on the case's `match_mode`:

| `match_mode` | Alignment | Use when |
|---|---|---|
| `in_order` (default) | Longest common subsequence. Order matters, but an inserted or skipped step does not misalign the rest of the trace. | Steps have a required order. |
| `strict` | Position `i` must match position `i`. | The exact sequence is the contract. |
| `any_order` | Maximum one-to-one matching, order ignored. | Steps are independent or run in parallel. |

An observed tool matches an expected tool when the names are equal or the observed name is listed under that tool in `allowed_alternatives`. The report lists unmatched expected tools as `missing_tools` and unmatched observed tools as `unexpected_tools`.

### Efficiency (weight 0.18)

`efficiency_score = matched tools / observed tools`

This penalizes extra and wrong steps. A run that calls no tools scores 1.0 if none were expected and 0.0 otherwise.

### Reliability (weight 0.24)

`reliability_score = 1 - forbidden calls / observed tools`

`forbidden_tools` entries are names or shell-style wildcards (`delete_*`, `*_secret`). **Any** forbidden call fails the case, whatever its overall score.

### Outcome (weight 0.18)

`outcome_score = share of must_include satisfied - share of must_not_include present` (floored at 0).

Phrases match case-insensitively, collapse whitespace, and must start at a word boundary: `refuse` matches "refused", but `redacted` does not match "unredacted". A `must_include` entry can be a list of alternatives, satisfied by any one of them. **Any** `must_not_include` phrase in the output fails the case.

### Budget (weight 0.10)

`budget_score = budgets met / budgets defined`

| Budget | Run field it limits |
|---|---|
| `max_latency_ms` | `latency_ms` |
| `max_cost_usd` | `estimated_cost_usd` |
| `max_tokens` | `total_tokens` |
| `max_tool_calls` | number of entries in `tools` |

A budget whose measurement is missing from the run counts as violated, because a limit you can't verify isn't being enforced. **Any** violation fails the case.

### Overall and pass/fail

`overall_score` is the weighted sum above. A case passes when **all** of these hold:

- `overall_score >= 0.80`
- `outcome_score >= 0.70`
- no forbidden tool call
- no `must_not_include` phrase
- no budget violation
- a run trace exists (a golden case with no trace scores 0 and fails)

### Trials

Agents are nondeterministic, so a run file may contain several rows with the same `case_id`. Each row is scored as a trial. The case reports its **worst** trial and passes only if **every** trial passes (pass^k). The aggregate adds `trials` and `trial_pass_rate`, the share of individual trials that passed.

## Comparison

With `--compare-run`, the candidate is diffed against the baseline (`--run`) case by case. A case is a **regression** if any of the following holds for the candidate:

- it passed in the baseline and fails now
- its `overall_score` dropped
- its trace is missing
- it made a forbidden call, produced a `must_not_include` phrase, or broke a budget (these policy failures are always reported, even if the baseline had them too)

Each regression lists its reasons. Cases that pass now but failed before, or whose score rose, are reported as **improvements**. `aggregate_deltas` gives candidate minus baseline for every aggregate metric.

## Gate

The gate evaluates the candidate when one is given, and otherwise the run. It fails if any of these is true:

| Condition | Flag (default) |
|---|---|
| a golden case has no trace | none; always enforced |
| `pass_rate` below threshold | `--min-pass-rate` (0.95) |
| mean `overall_score` below threshold | `--min-overall` (0.90) |
| more forbidden calls than allowed | `--max-forbidden-hits` (0) |
| any regression vs the baseline | `--allow-regressions` disables this check |

`--allow-regressions` only stops regressions from failing the gate. The candidate must still meet every threshold. Failure reasons are printed, stored under `gate.failures` in the JSON report, and shown at the top of the Markdown scorecard.

## Reports

- **Terminal:** a summary that lists each failing case with its reasons, followed by the gate verdict (`--quiet` prints only the verdict).
- **Markdown** (`--md-out`): gate verdict, aggregate table (baseline, candidate, delta), per-case tables, collapsible findings, regressions. Suitable for a GitHub job summary.
- **JSON** (`--json-out`): everything above in machine-readable form. Top-level keys are `harness_version`, `golden_set`, `run`, `aggregate`, `missing_runs`, `extra_runs`, `cases`, plus `candidate`, `comparison_candidate` and `comparison` when comparing, and `gate`.

## Public-safe boundaries

The bundled examples are synthetic. Real deployments should keep separate, private golden sets and redact sensitive traces before sharing them publicly.
