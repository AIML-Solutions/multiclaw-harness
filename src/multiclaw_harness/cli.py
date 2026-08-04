"""Command-line interface for MultiClaw Harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import compare, evaluate, gate_passed
from .reporting import write_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate agentic workflow trajectories against a golden set.")
    parser.add_argument("--golden", type=Path, required=True, help="Golden case JSONL file")
    parser.add_argument("--run", type=Path, required=True, help="Baseline/current run JSONL file")
    parser.add_argument("--compare-run", type=Path, help="Candidate run JSONL file for regression comparison")
    parser.add_argument("--json-out", type=Path, required=True, help="Output JSON scorecard")
    parser.add_argument("--md-out", type=Path, required=True, help="Output Markdown scorecard")
    parser.add_argument("--min-pass-rate", type=float, default=0.95, help="Minimum pass rate for gate success")
    parser.add_argument("--min-overall", type=float, default=0.90, help="Minimum aggregate overall score for gate success")
    parser.add_argument("--allow-regressions", action="store_true", help="Do not fail the gate on candidate regressions")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate(args.golden, args.run)
    comparison = None
    if args.compare_run:
        comparison = compare(report, evaluate(args.golden, args.compare_run))
        report["comparison_candidate"] = str(args.compare_run)
        report["comparison"] = comparison

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, args.md_out, comparison=comparison)
    print(f"wrote {args.json_out}")
    print(f"wrote {args.md_out}")
    return 0 if gate_passed(report, args.min_pass_rate, args.min_overall, args.allow_regressions) else 2


if __name__ == "__main__":
    raise SystemExit(main())
