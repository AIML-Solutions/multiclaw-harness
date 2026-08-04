# Harness Design

MultiClaw Harness evaluates the path an agent took, not just its final answer.

## Core Idea

```text
golden cases -> run trace -> trajectory scoring -> baseline comparison -> CI gate
```

## Scoring Dimensions

- Tool selection: expected tools in expected order, with allowed alternatives.
- Efficiency: missing and extra steps compared to the golden sequence.
- Reliability: forbidden tool/action hits.
- Outcome: required terms present and prohibited terms absent.
- Budget: latency and estimated cost within case limits.

## Intended Use

Use this for regression testing when changing:

- model
- prompt
- retrieval strategy
- tool registry
- MCP server policy
- runtime configuration
- approval gates

## Public-Safe Boundaries

The included examples are synthetic. Real deployments should maintain separate private golden sets and redact sensitive traces before any public sharing.
