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
ruff format --check .
pytest
```

Tests also run from a fresh clone without installing (`python -m pytest`).

Run a pack end to end:

```bash
multiclaw-harness --pack examples
multiclaw-harness --pack packs/agentic-security
multiclaw-harness --pack packs/trustworthy-ai
```

Each pack's candidate is intentionally unsafe, so these commands exit `1` (gate failed). That is the expected result, and CI requires it.

If you change scoring or report rendering, regenerate the sample scorecards and commit them; `tests/test_examples.py` fails when they are stale:

```bash
python scripts/update_examples.py
```

## Adding a Harness Pack

1. Create `packs/<name>/` with `golden_cases.jsonl`, `baseline_run.jsonl`, `candidate_run.jsonl`, and a `README.md` that states the pack's public-safety boundary (see [`docs/SCHEMA.md`](docs/SCHEMA.md)).
2. Make sure the baseline passes the gate and the candidate is blocked: `multiclaw-harness --pack packs/<name>`.
3. Add a test in `tests/` and the pack to the `harness-gate` matrix in `.github/workflows/ci.yml`.
4. List the pack in the README and move it from planned to current in `ROADMAP.md`.
5. Add an entry under a new version heading in `CHANGELOG.md`.
