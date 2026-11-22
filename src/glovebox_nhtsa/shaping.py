"""Turn raw NHTSA payloads into small, quotable objects.

Token estimates use len(json) / 4. That is a budget check, not a tokenizer.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from typing import Any

from glovebox_nhtsa.text import COMPLAINT_NOTE, REPAIR_NOTE, SENTINEL_NOTE, SPEC_NOTE, SPELLING_NOTICE

_CORE_FIELDS = (
    ("Make", "make"),
    ("Model", "model"),
    ("ModelYear", "model_year"),
    ("Trim", "trim"),
    ("BodyClass", "body_class"),
    ("VehicleType", "vehicle_type"),
    ("Doors", "doors"),
    ("DriveType", "drive"),
    ("EngineCylinders", "engine_cylinders"),
    ("DisplacementL", "displacement_l"),
    ("FuelTypePrimary", "fuel"),
    ("PlantCountry", "plant_country"),
    ("PlantCity", "plant_city"),
    ("AirBagLocFront", "airbags_front"),
    ("AirBagLocCurtain", "airbags_curtain"),
    ("AirBagLocSide", "airbags_side"),
    ("ESC", "esc"),
    ("TPMS", "tpms"),
    ("TractionControl", "traction_control"),
)

_DATE_SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_DATE_COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_DATE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

BUDGETS = {
    "decode_vin": 600,
    "get_recalls": 1200,
    "summarize_complaints": 500,
    "get_safety_ratings": 400,
    "search_investigations": 1200,
    "list_model_names": 800,
    "vehicle_profile": 2000,
    "vehicle_report": 2600,
    "instructions_and_tools": 1500,
}


def estimate_tokens(payload: Any) -> int:
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=False)
    return max(1, math.ceil(len(text) / 4))


def blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped == "" or stripped.lower() == "not applicable"
    return False


def parse_nhtsa_date(value: Any) -> dict[str, str] | None:
    """Return an ISO date. Day/month/year is the recalls API shape we observed."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    note = None
    year = month = day = None
    if match := _DATE_ISO.match(text):
        year, month, day = (int(part) for part in match.groups())
    elif match := _DATE_COMPACT.match(text):
        year, month, day = (int(part) for part in match.groups())
    elif match := _DATE_SLASH.match(text):
        day, month, year = (int(part) for part in match.groups())
        if day <= 12 and month <= 12:
            note = (
                "The source writes day/month/year. "
                "Both numbers are 12 or less, so a US month/day reading would differ."
            )
    else:
        return {"raw": text, "note": "Date was not recognized and was left unchanged."}
    try:
        iso = date(year, month, day).isoformat()
    except ValueError:
        return {"raw": text, "note": "Date was not a real calendar day and was left unchanged."}
    parsed = {"iso": iso, "raw": text}
    if note:
        parsed["note"] = note
    return parsed


def _clip(value: Any, limit: int) -> str | None:
    if blank(value):
        return None
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("results", payload.get("Results", []))
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def error_body(code: str, source: str, retryable: bool, detail: str, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"error": code, "source": source, "retryable": retryable, "detail": detail}
    body.update(extra)
    return body


def component_matches(needle: str, haystack: str) -> bool:
    """Case-insensitive substring match with simple English singular/plural overlap."""
    n = needle.strip().lower()
    h = haystack.strip().lower()
    if not n:
        return True
    if n in h:
        return True
    forms = {n}
    if n.endswith("s") and len(n) > 1:
        forms.add(n[:-1])
    if n.endswith("es") and len(n) > 2:
        forms.add(n[:-2])
    for form in forms:
        if form and form in h:
            return True
    return False


def component_arguments_equivalent(expected: str, actual: str) -> bool:
    a = expected.strip().casefold()
    b = actual.strip().casefold()
    if a == b:
        return True
    return component_matches(expected, actual) or component_matches(actual, expected)


def normalize_vin(vin: str) -> tuple[str | None, dict[str, Any] | None]:
    cleaned = vin.strip().upper().replace(" ", "")
    if cleaned == "" or len(cleaned) > 17 or re.fullmatch(r"[A-Z0-9*]+", cleaned) is None:
        return None, error_body(
            "invalid_vin",
            "glovebox",
            False,
            "A VIN must be 1 to 17 letters, digits, or * characters.",
        )
    return cleaned, None


