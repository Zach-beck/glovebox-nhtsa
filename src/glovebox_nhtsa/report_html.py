"""Self-contained HTML layout for vehicle_report JSON."""

from __future__ import annotations

import html
import re
from typing import Any

from glovebox_nhtsa.text import SPELLING_NOTICE

STAR_MAX = 5

_RATING_SKIP_ROWS = frozenset(
    {"make", "model", "model_year", "vehicle_id", "vehicle_description", "overall_rating"}
)


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _status_pill(status: str) -> str:
    label = _esc(status.replace("_", " "))
    return (
        f'<span class="status-pill status-{_esc(status)}" role="status">'
        f'<span class="visually-hidden">Section status: </span>{label}</span>'
    )


def _parse_star_value(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"", "not rated", "nr"}:
        return None
    if text.isdigit():
        n = int(text)
        return n if 1 <= n <= STAR_MAX else None
    return None


_STAR_PATH = (
    "M12 2l3.1 6.3 7 1-5.3 4.9 1.4 7.4L12 18.6 5.8 21.6l1.4-7.4L2 9.3l7-1z"
)


def _stars_svg(value: Any, *, label: str) -> str:
    rating = _parse_star_value(value)
    title = _esc(label)
    text_fallback = _esc(value if value is not None else "Not rated")
    icons = []
    for index in range(1, STAR_MAX + 1):
        filled = rating is not None and index <= rating
        if filled:
            icons.append(
                f'<svg class="star-icon" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">'
                f'<path fill="currentColor" d="{_STAR_PATH}"/></svg>'
            )
        else:
            icons.append(
                f'<svg class="star-icon" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">'
                f'<path fill="none" stroke="currentColor" stroke-width="1.5" d="{_STAR_PATH}"/></svg>'
            )
    return (
        f'<span class="star-rating" role="img" aria-label="{title}: {text_fallback}">'
        f'{"".join(icons)}'
        f'<span class="star-text">{text_fallback}</span></span>'
    )


def _stat_tile(label: str, value: str, *, hint: str = "") -> str:
    hint_attr = f' title="{_esc(hint)}"' if hint else ""
    return (
        f'<div class="stat-tile"{hint_attr}>'
        f'<span class="stat-label">{_esc(label)}</span>'
        f'<span class="stat-value tabular">{_esc(value)}</span>'
        f"</div>"
    )


def _collapsible(summary: str, body: str, *, open_default: bool = False) -> str:
    if not body:
        return ""
    open_attr = " open" if open_default else ""
    return (
        f"<details class=\"fold\"{open_attr}>"
        f"<summary>{_esc(summary)}</summary>"
        f"<div class=\"fold-body\">{body}</div>"
        "</details>"
    )


def _ratings_empty_message(
    ratings_data: dict[str, Any],
    *,
    year: Any,
    make: Any,
    model: Any,
) -> str:
    notice = ratings_data.get("notice")
    if notice and notice != SPELLING_NOTICE:
        return str(notice)
    if year and make and model:
        return f"NHTSA has no NCAP safety rating on file for {year} {make} {model}."
    return "NHTSA has no NCAP safety rating on file for this model year."


def _hero_overall_rating_label(
    ratings_section: dict[str, Any],
    ratings_data: dict[str, Any],
    rating_obj: dict[str, Any] | None,
) -> str:
    status = ratings_section.get("status") or ""
    if status in {"empty", "unavailable", "not_applicable"}:
        return "No data"
    if not rating_obj:
        if ratings_data.get("variants"):
            return "Variants listed"
        return "No data"
    overall = rating_obj.get("overall_rating")
    if overall is not None and str(overall).strip() != "":
        return str(overall)
    return "No data"


def _complaint_bars(components: list[dict[str, Any]], total: int) -> str:
    if not components or total <= 0:
        return "<p class=\"empty-note\">No complaint component breakdown.</p>"
    max_count = max(int(item.get("count") or 0) for item in components) or 1
    rows = []
    for item in components:
        count = int(item.get("count") or 0)
        pct = round(100 * count / max_count)
        name = _esc(item.get("component"))
        rows.append(
            f'<div class="bar-row">'
            f'<span class="bar-label" id="bar-{_esc(item.get("component", ""))[:12]}">{name}</span>'
            f'<div class="bar-track" role="presentation">'
            f'<div class="bar-fill" style="width:{pct}%" '
            f'aria-labelledby="bar-{_esc(item.get("component", ""))[:12]}"></div>'
            f"</div>"
            f'<span class="bar-value tabular">{count}</span>'
            f"</div>"
        )
    return f'<div class="bar-chart" aria-label="Complaints by component">{"".join(rows)}</div>'


