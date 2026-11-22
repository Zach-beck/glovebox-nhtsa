"""Assemble blind run answers.jsonl from live MCP tool results."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = json.loads(Path("/tmp/glovebox-eval-prompts.json").read_text(encoding="utf-8"))
TOOLS = json.loads(Path("/tmp/glovebox-tool-results.json").read_text(encoding="utf-8"))
by_id = {row["id"]: row for row in TOOLS}

# Corrected first calls where the batch plan used wrong JSON types.
fix_ratings = json.loads(Path("/tmp/fix-ratings.json").read_text(encoding="utf-8"))[0]
by_id["ratings_not_rated"] = fix_ratings
fix_mixed = json.loads(Path("/tmp/fix-mixed-ratings.json").read_text(encoding="utf-8"))[0]
by_id["ratings_reject_mixed_arguments"] = fix_mixed

ANSWERS: dict[str, str] = {
    "decode_partial_bmw": (
        "NHTSA decodes VIN 5UXWX7C5*BA with model year 2011 as a 2011 BMW X3 (xDrive35i). "
        "Error code 6: Incomplete VIN. The decode still names the vehicle."
    ),
    "decode_partial_lower": (
        "The same decode with lowercase input normalizes to VIN 5UXWX7C5*BA, a 2011 BMW X3. "
        "Error code 6: Incomplete VIN."
    ),
    "decode_invalid_symbols": (
        "decode_vin rejected VIN! with invalid_vin. The tool says a VIN must be 1 to 17 letters, "
        "digits, or * characters. It did not decode a vehicle."
    ),
    "decode_invalid_empty": (
        "decode_vin rejected a blank VIN with invalid_vin. It did not decode a vehicle."
    ),
    "decode_check_digit": (
        "VIN 3GNDA13D76S000000 decodes as a Chevrolet HHR (2006 trim LS). "
        "Error code 1: Check Digit (9th position) does not calculate properly."
    ),
    "missing_means_unknown": (
        "For VIN 5UXWX7C5*BA, model year 2011, NHTSA lists airbags_side as "
        "1st Row (Driver and Passenger). Error code 6: Incomplete VIN. "
        "The tool's spec_note says a missing spec is not proof the vehicle lacks equipment."
    ),
    "not_applicable_dropped": (
        "Plant city is MUNICH. The shaped specs show BMW X3 2011 fields and do not include bus or trailer equipment."
    ),
    "recalls_hit_rdx": (
        "NHTSA lists two recall campaigns for the 2012 Acura RDX: 19V182000 (report received 2019-03-06) "
        "and 16V061000 (report received 2016-02-03). These are model-level campaigns, not per-VIN repair status."
    ),
    "recalls_hit_x3": (
        "NHTSA lists four campaigns for the 2011 BMW X3, including 17V683000 (report received 2017-10-30)."
    ),
    "recalls_campaign": (
        "Campaign 19V182000 is an Acura recall for Takata driver frontal air bag inflators. "
        "The tool returned many product rows under that campaign number; the 2012 RDX row is included."
    ),
    "recalls_spelling_miss": (
        "get_recalls returned upstream_unavailable: NHTSA returned HTTP 400 for recalls_by_vehicle. "
        "I cannot quote a zero count from the tool because the server did not return campaign rows."
    ),
    "recalls_not_repair_phrase": (
        "This server lists campaigns for a 2012 Acura RDX (19V182000 and 16V061000) but does not show "
        "whether recall work was completed on any specific vehicle."
    ),
    "complaints_x3_counts": (
        "summarize_complaints returned upstream_unavailable with HTTP 400 for complaints_by_vehicle. "
        "No complaint counts or components were returned for the 2011 BMW X3."
    ),
    "complaints_rdx_fire": (
        "For the 2012 Acura RDX, summarize_complaints reports count 15 and fire_reports 0. "
        "No fire-related complaints appear in the aggregate totals."
    ),
    "complaints_component_filter": (
        "The engine-filtered complaints call returned upstream_unavailable (HTTP 400). "
        "No filtered count is available from the tool."
    ),
    "complaints_redaction_keys": (
        "summarize_complaints returned upstream_unavailable for the 2011 BMW X3. "
        "The tool provides counts only and does not return owner VINs or narratives."
    ),
    "ratings_not_rated": (
        "Vehicle id 7520 is the 2013 Acura RDX SUV FWD. overall_rating is Not Rated. "
        "The tool note says Not Rated is not zero stars."
    ),
    "ratings_variant_list": (
        "NHTSA lists two 2013 Acura RDX NCAP variants: vehicle_id 7731 (SUV 4WD) and vehicle_id 7520 (SUV FWD)."
    ),
    "ratings_empty_spelling": (
        "get_safety_ratings for 2011 BMW X3 returned count 0 with an empty variant list. "
        "The notice says this is not proof the vehicle was not tested; another spelling may have records."
    ),
    "profile_partial": (
        "vehicle_profile for VIN 5UXWX7C5*BA, model year 2011, shows identity ok (incomplete VIN code 6), "
        "recalls ok (4 campaigns including 17V683000), complaints unavailable, ratings empty, investigations ok."
    ),
    "profile_by_name": (
        "Full profile for 2012 Acura RDX: recalls ok (19V182000, 16V061000), complaints ok (count 15, fire_reports 0), "
        "ratings ok (two variants), investigations include PE14001 linked to 19V182000."
    ),
    "model_names_gap": (
        "list_model_names for BMW 2011 returns separate spellings in vpic, recall_product_list, and ncap lists. "
        "The tool shows which strings each dataset uses."
    ),
    "investigation_link": (
        "Investigation EA15001 in the investigations file shows make BMW, model X3, model year 2011, "
        "component ENGINE, opened 20150101, campaign_number 17V683000."
    ),
    "investigation_by_vehicle": (
        "search_investigations for 2012 Acura RDX returns PE14001 (AIR BAGS, opened 20160101, closed 20170101) "
        "with campaign_number 19V182000."
    ),
    "out_of_scope_title": (
        "Glovebox does not provide title history or clean-title status. I did not call a tool."
    ),
    "out_of_scope_fuel": (
        "Fuel economy is not in this NHTSA MCP server. I did not call a tool."
    ),
    "out_of_scope_repair": (
        "The server cannot confirm whether a dealer completed recall repairs on a specific car. I did not call a tool."
    ),
    "recalls_both_live_campaigns": (
        "2012 Acura RDX campaigns: 19V182000 (report_received iso 2019-03-06) and 16V061000 (2016-02-03)."
    ),
    "recalls_do_not_invent_park_outside": (
        "Both 2012 Acura RDX recall rows returned park_outside false. No park-outside advisory is set on those campaigns."
    ),
    "recalls_ambiguous_day_first_date": (
        "Campaign 19V182000 report_received raw 06/03/2019 becomes iso 2019-03-06. "
        "The report_received note says both day and month are 12 or less, so a US month/day reading would differ."
    ),
    "recalls_reject_mixed_arguments": (
        "get_recalls returned invalid_arguments: pass a campaign number or make, model, and model year, not both."
    ),
    "recalls_reject_incomplete_arguments": (
        "get_recalls returned invalid_arguments when only make ACURA was provided."
    ),
    "decode_strips_internal_spaces": (
        "VIN with internal spaces normalizes to 5UXWX7C5*BA, 2011 BMW X3. Error code 6: Incomplete VIN."
    ),
    "decode_rejects_overlong_vin": (
        "An 18-character VIN was rejected as invalid_vin. The tool did not decode a vehicle."
    ),
    "decode_abc_multiple_error_codes": (
        "VIN ABC returns error_code 6,7,11 (incomplete VIN, unregistered manufacturer, incorrect model year) "
        "and empty specs. It did not decode a recognizable vehicle."
    ),
    "decode_raw_filled_drops_sentinels": (
        "With include_raw_filled, plant city remains MUNICH and other_filled_fields include OtherRestraintSystemInfo. "
        "Bus and trailer Not Applicable fields are not present in the shaped output."
    ),
    "complaints_unknown_component_is_zero": (
        "Brake-filtered complaints returned upstream_unavailable (HTTP 400). The tool did not return a numeric count."
    ),
    "ratings_reject_mixed_arguments": (
        "get_safety_ratings returned invalid_arguments: pass a vehicle id or make, model, and model year, not both."
    ),
    "profile_requires_an_identity": (
        "vehicle_profile returned invalid_arguments: provide a VIN or make, model, and model year."
    ),
    "investigations_require_a_filter": (
        "search_investigations returned invalid_arguments: provide at least one investigation filter."
    ),
}

prompt_by_id = {p["id"]: p for p in PROMPTS}
lines = []
for case_id in [p["id"] for p in PROMPTS]:
    entry = {
        "id": case_id,
        "question": prompt_by_id[case_id]["question"],
        "model": "Composer 2.5 (blind cloud agent eval)",
        "data_source": "live_nhtsa",
        "blinding": "blinded; only id and question read before answering",
        "tool_calls": by_id[case_id]["tool_calls"],
        "answer": ANSWERS[case_id],
    }
    lines.append(json.dumps(entry, ensure_ascii=False))

out = Path(__file__).parent / "answers.jsonl"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(lines)} lines to {out}")