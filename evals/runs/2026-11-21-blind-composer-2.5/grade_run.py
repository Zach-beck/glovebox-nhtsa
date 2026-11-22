"""Score answers.jsonl against golden cases and write scores.json plus report.md."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from evals.score import score_case, summarize
from tests.golden_cases import CASES

RUN = Path(__file__).parent
transcripts = [
    json.loads(line)
    for line in (RUN / "answers.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
by_id = {t["id"]: t for t in transcripts}

rows = []
for case in CASES:
    rows.append(score_case(case, by_id[case["id"]]))

summary = summarize(rows)
summary["model"] = "Composer 2.5"
summary["date"] = "2026-11-21"
summary["data_source"] = "live_nhtsa"
summary["label"] = "blinded agent-run eval, not the CI gate"

# Per-category pass counts (all four metrics must pass).
cat_total: dict[str, int] = defaultdict(int)
cat_pass: dict[str, int] = defaultdict(int)
case_cat = {c["id"]: c.get("category", "unknown") for c in CASES}
for case, row in zip(CASES, rows):
    cat = case.get("category", "unknown")
    cat_total[cat] += 1
    if all(row[k] for k in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness")):
        cat_pass[cat] += 1

category_breakdown = {
    cat: {"passed": cat_pass[cat], "total": cat_total[cat]}
    for cat in sorted(cat_total)
}

summary["category_breakdown"] = category_breakdown
(RUN / "scores.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

# Failure cause notes without re-reading full golden expected (use scorer output only).
failure_notes: dict[str, str] = {
    "recalls_spelling_miss": "Server bug: NHTSA returns HTTP 400 with empty JSON; Glovebox surfaces upstream_unavailable instead of count 0.",
    "complaints_x3_counts": "Server bug: same HTTP 400 with empty body pattern on complaints_by_vehicle.",
    "complaints_component_filter": "Server bug: complaints_by_vehicle HTTP 400 handling.",
    "complaints_redaction_keys": "Server bug: complaints_by_vehicle HTTP 400 handling.",
    "complaints_unknown_component_is_zero": (
        "Model mistake: expected component BRAKES; server bug blocked count 0 anyway."
    ),
    "out_of_scope_title": "Model mistake: exact coverage phrase not used in answer.",
    "out_of_scope_fuel": "Model mistake: exact coverage phrase not used in answer.",
    "out_of_scope_repair": "Model mistake: exact coverage phrase not used in answer.",
    "missing_means_unknown": "Possible NHTSA data drift: live vPIC now returns airbags_side where fixture had an empty field.",
    "decode_raw_filled_drops_sentinels": "NHTSA data drift or live API richer than frozen fixture (OtherEngineInfo / raw field set).",
    "investigation_link": "run_stdio_calls left GLOVEBOX_INVESTIGATIONS_FILE on fixture sample; not full live zip.",
    "investigation_by_vehicle": "Same investigations fixture file via run_stdio_calls defaults.",
    "profile_partial": "Complaints section unavailable live (HTTP 400); investigations from fixture file.",
    "profile_by_name": "Investigations rows from fixture file in live run.",
}


def classify_failure(row: dict) -> str:
    cid = row["id"]
    if cid in failure_notes:
        return failure_notes[cid]
    if not row["tool_selection"]:
        return "Model mistake: wrong tool or extra tool call."
    if not row["argument_correctness"]:
        return "Model mistake: wrong tool arguments."
    if not row["field_accuracy"]:
        return "Model mistake or live/fixture mismatch on must_include strings in tool JSON."
    if not row["faithfulness"]:
        return "Model mistake: answer leaked must_not phrase or invented campaign number."
    return "Unknown"


all_pass = sum(
    1
    for row in rows
    if all(row[k] for k in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness"))
)

report_lines = [
    "# Blind eval: Composer 2.5",
    "",
    f"Overall: {all_pass}/40 cases fully passed (tool, arguments, field accuracy, faithfulness).",
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
for cat, stats in category_breakdown.items():
    report_lines.append(f"- {cat}: {stats['passed']}/{stats['total']}")
report_lines.extend(["", "## Failures", ""])
if not summary["failures"]:
    report_lines.append("None.")
else:
    for fail in summary["failures"]:
        row = next(r for r in rows if r["id"] == fail["id"])
        report_lines.append(f"### {fail['id']}")
        report_lines.append(
            f"tool={fail['tool_selection']} args={fail['argument_correctness']} "
            f"fields={fail['field_accuracy']} faith={fail['faithfulness']}"
        )
        if fail.get("missing_fields"):
            report_lines.append(f"missing_fields: {fail['missing_fields']}")
        if fail.get("leaked_phrases"):
            report_lines.append(f"leaked_phrases: {fail['leaked_phrases']}")
        if fail.get("invented_campaigns"):
            report_lines.append(f"invented_campaigns: {fail['invented_campaigns']}")
        report_lines.append(f"Cause: {classify_failure(row)}")
        report_lines.append("")

report_lines.extend(
    [
        "## Notes",
        "",
        "- Live NHTSA complaints and some recall spellings return HTTP 400 with an empty JSON body. "
        "Glovebox treats that as upstream_unavailable rather than count 0.",
        "- scripts/run_stdio_calls.py forces GLOVEBOX_INVESTIGATIONS_FILE to tests/fixtures/investigations.txt "
        "even when GLOVEBOX_FIXTURES is cleared unless you also unset investigations.",
        "- Scoring uses frozen golden must_include strings from fixtures; live drift counts as failure even when the model quoted the live tool JSON faithfully.",
        "",
    ]
)
(RUN / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
print(f"scored {len(rows)} cases, full pass {all_pass}/40")