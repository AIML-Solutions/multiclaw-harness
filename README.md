# MultiClaw Harness

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e.svg)](LICENSE)

**Production-grade regression harnesses for agentic AI workflows.**

MultiClaw Harness turns agent behavior into testable engineering evidence: tool-call assertions, forbidden-action checks, trajectory diffs, outcome rubrics, cost/latency budgets, and CI gates that fail when behavior drifts.

It is designed for teams asking the practical question:

> Did this model, prompt, retrieval, config, or tool change make the agent worse?

## What It Evaluates

- Expected tool-call sequences and allowed alternatives
- Forbidden tools or unsafe actions
- Missing or extra trajectory steps
- Outcome rubric coverage
- Per-run latency and cost budgets
- Baseline-vs-candidate regression deltas

## Quick Start

```bash
python -m multiclaw_harness.cli \
  --golden examples/golden_cases.jsonl \
  --run examples/baseline_run.jsonl \
  --compare-run examples/candidate_run.jsonl \
  --json-out reports/scorecard.json \
  --md-out reports/scorecard.md
```

Expected baseline aggregate:

```text
pass_rate: 1.0
overall_score: 1.0
```

The candidate run intentionally regresses. It demonstrates how the harness flags prompt-injection leakage, unsafe tool calls, retrieval drift, and cost/latency budget failures.

Sample output:

- [`docs/examples/core-scorecard.md`](docs/examples/core-scorecard.md)
- [`docs/examples/agentic-security-scorecard.md`](docs/examples/agentic-security-scorecard.md)

## Example Domains

The included examples are public-safe synthetic tasks:

- agentic security review workflow
- retrieval-quality workflow
- runtime handoff workflow
- customer-support triage workflow

## Harness Packs

### Agentic Security

`packs/agentic-security` contains synthetic adversarial fixtures for tool-using agents:

- prompt-injection tool override
- credential-exfiltration request
- sandbox-escape attempt
- untrusted retrieval instruction
- approval-bypass attempt
- unsafe network action

Run it with:

```bash
python -m multiclaw_harness.cli \
  --golden packs/agentic-security/golden_cases.jsonl \
  --run packs/agentic-security/baseline_run.jsonl \
  --compare-run packs/agentic-security/candidate_run.jsonl \
  --json-out reports/agentic-security-scorecard.json \
  --md-out reports/agentic-security-scorecard.md \
  --allow-regressions
```

The pack is a public-safe reference architecture. It uses synthetic fixtures only and makes no claim of certification, classified-system readiness, or coverage of any named customer/employer program.

No client data, credentials, private runtime paths, paid-task details, or employer-targeted material is included.

### Trustworthy AI

`packs/trustworthy-ai` contains synthetic decision-support fixtures for calibration, explanation faithfulness, drift detection, human override, stale-data warnings, and model-card/release documentation gates.

Run it with:

```bash
python -m multiclaw_harness.cli \
  --golden packs/trustworthy-ai/golden_cases.jsonl \
  --run packs/trustworthy-ai/baseline_run.jsonl \
  --compare-run packs/trustworthy-ai/candidate_run.jsonl \
  --json-out reports/trustworthy-ai-scorecard.json \
  --md-out reports/trustworthy-ai-scorecard.md \
  --allow-regressions
```

The pack is synthetic and public-safe. It demonstrates an evaluation pattern for decision-support trust gates; it does not claim certification, ATO readiness, or compliance approval.

Planned packs are tracked in [`ROADMAP.md`](ROADMAP.md). Planned items are development direction, not claims that the pack is already implemented.

## Schema

Golden cases are JSONL rows with:

- `case_id`
- `task_family`
- `input`
- `expected_tools`
- `allowed_alternatives`
- `forbidden_tools`
- `budgets`
- `rubric`
- `provenance`

Runs are JSONL rows with:

- `case_id`
- `tools`
- `outcome_text`
- `latency_ms`
- `estimated_cost_usd`
- `metadata`

## CI Gate Pattern

Use a baseline run as the expected healthy behavior and compare candidates before release:

```text
golden set -> replay run -> score trajectory -> compare baseline -> fail on drift
```

Recommended gate conditions:

- `pass_rate` must stay above threshold
- `overall_score` must not drop below threshold
- forbidden hits must be zero
- latency and cost budgets must pass unless explicitly waived

## How This Fits AIML Solutions

MultiClaw Harness is the evaluation layer for AIML Solutions' agentic AI systems work. It complements:

- `AgentTools` for CLI skills and harness-audit artifacts
- `RecallOps` for retrieval/provenance infrastructure
- `AssureOps` for claims/evidence/monitor review
- `MultiClaw` for operating-model governance

## Public Safety

Keep examples synthetic or public-data-only. Do not commit credentials, client specifics, private opportunity context, paid-task details, private runtime paths, or sensitive operational logs.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution standards and public-safety rules.

## License

MIT — see [LICENSE](LICENSE).
