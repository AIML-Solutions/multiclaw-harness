"""MultiClaw Harness: regression gates for agentic AI workflow trajectories."""

from ._version import __version__
from .evaluator import CaseScore, compare, evaluate, gate_failures, gate_passed, run_harness, score_case
from .reporting import render_markdown, render_summary
from .schema import HarnessInputError, load_jsonl

__all__ = [
    "CaseScore",
    "HarnessInputError",
    "__version__",
    "compare",
    "evaluate",
    "gate_failures",
    "gate_passed",
    "load_jsonl",
    "render_markdown",
    "render_summary",
    "run_harness",
    "score_case",
]
