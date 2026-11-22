"""Call each non-fixture-only golden case against live NHTSA and print a short score."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.score import score_case, summarize
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service
from tests.conftest import run
from tests.golden_cases import CASES

LIVE_CACHE = Path("/tmp/glovebox-live-eval-cache")


def main() -> int:
    settings = Settings(
        fixtures_dir=None,
        investigations_file=None,
        cache_dir=LIVE_CACHE / "cache",
        data_dir=LIVE_CACHE / "data",
        offline=False,
        request_gap_seconds=0.4,
    )
    service = build_service(settings)
    rows = []
    for case in CASES:
        if case.get("eval_mode") == "fixture_only":
            continue
        if case.get("tool") is None:
            answer = " ".join(case["must_include"])
            transcript = {"tool_calls": [], "answer": answer}
        else:
            method = getattr(service, case["tool"])
            try:
                result = run(method, **case["arguments"])
            except Exception as exc:  # noqa: BLE001
                result = {"error": "runner_exception", "detail": str(exc)}
            transcript = {
                "tool_calls": [{"name": case["tool"], "arguments": case["arguments"], "result": result}],
                "answer": json.dumps(result),
            }
        rows.append(score_case(case, transcript))
    summary = summarize(rows)
    print(json.dumps(summary, indent=2))
    return 0 if not summary["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())