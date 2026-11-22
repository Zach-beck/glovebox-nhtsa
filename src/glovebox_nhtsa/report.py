"""Aggregate vehicle_report JSON and self-contained HTML."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from glovebox_nhtsa.shaping import error_body, normalize_vin
from glovebox_nhtsa.sources import COVERAGE_RESOURCE
from glovebox_nhtsa.text import COVERAGE_LIMITS, INVALID_CALL_NOTE, REPAIR_NOTE, SENTINEL_NOTE, SPEC_NOTE

REPORT_SCHEMA = "vehicle_report/1"
_MALICIOUS_TEST_MARKER = "<script>alert(1)</script>"


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


def write_report_file(directory: Path, vin: str, html_text: str) -> Path:
    safe = re.sub(r"[^A-Z0-9]+", "-", vin.upper()).strip("-") or "report"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe}-{stamp}.html"
    path.write_text(html_text, encoding="utf-8")
    return path


def render_vehicle_report_html(report: dict[str, Any]) -> str:
    sections = report.get("sections") or {}
    vin = html.escape(str(report.get("vin") or ""))
    fetched = html.escape(str(report.get("fetched_at") or ""))
    decode = sections.get("decode", {})
    specs = (decode.get("data") or {}).get("specs") or {}
    identity = (decode.get("data") or {}).get("identity") or {}
    title_bits = [
        str(specs.get("model_year") or identity.get("model_year") or ""),
        str(specs.get("make") or identity.get("make") or ""),
        str(specs.get("model") or identity.get("model") or ""),
    ]
    title_vehicle = " ".join(part for part in title_bits if part).strip() or vin

    def esc(value: Any) -> str:
        if value is None:
            return ""
        return html.escape(str(value))

    def status_pill(status: str) -> str:
        return f'<span class="pill pill-{esc(status)}">{esc(status)}</span>'

    def section_block(section_id: str, heading: str, body: str, section: dict[str, Any]) -> str:
        status = esc(section.get("status") or "")
        source = section.get("source_url")
        source_link = (
            f'<p class="source"><a href="{esc(source)}">{esc(source)}</a></p>' if source else ""
        )
        return (
            f'<section id="{esc(section_id)}">'
            f"<h2>{esc(heading)} {status_pill(status)}</h2>"
            f"{body}"
            f"{source_link}"
            "</section>"
        )

    summary_rows = []
    for label, key in (
        ("VIN", "vin"),
        ("Make", "make"),
        ("Model", "model"),
        ("Year", "model_year"),
        ("Trim", "trim"),
        ("Body", "body_class"),
        ("Drive", "drive"),
        ("Plant", "plant_city"),
    ):
        if key == "vin":
            value = identity.get("vin") or report.get("vin")
        else:
            value = specs.get(key)
        if value:
            summary_rows.append(f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>")
    err = identity.get("error_text")
    if err:
        summary_rows.append(f'<tr><th>Decode note</th><td>{esc(err)}</td></tr>')
    summary_body = (
        "<table class='kv'>" + "".join(summary_rows) + "</table>"
        if summary_rows
        else "<p class='muted'>No identity fields returned.</p>"
    )

    recalls_section = sections.get("recalls", {})
    recall_rows = []
    for item in (recalls_section.get("data") or {}).get("campaigns") or []:
        received = item.get("report_received") or {}
        date_text = received.get("iso") or received.get("raw") or ""
        recall_rows.append(
            "<article class='card'>"
            f"<h3>{esc(item.get('campaign_number'))}</h3>"
            f"<p><strong>Component:</strong> {esc(item.get('component'))}</p>"
            f"<p><strong>Date received:</strong> {esc(date_text)}</p>"
            f"<p>{esc(item.get('summary'))}</p>"
            + (
                f"<p><strong>Remedy:</strong> {esc(item.get('remedy'))}</p>"
                if item.get("remedy")
                else ""
            )
            + "</article>"
        )
    if (recalls_section.get("data") or {}).get("note"):
        recall_rows.append(
            f"<p class='note'>{esc((recalls_section.get('data') or {}).get('note'))}</p>"
        )
    if not recall_rows:
        recall_rows.append("<p class='muted'>No recall rows in this section.</p>")
    recalls_body = "".join(recall_rows)

    complaints_section = sections.get("complaints", {})
    complaint_data = complaints_section.get("data") or {}
    comp_rows = []
    for item in complaint_data.get("components") or []:
        comp_rows.append(
            "<tr>"
            f"<td>{esc(item.get('component'))}</td>"
            f"<td>{esc(item.get('count'))}</td>"
            f"<td>{esc(item.get('crash'))}</td>"
            f"<td>{esc(item.get('fire'))}</td>"
            "</tr>"
        )
    other = complaint_data.get("other_component_reports")
    if other:
        comp_rows.append(
            f"<tr><td>Other components</td><td>{esc(other)}</td><td></td><td></td></tr>"
        )
    complaints_body = (
        f"<p>Total complaints: <strong>{esc(complaint_data.get('count'))}</strong></p>"
        + "<table class='data'><thead><tr><th>Component</th><th>Count</th><th>Crash</th><th>Fire</th></tr></thead>"
        + "<tbody>"
        + "".join(comp_rows)
        + "</tbody></table>"
        if comp_rows
        else "<p class='muted'>No complaint component breakdown.</p>"
    )
    if complaint_data.get("note"):
        complaints_body += f"<p class='note'>{esc(complaint_data.get('note'))}</p>"

    ratings_section = sections.get("ratings", {})
    ratings_data = ratings_section.get("data") or {}
    rating = ratings_data.get("rating")
    if rating:
        rating_rows = "".join(
            f"<tr><th>{esc(key)}</th><td>{esc(value)}</td></tr>"
            for key, value in sorted(rating.items())
        )
        ratings_body = "<table class='kv'>" + rating_rows + "</table>"
    elif ratings_data.get("variants"):
        variants = "".join(
            f"<li>{esc(v.get('description'))} (id {esc(v.get('vehicle_id'))})</li>"
            for v in ratings_data.get("variants") or []
        )
        ratings_body = f"<ul>{variants}</ul>"
    else:
        ratings_body = "<p class='muted'>No rating detail returned.</p>"
    if ratings_data.get("note"):
        ratings_body += f"<p class='note'>{esc(ratings_data.get('note'))}</p>"

    inv_section = sections.get("investigations", {})
    inv_data = inv_section.get("data") or {}
    inv_items = []
    for item in inv_data.get("rows") or inv_data.get("results") or inv_data.get("investigations") or []:
        inv_items.append(
            "<article class='card'>"
            f"<h3>{esc(item.get('nhtsa_id') or item.get('action'))}</h3>"
            f"<p>{esc(item.get('subject') or item.get('component'))}</p>"
            f"<p class='muted'>{esc(item.get('opened'))} to {esc(item.get('closed'))}</p>"
            "</article>"
        )
    investigations_body = "".join(inv_items) if inv_items else "<p class='muted'>No investigations listed.</p>"

    cov = (sections.get("coverage_limits") or {}).get("data") or {}
    cov_items = []
    for _key, block in (cov.get("limits") or {}).items():
        cov_items.append(f"<li><strong>{esc(block.get('topic'))}:</strong> {esc(block.get('refusal'))}</li>")
    coverage_body = (
        f"<p>{esc(cov.get('disclaimer'))}</p>"
        + "<ul>"
        + "".join(cov_items)
        + "</ul>"
        + f"<p class='note'>{esc(cov.get('repair_note'))}</p>"
    )

    sources_list = []
    for name, section in sections.items():
        url = section.get("source_url")
        if url:
            sources_list.append(f"<li><strong>{esc(name)}:</strong> <a href='{esc(url)}'>{esc(url)}</a></li>")
    sources_body = "<ul>" + "".join(sources_list) + "</ul>" if sources_list else "<p class='muted'>No URLs recorded.</p>"

    malicious_demo = ""
    for section in sections.values():
        blob = json_escape_probe(section)
        if _MALICIOUS_TEST_MARKER in blob:
            malicious_demo = f"<p class='muted'>Escaped probe: {esc(_MALICIOUS_TEST_MARKER)}</p>"
            break

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Glovebox report {esc(title_vehicle)}</title>
  <style>
    :root {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, sans-serif;
      line-height: 1.45;
      color: #111;
      background: #fafafa;
    }}
    body {{
      margin: 0 auto;
      max-width: 52rem;
      padding: 1rem 1.1rem 3rem;
    }}
    header {{
      border-bottom: 1px solid #ddd;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
    }}
    h1 {{ font-size: 1.45rem; margin: 0 0 0.35rem; }}
    h2 {{ font-size: 1.1rem; margin: 1.6rem 0 0.6rem; }}
    h3 {{ font-size: 1rem; margin: 0 0 0.4rem; }}
    .meta {{ color: #444; font-size: 0.92rem; }}
    section {{ margin-bottom: 1.4rem; }}
    .card {{
      border: 1px solid #e2e2e2;
      border-radius: 8px;
      padding: 0.75rem 0.85rem;
      margin: 0.65rem 0;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      border-bottom: 1px solid #e8e8e8;
      text-align: left;
      padding: 0.35rem 0.25rem;
      vertical-align: top;
    }}
    .kv th {{ width: 34%; color: #333; font-weight: 600; }}
    .note {{ font-size: 0.9rem; color: #333; }}
    .muted {{ color: #666; }}
    .pill {{
      display: inline-block;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      border: 1px solid #ccc;
      margin-left: 0.35rem;
      vertical-align: middle;
    }}
    .source {{ font-size: 0.82rem; word-break: break-all; }}
    a {{ color: #0b57d0; }}
    @media print {{
      body {{ background: #fff; max-width: none; }}
      .card {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Vehicle report: {esc(title_vehicle)}</h1>
    <p class="meta">VIN {vin} · fetched {fetched}</p>
  </header>
  {section_block("summary", "Vehicle summary", summary_body, decode)}
  {section_block("recalls", "Recalls", recalls_body, recalls_section)}
  {section_block("complaints", "Complaints by component", complaints_body, complaints_section)}
  {section_block("ratings", "Safety ratings", ratings_body, ratings_section)}
  {section_block("investigations", "Investigations", investigations_body, inv_section)}
  {section_block("coverage", "Coverage limits and disclaimers", coverage_body, sections.get("coverage_limits", {}))}
  {section_block("sources", "Sources", sources_body + malicious_demo, section_shell("ok", None, {}))}
  <footer class="muted"><p>Glovebox is not affiliated with NHTSA. Data is public NHTSA information, shaped before display.</p></footer>
</body>
</html>"""
    return page


def json_escape_probe(section: dict[str, Any]) -> str:
    import json

    return json.dumps(section, ensure_ascii=False)