def shape_decode(payload: dict[str, Any], *, include_raw_filled: bool = False) -> dict[str, Any]:
    rows = _rows(payload)
    if not rows:
        return error_body("not_found", "vpic", False, "vPIC returned no decode row.")
    row = rows[0]
    identity: dict[str, Any] = {
        "vin": row.get("VIN") or None,
        "error_code": str(row.get("ErrorCode") or ""),
        "error_text": row.get("ErrorText") or "",
        "spec_note": SPEC_NOTE,
    }
    extra_error = row.get("AdditionalErrorText")
    if not blank(extra_error):
        identity["additional_error_text"] = str(extra_error).strip()
    specs: dict[str, Any] = {}
    for source, target in _CORE_FIELDS:
        value = row.get(source)
        if not blank(value):
            specs[target] = str(value).strip()
    result: dict[str, Any] = {"identity": identity, "specs": specs}
    if include_raw_filled:
        used = {source for source, _target in _CORE_FIELDS}
        used.update({"VIN", "ErrorCode", "ErrorText", "AdditionalErrorText"})
        other = {}
        for key, value in row.items():
            if key in used or blank(value):
                continue
            other[key] = value if not isinstance(value, str) else value.strip()
        result["other_filled_fields"] = other
        result["sentinel_note"] = SENTINEL_NOTE
    return result


def shape_recalls(payload: dict[str, Any], *, include_remedy: bool = False, limit: int = 15) -> dict[str, Any]:
    rows = _rows(payload)
    campaigns = []
    for row in rows[:limit]:
        item: dict[str, Any] = {
            "campaign_number": row.get("NHTSACampaignNumber"),
            "make": row.get("Make"),
            "model": row.get("Model"),
            "model_year": row.get("ModelYear"),
            "component": row.get("Component"),
            "manufacturer": row.get("Manufacturer"),
            "park_it": bool(row.get("parkIt")),
            "park_outside": bool(row.get("parkOutSide")),
            "over_the_air_update": bool(row.get("overTheAirUpdate")),
        }
        parsed = parse_nhtsa_date(row.get("ReportReceivedDate"))
        if parsed:
            item["report_received"] = parsed
        action = row.get("NHTSAActionNumber")
        if not blank(action):
            item["investigation_id"] = str(action).strip()
        summary = _clip(row.get("Summary"), 400)
        if summary:
            item["summary"] = summary
        if include_remedy:
            consequence = _clip(row.get("Consequence"), 400)
            remedy = _clip(row.get("Remedy"), 400)
            if consequence:
                item["consequence"] = consequence
            if remedy:
                item["remedy"] = remedy
        units = row.get("PotentialNumberofUnitsAffected")
        if not blank(units):
            item["potential_units"] = units
        campaigns.append(item)
    result: dict[str, Any] = {
        "count": len(rows),
        "returned": len(campaigns),
        "truncated": len(rows) > limit,
        "campaigns": campaigns,
        "note": REPAIR_NOTE,
    }
    if len(rows) == 0:
        result["notice"] = SPELLING_NOTICE
    return result


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "yes", "y", "1"}


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def shape_complaints(payload: dict[str, Any], *, component: str | None = None) -> dict[str, Any]:
    """Counts only. Narratives and the partial VIN field are dropped."""
    rows = _rows(payload)
    needle = component.strip() if component else ""
    if needle:
        rows = [row for row in rows if component_matches(needle, str(row.get("components") or ""))]
    crashes = fires = injuries = deaths = 0
    buckets: dict[str, dict[str, int]] = {}
    filed: list[str] = []
    for row in rows:
        crash = _truthy(row.get("crash"))
        fire = _truthy(row.get("fire"))
        injury = _as_int(row.get("numberOfInjuries"))
        death = _as_int(row.get("numberOfDeaths"))
        crashes += int(crash)
        fires += int(fire)
        injuries += injury
        deaths += death
        name = str(row.get("components") or "").strip() or "UNSPECIFIED"
        bucket = buckets.setdefault(name, {"count": 0, "crash": 0, "fire": 0, "injuries": 0, "deaths": 0})
        bucket["count"] += 1
        bucket["crash"] += int(crash)
        bucket["fire"] += int(fire)
        bucket["injuries"] += injury
        bucket["deaths"] += death
        parsed = parse_nhtsa_date(row.get("dateComplaintFiled"))
        if parsed and "iso" in parsed:
            filed.append(parsed["iso"])
    ranked = sorted(buckets.items(), key=lambda item: (-item[1]["count"], item[0]))
    top = [{"component": name, **stats} for name, stats in ranked[:8]]
    other_count = sum(stats["count"] for _name, stats in ranked[8:])
    result: dict[str, Any] = {
        "count": len(rows),
        "crash_reports": crashes,
        "fire_reports": fires,
        "injuries": injuries,
        "deaths": deaths,
        "components": top,
        "note": COMPLAINT_NOTE,
    }
    if other_count:
        result["other_component_reports"] = other_count
    if filed:
        result["filed_from"] = min(filed)
        result["filed_to"] = max(filed)
    if needle:
        result["component_filter"] = component
    return result


