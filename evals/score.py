"""Score a transcript against one golden case.

This is the deterministic half of an agent run. It does not call a model.
"""

from __future__ import annotations

import json
from typing import Any


def normalize_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Compare make and model without case. Drop empty and false defaults."""
    if not arguments:
        return {}
    normalized: dict[str, Any] = {}
    for key, value in arguments.items():
        if value is None or value is False or value == "":
            continue
        if isinstance(value, str):
            text = value.strip()
            if text == "":
                continue
            if key in {"make", "model", "campaign_number"}:
                normalized[key] = text.upper()
            elif key == "vin":
                normalized[key] = text.upper().replace(" ", "")
            elif key in {"component", "nhtsa_id", "query"}:
                normalized[key] = text.casefold()
            else:
                normalized[key] = text
        else:
            normalized[key] = value
    return normalized


def score_case(case: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    calls = transcript.get("tool_calls") or []
    answer = transcript.get("answer") or ""
    expected_tool = case.get("tool")
    first = calls[0] if calls else None
    actual_tool = first.get("name") if first else None

    tool_ok = actual_tool == expected_tool
    if expected_tool is None:
        arguments_ok = len(calls) == 0
    elif first is None:
        arguments_ok = False
    else:
        arguments_ok = normalize_arguments(first.get("arguments")) == normalize_arguments(case.get("arguments"))

    tool_blob = "\n".join(json.dumps(call.get("result"), ensure_ascii=False) for call in calls)
    must_include = case.get("must_include") or []
    must_not = case.get("must_not_include") or []
    field_source = tool_blob if expected_tool else answer
    missing_fields = [item for item in must_include if item not in field_source]
    leaked_in_tool = [item for item in must_not if item and expected_tool and item in tool_blob]
    field_ok = not missing_fields and not leaked_in_tool

    leaked = [item for item in must_not if item and item in answer]
    invented = _invented_campaigns(answer, tool_blob)
    faithfulness_ok = not leaked and not invented

    return {
        "id": case["id"],
        "tool_selection": tool_ok,
        "argument_correctness": arguments_ok,
        "field_accuracy": field_ok,
        "faithfulness": faithfulness_ok,
        "missing_fields": missing_fields,
        "leaked_in_tool": leaked_in_tool,
        "leaked_phrases": leaked,
        "invented_campaigns": invented,
    }


def _invented_campaigns(answer: str, tool_blob: str) -> list[str]:
    import re

    found = []
    for match in re.findall(r"\d{2}V\d{6}", answer, flags=re.IGNORECASE):
        token = match.upper()
        if token not in tool_blob.upper():
            found.append(token)
    return found


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows) or 1
    def rate(key: str) -> dict[str, Any]:
        passed = sum(1 for row in rows if row[key])
        return {"passed": passed, "total": len(rows), "rate": round(passed / total, 4)}

    return {
        "cases": len(rows),
        "tool_selection": rate("tool_selection"),
        "argument_correctness": rate("argument_correctness"),
        "field_accuracy": rate("field_accuracy"),
        "faithfulness": rate("faithfulness"),
        "failures": [
            {
                "id": row["id"],
                "tool_selection": row["tool_selection"],
                "argument_correctness": row["argument_correctness"],
                "field_accuracy": row["field_accuracy"],
                "faithfulness": row["faithfulness"],
                "missing_fields": row["missing_fields"],
                "leaked_in_tool": row["leaked_in_tool"],
                "leaked_phrases": row["leaked_phrases"],
                "invented_campaigns": row["invented_campaigns"],
            }
            for row in rows
            if not all(row[key] for key in ("tool_selection", "argument_correctness", "field_accuracy", "faithfulness"))
        ],
    }
