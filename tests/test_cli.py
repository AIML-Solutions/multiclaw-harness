import json
from pathlib import Path

import pytest

from multiclaw_harness import __version__
from multiclaw_harness.cli import main

ROOT = Path(__file__).resolve().parents[1]
PACKS = [ROOT / "examples", ROOT / "packs/agentic-security", ROOT / "packs/trustworthy-ai"]


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_baseline_passes_gate(pack: Path, capsys) -> None:
    code = main(["--golden", str(pack / "golden_cases.jsonl"), "--run", str(pack / "baseline_run.jsonl")])
    assert code == 0
    assert "GATE PASS" in capsys.readouterr().out


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_pack_gate_blocks_unsafe_candidate(pack: Path, capsys) -> None:
    assert main(["--pack", str(pack)]) == 1
    out = capsys.readouterr().out
    assert "GATE FAIL" in out
    assert "regression(s) vs baseline" in out


def test_allow_regressions_does_not_hide_failing_candidate(capsys) -> None:
    assert main(["--pack", str(PACKS[0]), "--allow-regressions"]) == 1


def test_reports_are_written(tmp_path: Path, capsys) -> None:
    json_out = tmp_path / "nested" / "scorecard.json"
    md_out = tmp_path / "scorecard.md"
    main(["--pack", str(PACKS[1]), "--json-out", str(json_out), "--md-out", str(md_out)])
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["harness_version"] == __version__
    assert report["gate"]["passed"] is False
    assert len(report["candidate"]["cases"]) == 6
    assert md_out.read_text(encoding="utf-8").startswith("# MultiClaw Harness Scorecard")
    assert f"wrote {md_out}" in capsys.readouterr().out


def test_quiet_prints_only_verdict(capsys) -> None:
    main(["--pack", str(PACKS[0]), "--quiet"])
    out = capsys.readouterr().out
    assert out.startswith("GATE FAIL")
    assert "MultiClaw Harness" not in out


def test_input_error_exits_2_with_message(tmp_path: Path, capsys) -> None:
    golden = tmp_path / "golden.jsonl"
    golden.write_text('{"case_id": "c1", "forbiden_tools": []}\n', encoding="utf-8")
    assert main(["--golden", str(golden), "--run", str(golden)]) == 2
    assert "did you mean 'forbidden_tools'" in capsys.readouterr().err


def test_missing_inputs_is_a_usage_error(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--golden", "g.jsonl"])
    assert exc.value.code == 2
    assert "--pack DIR, or both --golden and --run" in capsys.readouterr().err


def test_threshold_must_be_a_fraction(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--pack", str(PACKS[0]), "--min-pass-rate", "95"])
    assert "between 0 and 1" in capsys.readouterr().err


def test_version(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out
