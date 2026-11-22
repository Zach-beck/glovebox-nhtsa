"""Scripted traces. A canned caller, not a live model."""

import json

from tests.conftest import run
from tests.golden_cases import CASES


def _run(service, case: dict) -> str:
    if case["tool"] is None:
        return case["canned_answer"]
    method = getattr(service, case["tool"])
    result = run(method, **case["arguments"])
    text = json.dumps(result)
    canned = case.get("canned_answer")
    if canned:
        return text + "\n" + canned
    return text


def test_every_scripted_trace(service):
    failures = []
    for case in CASES:
        text = _run(service, case)
        for needle in case["must_include"]:
            if needle not in text:
                failures.append(f"{case['id']} missing {needle!r}")
        for needle in case["must_not_include"]:
            if needle in text:
                failures.append(f"{case['id']} unexpectedly contains {needle!r}")
    assert failures == []


def test_scripted_set_covers_the_planned_categories():
    present = {case["category"] for case in CASES}
    required = {
        "decode_partial",
        "decode_invalid",
        "decode_check_digit",
        "missing_means_unknown",
        "not_applicable_dropped",
        "recalls_hit",
        "recalls_spelling",
        "recalls_not_repair_status",
        "complaints_summary",
        "complaints_redaction",
        "ratings_not_rated",
        "ratings_variant",
        "profile_partial",
        "out_of_scope",
        "investigation_link",
    }
    assert required <= present
    assert len(CASES) >= 24
