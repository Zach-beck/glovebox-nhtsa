"""Regenerate committed HTML samples from frozen fixtures."""

from __future__ import annotations

from pathlib import Path

import anyio

from glovebox_nhtsa.backend import build_url
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.report import profile_sections_to_report, render_vehicle_report_html
from glovebox_nhtsa.service import build_service, ratings_notice_for_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
INVESTIGATIONS = FIXTURES / "investigations.txt"


async def _samples(service) -> None:
    bmw = await service.vehicle_report("5UXWX7C5*BA", 2011, format="html")
    (ROOT / "docs" / "sample-report.html").write_text(bmw["html"], encoding="utf-8")

    profile = await service.vehicle_profile(make="ACURA", model="RDX", model_year=2012)
    recalls = await service.get_recalls("ACURA", "RDX", 2012, include_remedy=True)
    profile["recalls"] = recalls
    profile["section_status"]["recalls"] = "ok" if recalls.get("count") else "empty"
    profile["ratings"] = ratings_notice_for_report(
        await service.get_safety_ratings("ACURA", "RDX", 2012),
        make="ACURA",
        model="RDX",
        model_year=2012,
    )
    profile["section_status"]["ratings"] = "empty" if profile["ratings"].get("count", 0) == 0 else "ok"
    profile["identity"] = {
        "vin": "SAMPLE-2012-ACURA-RDX",
        "spec_note": profile.get("identity", {}).get("spec_note"),
    }
    profile["specs"] = {
        "make": "ACURA",
        "model": "RDX",
        "model_year": "2012",
        "trim": "SH-AWD",
    }
    urls = {
        "identity": None,
        "recalls": build_url("recalls_by_vehicle", {"make": "ACURA", "model": "RDX", "model_year": 2012}),
        "complaints": build_url(
            "complaints_by_vehicle",
            {"make": "ACURA", "model": "RDX", "model_year": 2012},
        ),
        "ratings": build_url(
            "ratings_model",
            {"make": "ACURA", "model": "RDX", "model_year": 2012},
        ),
        "investigations": "https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip",
    }
    report = profile_sections_to_report(profile, vin="SAMPLE-2012-ACURA-RDX", source_urls=urls)
    html_text = render_vehicle_report_html(report)
    (ROOT / "docs" / "sample-report-rdx.html").write_text(html_text, encoding="utf-8")
    await service.aclose()


def main() -> None:
    settings = Settings(
        fixtures_dir=FIXTURES,
        investigations_file=INVESTIGATIONS,
        offline=True,
        request_gap_seconds=0,
    )
    service = build_service(settings)
    async def runner() -> None:
        await _samples(service)

    anyio.run(runner)


if __name__ == "__main__":
    main()