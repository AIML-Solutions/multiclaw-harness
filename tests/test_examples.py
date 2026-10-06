"""Keep the committed sample scorecards in docs/examples in sync with the harness output.

Regenerate them with ``python scripts/update_examples.py``.
"""

from pathlib import Path

import pytest

from multiclaw_harness import render_markdown, run_harness

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = {
    "docs/examples/core-scorecard.md": "examples",
    "docs/examples/agentic-security-scorecard.md": "packs/agentic-security",
    "docs/examples/trustworthy-ai-scorecard.md": "packs/trustworthy-ai",
}


@pytest.mark.parametrize("doc,pack", EXAMPLES.items())
def test_sample_scorecard_is_current(doc: str, pack: str, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    report = run_harness(f"{pack}/golden_cases.jsonl", f"{pack}/baseline_run.jsonl", f"{pack}/candidate_run.jsonl")
    committed = (ROOT / doc).read_text(encoding="utf-8")
    assert committed == render_markdown(report), f"{doc} is stale; run: python scripts/update_examples.py"
