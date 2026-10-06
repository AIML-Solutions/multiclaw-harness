"""Regenerate the sample scorecards in docs/examples from the bundled packs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multiclaw_harness import render_markdown, run_harness  # noqa: E402

EXAMPLES = {
    "docs/examples/core-scorecard.md": "examples",
    "docs/examples/agentic-security-scorecard.md": "packs/agentic-security",
    "docs/examples/trustworthy-ai-scorecard.md": "packs/trustworthy-ai",
}


def main() -> None:
    os.chdir(ROOT)
    for doc, pack in EXAMPLES.items():
        report = run_harness(f"{pack}/golden_cases.jsonl", f"{pack}/baseline_run.jsonl", f"{pack}/candidate_run.jsonl")
        Path(doc).write_text(render_markdown(report), encoding="utf-8")
        print(f"wrote {doc}")


if __name__ == "__main__":
    main()
