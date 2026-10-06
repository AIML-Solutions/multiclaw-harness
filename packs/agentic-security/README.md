# Agentic Security Pack

Synthetic adversarial fixtures for evaluating tool-using agents.

This pack tests whether an agent respects tool authorization, sandbox boundaries, approval gates, and public/private safety when facing malicious or untrusted instructions.

## What It Covers

- prompt-injection attempts to override tool policy
- credential-exfiltration requests
- sandbox-escape attempts
- malicious instructions retrieved from untrusted context
- approval-bypass attempts
- unsafe network actions

## Public-Safe Boundary

These are reference fixtures on synthetic data. They do not include classified data, ITAR data, customer data, employer program details, credentials, or operational security claims.

Use this as a demonstrator of how to evaluate agentic tool-use safety, not as a certification or completed security product.

## Run

```bash
multiclaw-harness --pack packs/agentic-security
```

The baseline passes the gate. The candidate run is intentionally unsafe, so the gate fails (exit code `1`) and lists every regression. Add `--md-out reports/agentic-security-scorecard.md` to save a scorecard; a current sample is in [`docs/examples`](../../docs/examples/agentic-security-scorecard.md).

## Intended Interpretation

The value is not the individual prompt text. The value is the engineering pattern:

```text
synthetic adversarial case -> expected safe trajectory -> candidate trace -> regression scorecard -> CI gate
```

For real deployments, replace these synthetic cases with private, domain-specific traces and policy rules.
