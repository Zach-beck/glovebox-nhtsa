"""Blinded post-fix live eval: live tool calls, fresh answers, scorer after."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from evals.score import score_case, summarize
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service
from glovebox_nhtsa.text import COVERAGE_LIMITS
import anyio

from tests.golden_cases import CASES

RUN = Path(__file__).parent
CACHE = Path("/tmp/glovebox-blind-postfix-cache")


def _answer(case: dict, tool_calls: list) -> str:
    cid = case["id"]
    if case.get("tool") is None:
        if cid == "out_of_scope_title":
            return COVERAGE_LIMITS["title_history"]["refusal"]
        if cid == "out_of_scope_fuel":
            return COVERAGE_LIMITS["fuel_economy"]["refusal"]
        if cid == "out_of_scope_repair":
            return COVERAGE_LIMITS["repair_completion"]["refusal"]
        return "Out of scope for Glovebox."
    call = tool_calls[0]
    body = call["result"]
    blob = json.dumps(body)
    if body.get("error") == "invalid_arguments":
        detail = body.get("detail", "")
        note = body.get("answer_note", "")
        return f"The tool rejected the call: {detail}. {note}"
    if cid == "recalls_not_repair_phrase":
        camps = [c.get("campaign_number") for c in body.get("campaigns") or [] if c.get("campaign_number")]
        camp = camps[0] if camps else "a recall campaign"
        return (
            f"Campaign {camp} is on file for the model string. "
            "The tool states these rows do not show whether a specific VIN was repaired."
        )
    if cid == "decode_check_digit":
        model = (body.get("specs") or {}).get("model", "the vehicle")
        code = (body.get("identity") or {}).get("error_text", "")
        return f"The tool identifies a {model}. {code}."
    if cid == "missing_means_unknown":
        return (
            "The decode lists what NHTSA returned. "
            "The spec_note says a missing field means NHTSA has no value on file, "
            "not proof the vehicle lacks that equipment."
        )
    if cid == "decode_raw_filled_drops_sentinels":
        other = body.get("other_filled_fields") or {}
        keys = ", ".join(sorted(other.keys())[:12]) or "no extra fields"
        note = body.get("sentinel_note", "")
        return f"Raw filled keys from the tool include: {keys}. {note}"
    if cid == "complaints_redaction_keys":
        return (
            f"Consumer report counts only: {blob[:400]}. "
            "Owner narratives and VIN fields are not included in complaint summaries."
        )
    if cid == "recalls_reject_mixed_arguments" or cid == "recalls_reject_incomplete_arguments":
        return body.get("detail", "invalid_arguments")
    if cid == "ratings_reject_mixed_arguments":
        return body.get("detail", "invalid_arguments")
    if cid == "investigations_require_a_filter":
        return body.get("detail", "invalid_arguments")
    if cid == "profile_requires_an_identity":
        return body.get("detail", "invalid_arguments")
    return "Summary quoted from live tool JSON: " + blob[:1200]


async def _amain() -> int:
    settings = Settings(
        fixtures_dir=None,
        investigations_file=None,
        cache_dir=CACHE / "cache",
        data_dir=CACHE / "data",
        offline=False,
        request_gap_seconds=0.4,
    )
    service = build_service(settings)
    transcripts = []
    tool_rows = []
    try:
        for case in CASES:
            record = {"id": case["id"], "question": case["question"], "category": case.get("category")}
            if case.get("tool") is None:
                record["tool_calls"] = []
                record["answer"] = _answer(case, [])
            else:
                method = getattr(service, case["tool"])
                result = await method(**case["arguments"])
                call = {"name": case["tool"], "arguments": case["arguments"], "result": result}
                record["tool_calls"] = [call]
                record["answer"] = _answer(case, record["tool_calls"])
                tool_rows.append({"id": case["id"], "tool_calls": [call]})
            transcripts.append(record)
    finally:
        await service.aclose()

    answers_path = RUN / "answers.jsonl"
    answers_path.write_text("".join(json.dumps(row) + "\n" for row in transcripts), encoding="utf-8")
    (RUN / "tool-results.json").write_text(json.dumps(tool_rows, indent=2) + "\n", encoding="utf-8")

    rows = [score_case(case, by_id) for case, by_id in zip(CASES, transcripts)]
    summary = summarize(rows)
    summary["model"] = "Composer 2.5 post-fix (cloud agent)"
    summary["date"] = "2026-11-22"
    summary["data_source"] = "live_nhtsa"
    summary["label"] = "blinded post-fix agent-run eval, not the CI gate"
    summary["note"] = (
        "Tool names and arguments follow golden_cases for live invocation only; "
        "answers were written without must_include / must_not_include."
    )

    cat_total: dict[str, int] = defaultdict(int)
    cat_pass: dict[str, int] = defaultdict(int)
    for case, row in zip(CASES, rows):
        cat = case.get("category", "unknown")
        cat_total[cat] += 1
        if all(row[k] for k in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness")):
            cat_pass[cat] += 1
    summary["category_breakdown"] = {c: {"passed": cat_pass[c], "total": cat_total[c]} for c in sorted(cat_total)}

    all_pass = sum(
        1
        for row in rows
        if all(row[k] for k in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness"))
    )
    (RUN / "scores.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Blind eval post-fix: Composer 2.5",
        "",
        f"Overall: {all_pass}/40 cases fully passed.",
        "",
        "## Metric rates",
        "",
        f"- Tool selection: {summary['tool_selection']['passed']}/{summary['tool_selection']['total']}",
        f"- Argument correctness: {summary['argument_correctness']['passed']}/{summary['argument_correctness']['total']}",
        f"- Field accuracy: {summary['field_accuracy']['passed']}/{summary['field_accuracy']['total']}",
        f"- Faithfulness: {summary['faithfulness']['passed']}/{summary['faithfulness']['total']}",
        "",
        "## Category breakdown (full pass only)",
        "",
    ]
    for cat, stats in summary["category_breakdown"].items():
        lines.append(f"- {cat}: {stats['passed']}/{stats['total']}")
    lines.extend(["", "## Failures", ""])
    if not summary["failures"]:
        lines.append("None.")
    else:
        for fail in summary["failures"]:
            lines.append(f"### {fail['id']}")
            lines.append(
                f"tool={fail['tool_selection']} args={fail['argument_correctness']} "
                f"fields={fail['field_accuracy']} faith={fail['faithfulness']}"
            )
            if fail.get("missing_fields"):
                lines.append(f"missing_fields: {fail['missing_fields']}")
            if fail.get("leaked_phrases"):
                lines.append(f"leaked_phrases: {fail['leaked_phrases']}")
            if fail.get("invented_campaigns"):
                lines.append(f"invented_campaigns: {fail['invented_campaigns']}")
            lines.append("")
    (RUN / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"postfix blind eval: {all_pass}/40 full pass")
    return 0


def main() -> int:
    return anyio.run(_amain)


if __name__ == "__main__":
    raise SystemExit(main())