import json

from glovebox_nhtsa.shaping import (
    estimate_tokens,
    parse_nhtsa_date,
    shape_complaints,
    shape_decode,
    shape_recalls,
)


def test_day_first_unambiguous_date():
    parsed = parse_nhtsa_date("30/10/2017")
    assert parsed is not None
    assert parsed["iso"] == "2017-10-30"
    assert "note" not in parsed


def test_ambiguous_slash_date_stays_day_first_and_is_marked():
    parsed = parse_nhtsa_date("06/03/2019")
    assert parsed is not None
    assert parsed["iso"] == "2019-03-06"
    assert "note" in parsed


def test_not_applicable_and_empty_fields_drop():
    shaped = shape_decode(
        {
            "Results": [
                {
                    "ErrorCode": "0",
                    "ErrorText": "0 - VIN decoded clean.",
                    "Make": "BMW",
                    "Model": "X3",
                    "ModelYear": "2011",
                    "ABS": "",
                    "BusType": "Not Applicable",
                    "TrailerType": " not applicable ",
                }
            ]
        }
    )
    assert shaped["specs"]["make"] == "BMW"
    assert "bus_type" not in shaped["specs"]
    blob = json.dumps(shaped)
    assert "Not Applicable" not in blob
    assert "spec_note" in shaped["identity"]["spec_note"] or "no value" in shaped["identity"]["spec_note"]


def test_complaint_shape_drops_narrative_and_vin():
    raw = json.loads(( __import__("pathlib").Path("tests/fixtures/complaints_rdx.json")).read_text())
    shaped = shape_complaints(raw["body"])
    blob = json.dumps(shaped)
    assert "summary" not in shaped
    assert "vin" not in blob.lower() or "partial" in blob.lower()
    assert "REDACTEDVIN" not in blob
    assert "Do not return this narrative" not in blob
    assert shaped["count"] == 1
    assert shaped["fire_reports"] == 1


def test_recall_count_zero_is_a_spelling_notice():
    shaped = shape_recalls({"results": []})
    assert shaped["count"] == 0
    assert "not proof" in shaped["notice"]
    assert estimate_tokens(shaped) < 400