_REPORT_CSS = """
:root {
  color-scheme: light dark;
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", "SF Mono", Menlo, Consolas, monospace;
  --bg: #f3f1ee;
  --bg-elevated: #faf9f7;
  --ink: #1a1917;
  --ink-muted: #5c5854;
  --ink-faint: #7a7570;
  --line: #d8d4ce;
  --line-soft: #e6e2dc;
  --accent: #4a5d52;
  --accent-soft: rgba(74, 93, 82, 0.12);
  --shadow: 0 1px 2px rgba(26, 25, 23, 0.06), 0 8px 24px rgba(26, 25, 23, 0.05);
  --radius: 12px;
  --radius-sm: 8px;
  --space-1: 0.35rem;
  --space-2: 0.65rem;
  --space-3: 1rem;
  --space-4: 1.5rem;
  --space-5: 2.25rem;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: 1.65rem;
  --text-2xl: clamp(1.55rem, 3vw, 2.05rem);
  --status-ok-bg: #e8efe9;
  --status-ok-fg: #2f4a3a;
  --status-empty-bg: #eceae7;
  --status-empty-fg: #5c5854;
  --status-unavailable-bg: #f2e8e6;
  --status-unavailable-fg: #6b3d38;
  --status-na-bg: #e6eaef;
  --status-na-fg: #3d4a56;
  --callout-bg: #ebe8e3;
  --star: #6b5e4a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121110;
    --bg-elevated: #1a1918;
    --ink: #eceae7;
    --ink-muted: #b5b0a8;
    --ink-faint: #8c8680;
    --line: #2e2c2a;
    --line-soft: #252322;
    --accent: #8fa89a;
    --accent-soft: rgba(143, 168, 154, 0.15);
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.35), 0 12px 32px rgba(0, 0, 0, 0.28);
    --status-ok-bg: #1e2e26;
    --status-ok-fg: #b8d4c4;
    --status-empty-bg: #252322;
    --status-empty-fg: #b5b0a8;
    --status-unavailable-bg: #352826;
    --status-unavailable-fg: #e8b4ae;
    --status-na-bg: #242a30;
    --status-na-fg: #a8b8c8;
    --callout-bg: #1e1d1c;
    --star: #c4b69a;
  }
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.55;
  color: var(--ink);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}
.tabular { font-variant-numeric: tabular-nums; }
.visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
.report-shell { max-width: 54rem; margin: 0 auto; padding: var(--space-3) var(--space-3) var(--space-5); }
.layout { display: block; }
@media (min-width: 960px) {
  .layout {
    display: grid;
    grid-template-columns: 11rem 1fr;
    gap: var(--space-4);
    align-items: start;
  }
  .report-nav {
    position: sticky;
    top: var(--space-3);
  }
}
.report-nav {
  display: none;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: var(--text-sm);
}
@media (min-width: 960px) {
  .report-nav { display: flex; }
}
.report-nav a {
  color: var(--ink-muted);
  text-decoration: none;
  padding: 0.35rem 0.5rem;
  border-radius: var(--radius-sm);
}
.report-nav a:hover, .report-nav a:focus-visible {
  color: var(--ink);
  background: var(--accent-soft);
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.hero {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}
.hero-eyebrow {
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
  margin: 0 0 var(--space-2);
}
.hero-title {
  font-size: var(--text-2xl);
  font-weight: 650;
  letter-spacing: -0.02em;
  margin: 0 0 var(--space-1);
  line-height: 1.15;
}
.hero-trim {
  font-size: var(--text-lg);
  color: var(--ink-muted);
  margin: 0 0 var(--space-3);
  font-weight: 500;
}
.vin-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.vin-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  padding: 0.4rem 0.65rem;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  letter-spacing: 0.04em;
}
.copy-vin {
  font: inherit;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.45rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--ink-muted);
  cursor: pointer;
}
.copy-vin:hover, .copy-vin:focus-visible {
  border-color: var(--accent);
  color: var(--ink);
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.meta-line {
  font-size: var(--text-sm);
  color: var(--ink-faint);
  margin: 0 0 var(--space-3);
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}
@media (min-width: 640px) {
  .stat-grid { grid-template-columns: repeat(4, 1fr); }
}
.stat-tile {
  background: var(--bg);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-2);
}
.stat-label {
  display: block;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
  margin-bottom: 0.25rem;
}
.stat-value {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--ink);
}
.report-section {
  margin-bottom: var(--space-5);
  scroll-margin-top: var(--space-3);
}
.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--line-soft);
}
.report-section.is-empty .section-body,
.report-section.is-unavailable .section-body {
  padding: var(--space-2);
  border: 1px dashed var(--line);
  border-radius: var(--radius-sm);
  background: var(--bg);
}
.section-head h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
  letter-spacing: -0.01em;
}
.status-pill {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--line);
}
.status-ok { background: var(--status-ok-bg); color: var(--status-ok-fg); border-color: rgba(47, 74, 58, 0.2); }
.status-empty { background: var(--status-empty-bg); color: var(--status-empty-fg); border-color: var(--line); }
.status-unavailable { background: var(--status-unavailable-bg); color: var(--status-unavailable-fg); border-color: rgba(107, 61, 56, 0.25); }
.status-not_applicable { background: var(--status-na-bg); color: var(--status-na-fg); border-color: var(--line); }
.def-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: var(--space-2);
}
.def-item {
  background: var(--bg-elevated);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
}
.def-item dt {
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
  margin: 0 0 0.2rem;
}
.def-item dd {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 500;
}
.card-stack { display: flex; flex-direction: column; gap: var(--space-2); }
.recall-card {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-3);
}
.recall-card h3 {
  margin: 0 0 var(--space-1);
  font-size: var(--text-base);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}
.recall-meta {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin: 0 0 var(--space-2);
}
.recall-meta span + span::before { content: " · "; }
.fold {
  margin-top: var(--space-2);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  padding: 0 var(--space-2);
  background: var(--bg);
}
.fold summary {
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: 600;
  padding: var(--space-2) 0;
  color: var(--accent);
}
.fold-body {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  padding-bottom: var(--space-2);
  border-top: 1px solid var(--line-soft);
}
.bar-chart { display: flex; flex-direction: column; gap: var(--space-2); }
.bar-row {
  display: grid;
  grid-template-columns: minmax(5rem, 28%) 1fr auto;
  gap: var(--space-2);
  align-items: center;
  font-size: var(--text-sm);
}
.bar-label { color: var(--ink-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track {
  height: 0.55rem;
  background: var(--line-soft);
  border-radius: 999px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 999px;
  min-width: 2px;
}
.bar-value { font-weight: 600; min-width: 2ch; text-align: right; }
.ratings-block { background: var(--bg-elevated); border: 1px solid var(--line); border-radius: var(--radius); padding: var(--space-3); }
.star-rating { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--star); flex-wrap: wrap; }
.star-icon { display: inline-block; vertical-align: middle; }
.rating-hero { margin-bottom: var(--space-2); }
.star-text { font-size: var(--text-sm); color: var(--ink-muted); }
.rating-rows { margin-top: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); }
.rating-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--line-soft);
}
.rating-row:last-child { border-bottom: 0; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.data-table th, .data-table td {
  text-align: left;
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--line-soft);
}
.data-table th {
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
  background: var(--bg);
}
.data-table tr:last-child td { border-bottom: 0; }
.callout {
  background: var(--callout-bg);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius);
  padding: var(--space-3);
  font-size: var(--text-sm);
  color: var(--ink-muted);
}
.callout ul { margin: var(--space-2) 0 0; padding-left: 1.2rem; }
.callout li { margin-bottom: 0.35rem; }
.note { font-size: var(--text-sm); color: var(--ink-muted); margin-top: var(--space-2); }
.empty-note { font-size: var(--text-sm); color: var(--ink-muted); font-style: normal; margin: 0; }
.rating-meta { font-size: var(--text-xs); margin: var(--space-2) 0 0; line-height: 1.45; }
.section-notice { font-size: var(--text-sm); color: var(--ink-muted); margin-top: var(--space-2); }
.sources-footer {
  margin-top: var(--space-5);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
  font-size: var(--text-xs);
  color: var(--ink-faint);
}
.sources-footer ul { list-style: none; padding: 0; margin: var(--space-2) 0 0; }
.sources-footer li { margin-bottom: 0.35rem; word-break: break-all; }
.sources-footer a { color: var(--accent); }
.page-footer {
  margin-top: var(--space-4);
  font-size: var(--text-xs);
  color: var(--ink-faint);
  text-align: center;
}
.section-source {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  word-break: break-all;
}
.section-source a { color: var(--accent); }
@media print {
  body { background: #fff; color: #000; }
  .report-nav, .copy-vin { display: none !important; }
  .hero, .recall-card, .ratings-block, .callout { box-shadow: none; break-inside: avoid; }
  .report-section { break-inside: avoid-page; }
  a { color: #000; text-decoration: underline; }
}
"""


