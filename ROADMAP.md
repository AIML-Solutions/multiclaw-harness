# MultiClaw Harness Roadmap

This roadmap lists planned public-safe harness packs. Items here are not product claims; they are development direction for reference architectures and synthetic/public-data fixtures.

## Current

### Core Trajectory Harness

Status: implemented.

- JSONL golden cases and run traces
- expected tool-call sequence scoring
- allowed alternatives
- forbidden-action checks
- outcome rubrics
- latency and cost budgets
- baseline-vs-candidate regression comparison
- Markdown and JSON scorecards
- CI gate pattern

### Agentic Security Pack

Status: implemented with synthetic fixtures.

- prompt-injection tool override
- credential-exfiltration request
- sandbox-escape attempt
- untrusted retrieval instruction
- approval-bypass attempt
- unsafe network action

## Planned Packs

### Trustworthy AI Pack

Status: implemented with synthetic fixtures.

Goal: evaluate decision-support workflows for calibration, explanation quality, drift, override handling, and auditability.

Candidate cases:

- confidence calibration check
- explanation-faithfulness check
- drift-detection gate
- human-override audit trail
- stale-data warning
- model-card update requirement

Candidate metrics:

- calibration bucket error
- explanation support coverage
- drift threshold pass/fail
- override recorded yes/no
- audit trail completeness
- stale-data warning present

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

## Public-Safety Rules

- Use synthetic or public-data-only examples.
- Do not include customer data, private opportunity context, credentials, paid-task details, private runtime paths, or sensitive operational logs.
- Do not imply access to classified, ITAR-controlled, customer, or employer-program data.
- Do not claim certification, compliance approval, production security assurance, or named-program involvement unless independently true and explicitly approved for public use.
