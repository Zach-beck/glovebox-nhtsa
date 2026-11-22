import json
import re
from pathlib import Path

import pytest

from glovebox_nhtsa.cache import MemoryCache, NullCache
from glovebox_nhtsa.report import render_vehicle_report_html
from glovebox_nhtsa.service import Service
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


def test_recalls_in_report_include_remedy_when_present(service):
    result = run(service.vehicle_report, "5UXWX7C5*BA", 2011)
    campaigns = result["sections"]["recalls"]["data"]["campaigns"]
    assert campaigns
    assert any("remedy" in item for item in campaigns) or "remedy" in json.dumps(campaigns)