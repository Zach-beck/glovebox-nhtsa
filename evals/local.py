"""Local model eval. Skips cleanly when no key is configured.

Keys are read from the environment or a gitignored .env in the current
directory. This module never asks for a key and never prints a key.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def _post_json(url: str, key: str, body: dict, opener=None) -> dict:
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def run_openai_cases(key: str, cases: list[dict], opener=None, model: str | None = None) -> dict:
    """One completion per case. The model is asked which tool name to call.

    This does not execute tools. It scores whether the reply names the expected
    tool. Faithfulness of a full answer is still the deterministic suite's job
    until a maintainer opts into a longer loop.
    """
    model_name = model or os.environ.get("EVAL_MODEL") or "gpt-4o-mini"
    hits = 0
    for case in cases:
        if not case.get("tool"):
            continue
        question = case.get("question") or case["id"].replace("_", " ")
        body = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Reply with only the tool name. Question: {question}. "
                        f"Tools: decode_vin, get_recalls, summarize_complaints, "
                        f"get_safety_ratings, search_investigations, list_model_names, "
                        f"vehicle_profile, vehicle_report, render_vehicle_report_html."
                    ),
                }
            ],
        }
        payload = _post_json("https://api.openai.com/v1/chat/completions", key, body, opener=opener)
        text = payload["choices"][0]["message"].get("content") or ""
        if case["tool"] in text:
            hits += 1
    considered = sum(1 for case in cases if case.get("tool"))
    return {
        "status": "completed",
        "provider": "openai",
        "model": model_name,
        "cases": considered,
        "tool_name_mentions": hits,
        "gate": "This run is not the CI gate.",
    }


def main() -> int:
    _load_dotenv(Path(".env"))
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not openai_key and not anthropic_key:
        report = {
            "status": "skipped",
            "reason": "No OPENAI_API_KEY or ANTHROPIC_API_KEY in the environment or .env.",
            "cases": 0,
            "gate": "This run is not the CI gate. CI runs the deterministic pytest suite only.",
        }
        print(json.dumps(report, indent=2))
        return 0
    if not openai_key:
        report = {
            "status": "skipped",
            "reason": "ANTHROPIC_API_KEY is set, and this runner only calls OpenAI when OPENAI_API_KEY is set.",
            "cases": 0,
            "gate": "This run is not the CI gate.",
        }
        print(json.dumps(report, indent=2))
        return 0
    repo_cases = Path(__file__).resolve().parents[1] / "tests" / "golden_cases.py"
    if not repo_cases.is_file():
        print(json.dumps({"status": "skipped", "reason": "Golden cases were not found.", "cases": 0}, indent=2))
        return 0
    sys.path.insert(0, str(repo_cases.parents[1]))
    from tests.golden_cases import CASES

    report = run_openai_cases(openai_key, CASES)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
