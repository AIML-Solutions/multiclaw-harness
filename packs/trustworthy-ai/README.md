# Trustworthy AI Pack

Synthetic decision-support fixtures for evaluating whether an AI workflow has enough trust evidence to support operational use.

This pack tests calibration, explanation faithfulness, drift detection, human override handling, stale-data warnings, and model-card/release documentation. It is a public-safe reference architecture, not a certification or compliance claim.

## What It Covers

- confidence calibration and overconfidence checks
- explanation faithfulness against evidence traces
- drift detection and release blocking
- human override audit trails
- stale source-data warnings
- model/config change documentation gates

## Public-Safe Boundary

These fixtures are synthetic. They do not include classified data, ITAR data, customer data, employer program details, credentials, or regulated decisions.

Use this pack to demonstrate the evaluation pattern, not to claim production approval, ATO readiness, certification, or compliance status.

## Run

```bash
multiclaw-harness --pack packs/trustworthy-ai
```

The baseline passes every case. The candidate run intentionally fails every case so the regression behavior is obvious: the gate fails (exit code `1`) and lists each regression. Add `--md-out reports/trustworthy-ai-scorecard.md` to save a scorecard; a current sample is in [`docs/examples`](../../docs/examples/trustworthy-ai-scorecard.md).

## Intended Interpretation

```text
trust case -> expected evidence checks -> candidate trace -> scorecard -> CI gate
```

For real deployments, replace these synthetic fixtures with private policies, traces, decision logs, and domain-specific review thresholds.
