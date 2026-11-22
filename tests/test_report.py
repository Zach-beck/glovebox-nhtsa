import json
import re
from pathlib import Path

import pytest

from glovebox_nhtsa.cache import MemoryCache, NullCache
from glovebox_nhtsa.report import render_vehicle_report_html
from glovebox_nhtsa.service import ratings_for_report_year
from tests.conftest import run


def test_vehicle_report_sections_and_sources(service):
    result = run(service.vehicle_report, "5UXWX7C5*BA", 2011)
    assert result["schema"] == "vehicle_report/1"
    assert result["fetched_at"].endswith("Z")
    sections = result["sections"]
    assert sections["decode"]["status"] == "ok"
    assert sections["recalls"]["status"] == "ok"
    assert "17V683000" in json.dumps(sections["recalls"]["data"])
    assert sections["complaints"]["status"] == "ok"
    assert sections["ratings"]["status"] == "empty"
    assert sections["recalls"]["source_url"].startswith("https://api.nhtsa.gov/")
    assert sections["decode"]["source_url"].startswith("https://vpic.nhtsa.dot.gov/")
    assert "specific VIN was repaired" in json.dumps(sections["coverage_limits"]["data"])
    blob = json.dumps(result)
    assert "person@example.com" not in blob
    assert "repairs are complete" not in blob


def test_vehicle_report_html_escapes_xss(service):
    result = run(service.vehicle_report, "5UXWX7C5*BA", 2011)
    malicious = "<script>alert(1)</script>"
    result["sections"]["recalls"]["data"]["campaigns"][0]["summary"] = malicious
    html_text = render_vehicle_report_html(result)
    assert malicious not in html_text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_text


def test_report_html_empty_ratings_one_ncap_notice_and_no_data_tile(service):
    profile = run(service.vehicle_profile, None, "ACURA", "RDX", 2012)
    from glovebox_nhtsa.report import profile_sections_to_report, render_vehicle_report_html

    report = profile_sections_to_report(
        profile,
        vin="SAMPLE-2012-ACURA-RDX",
        source_urls={"recalls": "https://example.test/recalls"},
    )
    report["sections"]["ratings"]["status"] = "empty"
    html_text = render_vehicle_report_html(report)
    assert html_text.count("This spelling returned no rows") == 0
    assert html_text.count("NHTSA has no NCAP safety rating on file") == 1
    assert "No data" in html_text
    assert html_text.count("These are campaigns filed against the model string") == 1


def test_vehicle_report_html_omits_redundant_rating_identity_rows(service):
    result = run(service.get_safety_ratings, vehicle_id=7520)
    report = {
        "vin": "TEST",
        "fetched_at": "2026-01-01T00:00:00Z",
        "sections": {
            "ratings": {"status": "ok", "data": result},
            "decode": {"status": "ok", "data": {}},
            "recalls": {"status": "empty", "data": {}},
            "complaints": {"status": "empty", "data": {}},
            "investigations": {"status": "empty", "data": {}},
            "coverage_limits": {"status": "ok", "data": {"limits": {}, "disclaimer": "x", "repair_note": "y"}},
        },
    }
    html_text = render_vehicle_report_html(report)
    assert "rating-meta" in html_text
    assert "Vehicle Id" not in html_text
    assert "NHTSA vehicle id 7520" in html_text


def test_vehicle_report_html_is_self_contained(service):
    html_text = run(service.vehicle_report, "5UXWX7C5*BA", 2011, format="html")["html"]
    lower = html_text.lower()
    assert "<link " not in lower
    assert re.search(r"<script[^>]+src=", lower) is None
    assert "@import url(" not in lower
    assert re.search(r"url\s*\(\s*['\"]https?://", lower) is None
    assert 'class="hero-title"' in html_text
    assert 'class="report-nav"' in html_text


def test_vehicle_report_html_writes_path(service, tmp_path: Path):
    target = tmp_path / "out.html"
    payload = run(
        service.vehicle_report,
        "5UXWX7C5*BA",
        2011,
        format="html",
        write_html_path=target,
    )
    assert payload["format"] == "html"
    assert target.is_file()
    assert "<!DOCTYPE html>" in target.read_text(encoding="utf-8")


def test_cache_skips_error_payloads():
    cache = MemoryCache()
    cache.put("k", {"error": "upstream_unavailable", "detail": "nope"}, 60)
    assert cache.get("k") is None


def test_null_cache_is_inert():
    cache = NullCache()
    cache.put("k", {"count": 1}, 60)
    assert cache.get("k") is None


def test_cli_report_json(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GLOVEBOX_FIXTURES", str(Path("tests/fixtures").resolve()))
    monkeypatch.setenv("GLOVEBOX_INVESTIGATIONS_FILE", str(Path("tests/fixtures/investigations.txt").resolve()))
    monkeypatch.setenv("GLOVEBOX_OFFLINE", "1")
    monkeypatch.setenv("GLOVEBOX_CACHE", "off")
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "glovebox_nhtsa.cli", "report", "5UXWX7C5*BA", "--model-year", "2011", "--json"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["sections"]["decode"]["status"] == "ok"


def test_ratings_notice_for_report_replaces_spelling_notice():
    from glovebox_nhtsa.service import ratings_notice_for_report
    from glovebox_nhtsa.text import SPELLING_NOTICE

    out = ratings_notice_for_report(
        {"count": 0, "notice": SPELLING_NOTICE},
        make="ACURA",
        model="RDX",
        model_year=2012,
    )
    assert "NCAP" in out["notice"]
    assert "2012" in out["notice"]
    assert out["notice"] != SPELLING_NOTICE


def test_ratings_for_report_year_rejects_mismatched_ncap_row():
    payload = {
        "count": 1,
        "rating": {
            "model_year": 2013,
            "overall_rating": "Not Rated",
            "vehicle_id": "7520",
            "vehicle_description": "2013 Acura RDX SUV FWD",
        },
    }
    aligned = ratings_for_report_year(payload, 2012)
    assert aligned["count"] == 0
    assert aligned["rating"] is None
    assert "2013" in aligned["notice"]
    assert "2012" in aligned["notice"]


def test_vehicle_profile_rdx_2012_ratings_empty_not_wrong_year(service):
    result = run(service.vehicle_profile, None, "ACURA", "RDX", 2012)
    assert result["section_status"]["ratings"] == "empty"
    assert result["ratings"].get("count", 0) == 0
    assert "7520" not in json.dumps(result["ratings"])


def test_recalls_in_report_include_remedy_when_present(service):
    result = run(service.vehicle_report, "5UXWX7C5*BA", 2011)
    campaigns = result["sections"]["recalls"]["data"]["campaigns"]
    assert campaigns
    assert any("remedy" in item for item in campaigns) or "remedy" in json.dumps(campaigns)