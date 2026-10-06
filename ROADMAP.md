# MultiClaw Harness Roadmap

This roadmap lists what is implemented today and the planned direction for the core evaluator and the public-safe harness packs. Planned items are not product claims; they are development direction for reference architectures and synthetic/public-data fixtures.

## Current

### Core Trajectory Harness

Status: implemented (0.2.0).

- JSONL golden cases and run traces with validated schema and file:line errors
- tool-sequence alignment: `in_order` (LCS), `strict`, `any_order`
- allowed alternatives and wildcard forbidden-action checks
- outcome rubrics with any-of phrases
- latency, cost, token, and tool-call budgets
- repeated trials per case (pass only if every trial passes)
- baseline-vs-candidate regression and improvement reports
- Markdown and JSON scorecards, terminal summary with gate reasons
- CI gate via CLI exit code, Python API, and reusable GitHub Action

### Agentic Security Pack

Status: implemented with synthetic fixtures.

- prompt-injection tool override
- credential-exfiltration request
- sandbox-escape attempt
- untrusted retrieval instruction
- approval-bypass attempt
- unsafe network action

### Trustworthy AI Pack

Status: implemented with synthetic fixtures.

Goal: evaluate decision-support workflows for calibration, explanation quality, drift, override handling, and auditability.

Cases:

- confidence calibration check
- explanation-faithfulness check
- drift-detection gate
- human-override audit trail
- stale-data warning
- model-card update requirement

Future metrics:

- calibration bucket error
- explanation support coverage
- drift threshold pass/fail
- override recorded yes/no
- audit trail completeness
- stale-data warning present

## Planned Packs

### Regulatory RAG Pack

Goal: evaluate retrieval quality over public regulatory or policy corpora.

Candidate metrics:

- citation grounding
- context precision
- context recall
- faithfulness
- abstention correctness
- source freshness and provenance

### Disconnected MLOps Pack

Goal: evaluate reference delivery patterns for constrained or offline environments.

Candidate checks:

- reproducible build hash
- SBOM presence
- vulnerability gate
- image provenance labels
- offline install smoke test
- manifest validation

### Edge Inference Pack

Goal: evaluate constrained inference tradeoffs using public models and datasets.

Candidate metrics:

- accuracy retention after quantization
- latency budget
- memory footprint
- model-size tradeoff
- degradation curve

### Multi-Source Analysis Pack

Goal: evaluate public/synthetic multi-source analysis workflows.

Candidate metrics:

- detection precision/recall
- geolocation error bounds
- entity-resolution precision/recall/F1
- track continuity
- provenance completeness
- analyst-style report rubric

## Planned Core Improvements

Direction for the evaluator itself; not yet implemented.

- trace importers for common agent logs (OpenTelemetry GenAI spans, Anthropic and OpenAI message transcripts, MCP tool-call logs)
- tool-argument assertions (expected or forbidden argument values, not just tool names)
- optional model-graded rubric hook for criteria that phrase matching can't express
- per-case flakiness budgets for multi-trial runs (for example, pass if at least 4 of 5 trials pass)
- task-family breakdowns in aggregate reports

## Public-Safety Rules

- Use synthetic or public-data-only examples.
- Do not include customer data, private opportunity context, credentials, paid-task details, private runtime paths, or sensitive operational logs.
- Do not imply access to classified, ITAR-controlled, customer, or employer-program data.
- Do not claim certification, compliance approval, production security assurance, or named-program involvement unless independently true and explicitly approved for public use.