_COPY_VIN_JS = """
(function () {
  var btn = document.querySelector('.copy-vin');
  if (!btn || !navigator.clipboard) return;
  btn.addEventListener('click', function () {
    var vin = btn.getAttribute('data-vin') || '';
    navigator.clipboard.writeText(vin).then(function () {
      btn.textContent = 'Copied';
      setTimeout(function () { btn.textContent = 'Copy VIN'; }, 1800);
    });
  });
})();
""".strip()


def render_vehicle_report_html(report: dict[str, Any]) -> str:
    sections = report.get("sections") or {}
    raw_vin = str(report.get("vin") or "")
    vin = _esc(raw_vin)
    fetched = _esc(report.get("fetched_at") or "")
    decode = sections.get("decode", {})
    decode_data = decode.get("data") or {}
    specs = decode_data.get("specs") or {}
    identity = decode_data.get("identity") or {}

    year = specs.get("model_year") or identity.get("model_year") or ""
    make = specs.get("make") or identity.get("make") or ""
    model = specs.get("model") or identity.get("model") or ""
    trim = specs.get("trim") or ""
    title_vehicle = " ".join(part for part in (str(year), make, model) if part).strip() or raw_vin
    page_title = _esc(f"{title_vehicle} · Glovebox")

    recalls_section = sections.get("recalls", {})
    recalls_data = recalls_section.get("data") or {}
    campaigns = recalls_data.get("campaigns") or []

    complaints_section = sections.get("complaints", {})
    complaint_data = complaints_section.get("data") or {}
    complaint_total = int(complaint_data.get("count") or 0)

    ratings_section = sections.get("ratings", {})
    ratings_data = ratings_section.get("data") or {}
    rating_raw = ratings_data.get("rating")
    rating = rating_raw if isinstance(rating_raw, dict) else None
    overall = _hero_overall_rating_label(ratings_section, ratings_data, rating)

    inv_section = sections.get("investigations", {})
    inv_data = inv_section.get("data") or {}
    inv_rows = inv_data.get("rows") or []
    inv_count = int(inv_data.get("count") or len(inv_rows))

    stat_tiles = "".join(
        [
            _stat_tile("Recalls", str(len(campaigns) or recalls_data.get("count") or 0)),
            _stat_tile("Complaints", str(complaint_total)),
            _stat_tile("Overall rating", str(overall)),
            _stat_tile("Investigations", str(inv_count)),
        ]
    )

    spec_fields = (
        ("Year", "model_year"),
        ("Make", "make"),
        ("Model", "model"),
        ("Trim", "trim"),
        ("Body class", "body_class"),
        ("Drive", "drive"),
        ("Engine", "engine_cylinders"),
        ("Fuel", "fuel"),
        ("Plant", "plant_city"),
        ("Country", "plant_country"),
    )
    def_items = []
    vin_display = identity.get("vin") or raw_vin
    if vin_display:
        def_items.append(f'<div class="def-item"><dt>VIN</dt><dd>{_esc(vin_display)}</dd></div>')
    for label, key in spec_fields:
        val = specs.get(key)
        if val:
            def_items.append(f'<div class="def-item"><dt>{_esc(label)}</dt><dd>{_esc(val)}</dd></div>')
    err = identity.get("error_text")
    if err:
        def_items.append(f'<div class="def-item"><dt>Decode</dt><dd>{_esc(err)}</dd></div>')
    specs_body = (
        f'<div class="def-grid" role="list">{"".join(def_items)}</div>'
        if def_items
        else '<p class="empty-note">No specs returned.</p>'
    )

    recall_cards = []
    for item in campaigns:
        received = item.get("report_received") or {}
        date_text = received.get("iso") or received.get("raw") or ""
        summary = _esc(item.get("summary"))
        remedy = item.get("remedy")
        consequence = item.get("consequence")
        body_blocks = ""
        if summary:
            if len(str(item.get("summary") or "")) > 220:
                body_blocks += _collapsible("Summary", f"<p>{summary}</p>")
            else:
                body_blocks += f"<p class=\"note\">{summary}</p>"
        if remedy:
            body_blocks += _collapsible(
                "Remedy",
                f"<p>{_esc(remedy)}</p>",
            )
        if consequence and not remedy:
            body_blocks += _collapsible("Consequence", f"<p>{_esc(consequence)}</p>")
        recall_cards.append(
            f'<article class="recall-card">'
            f"<h3>{_esc(item.get('campaign_number'))}</h3>"
            f'<p class="recall-meta"><span>{_esc(item.get("component"))}</span>'
            f"<span>{_esc(date_text)}</span></p>"
            f"{body_blocks}"
            f"</article>"
        )
    if recalls_data.get("note"):
        recall_cards.append(f'<p class="note">{_esc(recalls_data.get("note"))}</p>')
    recalls_body = (
        f'<div class="card-stack">{"".join(recall_cards)}</div>'
        if recall_cards
        else '<p class="empty-note">No recall rows in this section.</p>'
    )

    complaints_body = _complaint_bars(complaint_data.get("components") or [], complaint_total)
    if complaint_data.get("other_component_reports"):
        complaints_body += (
            f'<p class="note tabular">Other components: '
            f'{_esc(complaint_data.get("other_component_reports"))} reports</p>'
        )
    if complaint_data.get("note"):
        complaints_body += f'<p class="note">{_esc(complaint_data.get("note"))}</p>'

    ratings_body = ""
    if rating:
        vid = rating.get("vehicle_id")
        desc = rating.get("vehicle_description")
        meta_bits = []
        if vid:
            meta_bits.append(f"NHTSA vehicle id {_esc(vid)}")
        if desc:
            meta_bits.append(_esc(desc))
        meta_line = (
            f'<p class="rating-meta muted">{" · ".join(meta_bits)}</p>' if meta_bits else ""
        )
        ratings_body = (
            f'<div class="ratings-block">'
            f'<div class="rating-hero">'
            f'{_stars_svg(rating.get("overall_rating"), label="Overall")}'
            f"</div>"
            f"{meta_line}"
        )
        rows = []
        for key in sorted(rating.keys()):
            if key in _RATING_SKIP_ROWS:
                continue
            value = rating.get(key)
            if "rating" in key.lower() or "rollover" in key.lower():
                rows.append(
                    f'<div class="rating-row"><span>{_esc(key.replace("_", " ").title())}</span>'
                    f"{_stars_svg(value, label=key)}</div>"
                )
            elif key not in _RATING_SKIP_ROWS:
                rows.append(
                    f'<div class="rating-row"><span>{_esc(key.replace("_", " ").title())}</span>'
                    f'<span class="tabular">{_esc(value)}</span></div>'
                )
        ratings_body += f'<div class="rating-rows">{"".join(rows)}</div></div>'
    elif ratings_data.get("variants"):
        variants = "".join(
            f"<li>{_esc(v.get('description'))} "
            f"<span class=\"tabular\">(id {_esc(v.get('vehicle_id'))})</span></li>"
            for v in ratings_data.get("variants") or []
        )
        ratings_body = f'<div class="section-body"><ul class="empty-note">{variants}</ul></div>'
    else:
        empty_msg = _ratings_empty_message(
            ratings_data,
            year=year,
            make=make,
            model=model,
        )
        ratings_body = f'<div class="section-body"><p class="empty-note">{_esc(empty_msg)}</p></div>'
    if ratings_data.get("note") and rating:
        ratings_body += f'<p class="note">{_esc(ratings_data.get("note"))}</p>'

    inv_table_rows = []
    for item in inv_rows:
        inv_table_rows.append(
            "<tr>"
            f"<th scope=\"row\">{_esc(item.get('nhtsa_id'))}</th>"
            f"<td>{_esc(item.get('component'))}</td>"
            f"<td>{_esc(item.get('subject'))}</td>"
            f"<td class=\"tabular\">{_esc(item.get('opened'))}</td>"
            f"<td class=\"tabular\">{_esc(item.get('closed'))}</td>"
            "</tr>"
        )
    investigations_body = (
        '<table class="data-table">'
        "<thead><tr><th>ID</th><th>Component</th><th>Subject</th><th>Opened</th><th>Closed</th></tr></thead>"
        f"<tbody>{''.join(inv_table_rows)}</tbody></table>"
        if inv_table_rows
        else '<p class="empty-note">No investigations listed.</p>'
    )

    cov = (sections.get("coverage_limits") or {}).get("data") or {}
    cov_items = []
    for block in (cov.get("limits") or {}).values():
        cov_items.append(f"<li><strong>{_esc(block.get('topic'))}:</strong> {_esc(block.get('refusal'))}</li>")
    coverage_body = f"<p>{_esc(cov.get('disclaimer'))}</p>" f"<ul>{''.join(cov_items)}</ul>"

    sources_list = []
    for name, section in sections.items():
        url = section.get("source_url")
        if url:
            sources_list.append(f"<li><span>{_esc(name)}</span> <a href=\"{_esc(url)}\">{_esc(url)}</a></li>")
    sources_body = f"<ul>{''.join(sources_list)}</ul>" if sources_list else "<p>No URLs recorded.</p>"

    def section_block(section_id: str, heading: str, body: str, section: dict[str, Any]) -> str:
        status = section.get("status") or ""
        state_class = ""
        if status in {"empty", "unavailable", "not_applicable"}:
            state_class = f" is-{status.replace('_', '-')}"
        source = section.get("source_url")
        source_html = (
            f'<p class="section-source"><a href="{_esc(source)}">{_esc(source)}</a></p>'
            if source
            else ""
        )
        return (
            f'<section class="report-section{state_class}" id="{_esc(section_id)}" aria-labelledby="{_esc(section_id)}-head">'
            f'<div class="section-head" id="{_esc(section_id)}-head">'
            f"<h2>{_esc(heading)}</h2>{_status_pill(status)}"
            f"</div>{body}{source_html}</section>"
        )

    nav = (
        '<nav class="report-nav" aria-label="Report sections">'
        '<a href="#specs">Specs</a>'
        '<a href="#recalls">Recalls</a>'
        '<a href="#complaints">Complaints</a>'
        '<a href="#ratings">Ratings</a>'
        '<a href="#investigations">Investigations</a>'
        '<a href="#coverage">Coverage</a>'
        '<a href="#sources">Sources</a>'
        "</nav>"
    )

    trim_line = f'<p class="hero-trim">{_esc(trim)}</p>' if trim else ""
    vin_attr = _esc(raw_vin)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>{_REPORT_CSS}</style>
