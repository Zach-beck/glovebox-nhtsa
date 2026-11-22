"""Aggregate vehicle_report JSON and self-contained HTML."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from glovebox_nhtsa.report_html import render_vehicle_report_html
from glovebox_nhtsa.shaping import error_body, normalize_vin
from glovebox_nhtsa.sources import COVERAGE_RESOURCE
from glovebox_nhtsa.text import COVERAGE_LIMITS, INVALID_CALL_NOTE, REPAIR_NOTE, SENTINEL_NOTE, SPEC_NOTE

REPORT_SCHEMA = "vehicle_report/1"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def section_shell(status: str, source_url: str | None, data: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"status": status, "data": data}
    if source_url:
        row["source_url"] = source_url
    return row


def identity_ready(specs: dict[str, Any], identity: dict[str, Any]) -> bool:
    make = specs.get("make") or identity.get("make")
    model = specs.get("model") or identity.get("model")
    year = specs.get("model_year") or identity.get("model_year")
    if not make or not model:
        return False
    try:
        int(str(year))
    except (TypeError, ValueError):
        return False
    return True


def status_for_payload(payload: dict[str, Any], *, applicable: bool) -> str:
    if not applicable:
        return "not_applicable"
    if payload.get("error"):
        if payload.get("error") == "skipped":
            return "not_applicable"
        return "unavailable"
    if "specs" in payload:
        specs = payload.get("specs") or {}
        if specs or payload.get("identity"):
            return "ok"
        return "empty"
    count = payload.get("count")
    if count == 0:
        return "empty"
    if count:
        return "ok"
    if payload.get("campaigns") or payload.get("components") or payload.get("variants"):
        return "ok" if (payload.get("campaigns") or payload.get("components") or payload.get("variants")) else "empty"
    if payload.get("rows") or payload.get("results") or payload.get("investigations"):
        rows = payload.get("rows") or payload.get("results") or payload.get("investigations") or []
        return "ok" if rows else "empty"
    if payload.get("rating") is not None:
        return "ok"
    return "empty"


def coverage_limits_section() -> dict[str, Any]:
    data = {
        "limits": COVERAGE_LIMITS,
        "invalid_call_note": INVALID_CALL_NOTE,
        "sentinel_note": SENTINEL_NOTE,
        "spec_note": SPEC_NOTE,
        "repair_note": REPAIR_NOTE,
        "disclaimer": (
            "Glovebox is not NHTSA. Empty recall or complaint lists are not proof that nothing was filed. "
            "Recall campaigns do not show whether a specific VIN was repaired."
        ),
    }
    return section_shell("ok", COVERAGE_RESOURCE, data)


__all__ = [
    "REPORT_SCHEMA",
    "coverage_limits_section",
    "identity_ready",
    "render_vehicle_report_html",
    "section_shell",
    "status_for_payload",
    "utc_now_iso",
    "write_report_file",
]


def profile_sections_to_report(
    profile: dict[str, Any],
    *,
    vin: str,
    fetched_at: str | None = None,
    source_urls: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Map vehicle_profile output into vehicle_report section shells (for fixtures/samples)."""
    urls = source_urls or {}
    status = profile.get("section_status") or {}

    def wrap(name: str, data: dict[str, Any], *, section_status: str | None = None) -> dict[str, Any]:
        st = section_status if section_status is not None else status.get(name, "ok")
        return section_shell(st, urls.get(name), data)

    decode_status = status.get("identity") or status.get("specs") or "ok"

    return {
        "schema": REPORT_SCHEMA,
        "vin": vin,
        "fetched_at": fetched_at or utc_now_iso(),
        "sections": {
            "decode": wrap(
                "identity",
                {"identity": profile.get("identity"), "specs": profile.get("specs")},
                section_status=decode_status,
            ),
            "recalls": wrap("recalls", profile.get("recalls") or {}),
            "complaints": wrap("complaints", profile.get("complaints") or {}),
            "ratings": wrap("ratings", profile.get("ratings") or {}),
            "investigations": wrap("investigations", profile.get("investigations") or {}),
            "coverage_limits": coverage_limits_section(),
        },
        "notes": profile.get("notes") or [SPEC_NOTE, REPAIR_NOTE],
    }


def write_report_file(directory: Path, vin: str, html_text: str) -> Path:
    safe = re.sub(r"[^A-Z0-9]+", "-", vin.upper()).strip("-") or "report"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe}-{stamp}.html"
    path.write_text(html_text, encoding="utf-8")
    return path

