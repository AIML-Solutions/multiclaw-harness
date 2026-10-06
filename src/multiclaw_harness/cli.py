"""Command-line interface for MultiClaw Harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._version import __version__
from .evaluator import run_harness
from .reporting import render_markdown, render_summary
from .schema import HarnessInputError

EXIT_PASS = 0
EXIT_GATE_FAILED = 1
EXIT_INPUT_ERROR = 2

PACK_GOLDEN = "golden_cases.jsonl"
PACK_BASELINE = "baseline_run.jsonl"
PACK_CANDIDATE = "candidate_run.jsonl"

EPILOG = f"""\
examples:
  multiclaw-harness --pack packs/agentic-security
  multiclaw-harness --golden evals/golden.jsonl --run evals/run.jsonl --md-out reports/scorecard.md
  multiclaw-harness --golden evals/golden.jsonl --run baseline.jsonl --compare-run candidate.jsonl

A pack directory holds {PACK_GOLDEN}, {PACK_BASELINE} and, optionally, {PACK_CANDIDATE}.
When --compare-run is given, thresholds apply to the candidate and any regression vs --run fails the gate.

exit codes: 0 gate passed, 1 gate failed, 2 invalid input or usage
"""


def _fraction(value: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {value}")
    return number


def _count(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multiclaw-harness",
        description="Score agent trajectories against a golden set and gate releases on regressions.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    inputs = parser.add_argument_group("inputs")
    inputs.add_argument("--pack", type=Path, metavar="DIR", help="Pack directory; fills in any of the paths below")
    inputs.add_argument("--golden", type=Path, metavar="JSONL", help="Golden cases")
    inputs.add_argument("--run", type=Path, metavar="JSONL", help="Run traces to score (baseline if comparing)")
    inputs.add_argument("--compare-run", type=Path, metavar="JSONL", help="Candidate run traces to gate and compare")

    outputs = parser.add_argument_group("outputs")
    outputs.add_argument("--json-out", type=Path, metavar="PATH", help="Write the full JSON report here")
    outputs.add_argument("--md-out", type=Path, metavar="PATH", help="Write a Markdown scorecard here")
    outputs.add_argument("-q", "--quiet", action="store_true", help="Print only the gate verdict")

    gate = parser.add_argument_group("gate")
    gate.add_argument("--min-pass-rate", type=_fraction, default=0.95, help="Minimum case pass rate (default 0.95)")
    gate.add_argument("--min-overall", type=_fraction, default=0.90, help="Minimum mean overall score (default 0.90)")
    gate.add_argument(
        "--max-forbidden-hits", type=_count, default=0, help="Forbidden tool calls tolerated in total (default 0)"
    )
    gate.add_argument("--allow-regressions", action="store_true", help="Do not fail on regressions vs the baseline")
    return parser


def _resolve_pack(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.pack is not None:
        if not args.pack.is_dir():
            parser.error(f"--pack {args.pack}: not a directory")
        args.golden = args.golden or args.pack / PACK_GOLDEN
        args.run = args.run or args.pack / PACK_BASELINE
        candidate = args.pack / PACK_CANDIDATE
        if args.compare_run is None and candidate.is_file():
            args.compare_run = candidate
    if args.golden is None or args.run is None:
        parser.error("provide --pack DIR, or both --golden and --run")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _resolve_pack(parser, args)

    try:
        report = run_harness(
            args.golden,
            args.run,
            args.compare_run,
            min_pass_rate=args.min_pass_rate,
            min_overall=args.min_overall,
            allow_regressions=args.allow_regressions,
            max_forbidden_hits=args.max_forbidden_hits,
        )
        written = []
        for path, content in (
            (args.json_out, lambda: json.dumps(report, indent=2) + "\n"),
            (args.md_out, lambda: render_markdown(report)),
        ):
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content(), encoding="utf-8")
                written.append(path)
    except HarnessInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except OSError as exc:
        print(f"error: cannot write {exc.filename}: {exc.strerror}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    gate = report["gate"]
    if args.quiet:
        print("GATE PASS" if gate["passed"] else "GATE FAIL")
        for reason in gate["failures"]:
            print(f"  - {reason}")
    else:
        print(render_summary(report))
        if written:
            print()
        for path in written:
            print(f"wrote {path}")
    return EXIT_PASS if gate["passed"] else EXIT_GATE_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