</head>
<body>
  <div class="report-shell">
    <div class="layout">
      {nav}
      <main class="report-main">
        <header class="hero" id="top">
          <p class="hero-eyebrow">Glovebox vehicle report</p>
          <h1 class="hero-title">{_esc(title_vehicle)}</h1>
          {trim_line}
          <div class="vin-row">
            <code class="vin-code" id="report-vin">{vin}</code>
            <button type="button" class="copy-vin" data-vin="{vin_attr}" aria-label="Copy VIN to clipboard">Copy VIN</button>
          </div>
          <p class="meta-line">Fetched <time datetime="{fetched}">{fetched}</time></p>
          <div class="stat-grid" aria-label="At a glance">{stat_tiles}</div>
        </header>
        {section_block("specs", "Key specifications", specs_body, decode)}
        {section_block("recalls", "Recalls", recalls_body, recalls_section)}
        {section_block("complaints", "Complaints by component", complaints_body, complaints_section)}
        {section_block("ratings", "Safety ratings", ratings_body, ratings_section)}
        {section_block("investigations", "Investigations", investigations_body, inv_section)}
        {section_block("coverage", "Coverage limits and disclaimers", f'<aside class="callout">{coverage_body}</aside>', sections.get("coverage_limits", {}))}
        <footer class="sources-footer" id="sources">
          <h2 class="visually-hidden">Data sources</h2>
          {sources_body}
        </footer>
        <p class="page-footer">Glovebox is not affiliated with NHTSA. Public data, shaped before display.</p>
      </main>
    </div>
  </div>
  <script>{_COPY_VIN_JS}</script>
</body>
</html>"""