def shape_rating_variants(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(payload)
    variants = []
    for row in rows:
        description = row.get("VehicleDescription") or row.get("vehicleDescription")
        vehicle_id = row.get("VehicleId", row.get("vehicleId"))
        if blank(description) and blank(vehicle_id):
            continue
        variants.append(
            {
                "vehicle_id": None if blank(vehicle_id) else str(vehicle_id),
                "description": None if blank(description) else str(description).strip(),
            }
        )
    # A make-level response uses VehicleId 0 as a placeholder. Drop those.
    real = [item for item in variants if item["vehicle_id"] not in {None, "0"}]
    chosen = real or []
    result: dict[str, Any] = {"count": len(chosen), "variants": chosen}
    if len(chosen) == 0:
        result["notice"] = SPELLING_NOTICE
    return result


def shape_rating_detail(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(payload)
    if not rows:
        return {"count": 0, "notice": SPELLING_NOTICE, "rating": None}
    row = rows[0]
    keep = (
        "OverallRating",
        "OverallFrontCrashRating",
        "FrontCrashDriversideRating",
        "FrontCrashPassengersideRating",
        "OverallSideCrashRating",
        "SideCrashDriversideRating",
        "SideCrashPassengersideRating",
        "RolloverRating",
        "RolloverPossibility",
        "SidePoleCrashRating",
        "NHTSAElectronicStabilityControl",
        "NHTSAForwardCollisionWarning",
        "NHTSALaneDepartureWarning",
        "ComplaintsCount",
        "RecallsCount",
        "InvestigationCount",
        "VehicleDescription",
        "VehicleId",
        "Make",
        "Model",
        "ModelYear",
    )
    rating = {}
    for key in keep:
        if key not in row or blank(row.get(key)):
            continue
        rating[_snake(key)] = row.get(key)
    return {
        "count": 1,
        "rating": rating,
        "note": "Not Rated is a published value. It is not zero stars and it is not a safety judgment.",
    }


def _snake(name: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(name):
        previous = name[index - 1] if index else ""
        nxt = name[index + 1] if index + 1 < len(name) else ""
        if char.isupper() and index and chars and chars[-1] != "_":
            if not previous.isupper() or nxt.islower():
                chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def shape_model_list(payload: dict[str, Any], *, source: str, limit: int = 40) -> dict[str, Any]:
    rows = _rows(payload)
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        raw = row.get("Model_Name", row.get("model", row.get("Model")))
        if blank(raw):
            continue
        name = str(raw).strip()
        key = name.upper()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    names.sort()
    return {
        "source": source,
        "count": len(names),
        "returned": min(len(names), limit),
        "truncated": len(names) > limit,
        "models": names[:limit],
    }


def drive_matches(drive: str, description: str) -> bool:
    drive_text = drive.upper()
    desc = description.upper()
    if any(token in drive_text for token in ("AWD", "ALL-WHEEL", "4WD", "4X4")):
        return any(token in desc for token in ("AWD", "4WD", "4X4"))
    if any(token in drive_text for token in ("FWD", "FRONT-WHEEL", "4X2")):
        return any(token in desc for token in ("FWD", "2WD", "4X2"))
    return False


def component_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("components") or "") for row in rows)
