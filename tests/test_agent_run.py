import json
from pathlib import Path

from evals.score import score_case, summarize
from tests.golden_cases import CASES

RUN = Path("evals/runs/2026-11-22-cursor-agent")


def test_committed_agent_run_matches_its_summary():
    summary = json.loads((RUN / "summary.json").read_text(encoding="utf-8"))
    rows = []
    for case in CASES:
        transcript_path = RUN / f"{case['id']}.json"
        if not transcript_path.is_file():
            continue
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        rows.append(score_case(case, transcript))
    fresh = summarize(rows)
    for key in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness"):
        assert fresh[key] == summary[key]
    assert fresh["failures"] == []
    assert summary["label"].startswith("agent-run")
    assert summary["cases"] == 40
