# Contributing

MultiClaw Harness welcomes public-safe examples, tests, and documentation improvements.

## Standards

- Keep changes small and reviewable.
- Add or update tests for evaluator behavior.
- Include a runnable example for new harness patterns.
- Prefer synthetic fixtures unless a public dataset is clearly licensed for reuse.
- Keep README and docs accurate; planned work belongs in `ROADMAP.md`.

## Public-Safety Boundary

Do not contribute:

- credentials, tokens, cookies, keys, or `.env` contents
- customer data or private runtime paths
- paid-task, employer-targeted, or private opportunity details
- classified or ITAR-controlled data
- claims of certification, compliance approval, or named-program coverage without explicit public approval

## Local Checks

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

Run the core harness example:

```bash
python -m multiclaw_harness.cli \
  --golden examples/golden_cases.jsonl \
  --run examples/baseline_run.jsonl \
  --compare-run examples/candidate_run.jsonl \
  --json-out reports/scorecard.json \
  --md-out reports/scorecard.md \
  --allow-regressions
```

Run the agentic-security pack:

```bash
python -m multiclaw_harness.cli \
  --golden packs/agentic-security/golden_cases.jsonl \
  --run packs/agentic-security/baseline_run.jsonl \
  --compare-run packs/agentic-security/candidate_run.jsonl \
  --json-out reports/agentic-security-scorecard.json \
  --md-out reports/agentic-security-scorecard.md \
  --allow-regressions
```
