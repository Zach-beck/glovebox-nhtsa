"""Tool behavior, independent of the MCP transport."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from glovebox_nhtsa.backend import (
    FixtureBackend,
    LiveBackend,
    OfflineBackend,
    UpstreamError,
    request_key,
)
from glovebox_nhtsa.cache import ResponseCache, build_response_cache
from glovebox_nhtsa.report import (
    coverage_limits_section,
    identity_ready,
    render_vehicle_report_html,
    section_shell,
    status_for_payload,
    utc_now_iso,
    write_report_file,
    REPORT_SCHEMA,
)
from glovebox_nhtsa.sources import source_url
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.investigations import InvestigationIndex
from glovebox_nhtsa.shaping import (
    SPEC_NOTE,
    REPAIR_NOTE,
    drive_matches,
    error_body,
    normalize_vin,
    shape_complaints,
    shape_decode,
    shape_model_list,
    shape_rating_detail,
    shape_rating_variants,
    shape_recalls,
)
from glovebox_nhtsa.text import INVALID_CALL_NOTE, SPELLING_NOTICE

TTL_DECODE = 7 * 24 * 3600
TTL_RECALLS = 6 * 3600
TTL_COMPLAINTS = 6 * 3600
TTL_RATINGS = 7 * 24 * 3600
TTL_MODELS = 7 * 24 * 3600
SCHEMA = "1"

def ratings_notice_for_report(
    payload: dict[str, Any],
    *,
    make: str | None,
    model: str | None,
    model_year: int | None,
) -> dict[str, Any]:
    if payload.get("count", 0) != 0 or payload.get("rating"):
        return payload
    notice = payload.get("notice")
    if notice and notice != SPELLING_NOTICE:
        return payload
    if make and model and model_year:
        text = (
            f"NHTSA has no NCAP safety rating on file for {int(model_year)} {make} {model}."
        )
    else:
        text = "NHTSA has no NCAP safety rating on file for this model year."
    updated = dict(payload)
    updated["notice"] = text
    return updated


def ratings_for_report_year(payload: dict[str, Any], expected_year: int | None) -> dict[str, Any]:
    """Drop NCAP detail when NHTSA's row year does not match the vehicle identity year."""
    if expected_year is None or payload.get("error"):
        return payload
    rating = payload.get("rating")
    if not isinstance(rating, dict):
        return payload
    raw_year = rating.get("model_year")
    if raw_year is None or str(raw_year).strip() == "":
        return payload
    try:
        got = int(raw_year)
    except (TypeError, ValueError):
        return payload
    if got == int(expected_year):
        return payload
    return {
        "count": 0,
        "rating": None,
        "notice": (
            f"NHTSA returned NCAP data for model year {got}, not {expected_year}. "
            "No rating is shown for the requested year."
        ),
    }


def _invalid_arguments(detail: str) -> dict[str, Any]:
    return error_body(
        "invalid_arguments",
        "glovebox",
        False,
        detail,
        answer_note=INVALID_CALL_NOTE,
    )


class Service:
    def __init__(
        self,
        backend: FixtureBackend | LiveBackend | OfflineBackend,
        cache: ResponseCache,
        investigations: InvestigationIndex,
    ) -> None:
        self.backend = backend
        self.cache = cache
        self.investigations = investigations

    async def aclose(self) -> None:
        closer = getattr(self.backend, "aclose", None)
        if closer is not None:
            await closer()

    async def _fetch_shaped(
        self,
        cache_name: str,
        cache_params: dict[str, Any],
        ttl: float,
        fetch_name: str,
        fetch_params: dict[str, Any],
        shape,
    ) -> dict[str, Any]:
        key = request_key(f"{SCHEMA}:{cache_name}", cache_params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            raw = await self.backend.fetch(fetch_name, fetch_params)
        except UpstreamError as exc:
            return exc.to_dict()
        shaped = shape(raw)
        if "error" not in shaped:
            self.cache.put(key, shaped, ttl)
        return shaped

    async def decode_vin(
        self,
        vin: str,
        model_year: int | None = None,
        include_raw_filled: bool = False,
    ) -> dict[str, Any]:
        normalized, problem = normalize_vin(vin)
        if problem or normalized is None:
            return problem or error_body("invalid_vin", "glovebox", False, "VIN is empty.")
        params: dict[str, Any] = {"vin": normalized}
        if model_year:
            params["model_year"] = int(model_year)
        cache_params = {**params, "raw": bool(include_raw_filled)}
        return await self._fetch_shaped(
            "decode",
            cache_params,
            TTL_DECODE,
            "decode_vin",
            params,
            lambda raw: shape_decode(raw, include_raw_filled=include_raw_filled),
        )

    async def get_recalls(
        self,
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        campaign_number: str | None = None,
        include_remedy: bool = False,
    ) -> dict[str, Any]:
        campaign = (campaign_number or "").strip().upper()
        if campaign and any((make, model, model_year)):
            return _invalid_arguments("Pass a campaign number or a make, model, and model year, not both.")
        if campaign:
            params = {"campaign_number": campaign}
            return await self._fetch_shaped(
                "recalls_campaign",
                {**params, "remedy": bool(include_remedy)},
                TTL_RECALLS,
                "recalls_by_campaign",
                params,
                lambda raw: shape_recalls(raw, include_remedy=include_remedy),
            )
        if not make or not model or not model_year:
            return _invalid_arguments("Provide make, model, and model year, or a campaign number.")
        params = {"make": make.strip().upper(), "model": model.strip().upper(), "model_year": int(model_year)}
        return await self._fetch_shaped(
            "recalls_vehicle",
            {**params, "remedy": bool(include_remedy)},
            TTL_RECALLS,
            "recalls_by_vehicle",
            params,
            lambda raw: shape_recalls(raw, include_remedy=include_remedy),
        )

    async def summarize_complaints(
        self,
        make: str,
        model: str,
        model_year: int,
        component: str | None = None,
    ) -> dict[str, Any]:
        if not make or not model or not model_year:
            return _invalid_arguments("Provide make, model, and model year.")
        params = {"make": make.strip().upper(), "model": model.strip().upper(), "model_year": int(model_year)}
        return await self._fetch_shaped(
            "complaints",
            {**params, "component": (component or "").strip().upper()},
            TTL_COMPLAINTS,
            "complaints_by_vehicle",
            params,
            lambda raw: shape_complaints(raw, component=component),
        )

    async def get_safety_ratings(
        self,
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        vehicle_id: int | str | None = None,
        drive_type: str | None = None,
    ) -> dict[str, Any]:
        if vehicle_id is not None and str(vehicle_id).strip() != "":
            if any((make, model, model_year)):
                return _invalid_arguments("Pass a vehicle id or a make, model, and model year, not both.")
            params = {"vehicle_id": str(vehicle_id).strip()}
            return await self._fetch_shaped(
                "ratings_vehicle",
                params,
                TTL_RATINGS,
                "ratings_vehicle",
                params,
                shape_rating_detail,
            )
        if not make or not model or not model_year:
            return _invalid_arguments("Provide make, model, and model year, or a vehicle id.")
        params = {"make": make.strip().upper(), "model": model.strip().upper(), "model_year": int(model_year)}
        listing = await self._fetch_shaped(
            "ratings_model",
            params,
            TTL_RATINGS,
            "ratings_model",
            params,
            shape_rating_variants,
        )
        if "error" in listing or listing.get("count", 0) != 1 and not drive_type:
            if listing.get("count", 0) > 1:
                listing["note"] = "More than one tested variant. Pass vehicle_id for a single rating."
            return listing
        variants = listing.get("variants") or []
        chosen = variants
        if drive_type and len(variants) > 1:
            matched = [
                item
                for item in variants
                if item.get("description") and drive_matches(drive_type, item["description"])
            ]
            if len(matched) == 1:
                chosen = matched
                listing["matched_drive"] = True
            else:
                listing["note"] = "Drive type did not select a single variant."
                return listing
        if len(chosen) == 1 and chosen[0].get("vehicle_id"):
            detail = await self.get_safety_ratings(vehicle_id=chosen[0]["vehicle_id"])
            aligned = ratings_for_report_year(detail, int(model_year))
            if aligned.get("rating"):
                listing["rating"] = aligned.get("rating")
                listing["rating_note"] = detail.get("note")
            elif aligned.get("notice"):
                listing["count"] = 0
                listing["variants"] = []
                listing["notice"] = aligned["notice"]
        return listing

    async def list_model_names(self, make: str, model_year: int) -> dict[str, Any]:
        if not make or not model_year:
            return _invalid_arguments("Provide make and model year.")
        params = {"make": make.strip().upper(), "model_year": int(model_year)}

        async def one(fetch_name: str, source: str) -> dict[str, Any]:
            try:
                raw = await self.backend.fetch(fetch_name, params)
            except UpstreamError as exc:
                body = exc.to_dict()
                body["source"] = source
                return body
            return shape_model_list(raw, source=source)

        vpic, products, ncap = await asyncio.gather(
            one("vpic_models", "vpic"),
            one("products_models", "recall_product_list"),
            one("ratings_make", "ncap"),
        )
        return {
            "make": params["make"],
            "model_year": params["model_year"],
            "lists": [vpic, products, ncap],
            "note": (
                "The recall product list is incomplete. An empty list is not proof a model has no campaigns. "
                + SPELLING_NOTICE
            ),
        }

    async def search_investigations(
        self,
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        component: str | None = None,
        query: str | None = None,
        nhtsa_id: str | None = None,
    ) -> dict[str, Any]:
        if not any((make, model, model_year, component, query, nhtsa_id)):
            return _invalid_arguments("Provide at least one investigation filter.")
        return await self.investigations.search(
            make=(make or "").strip(),
            model=(model or "").strip(),
            model_year=str(model_year) if model_year else "",
            component=(component or "").strip(),
            query=(query or "").strip(),
            nhtsa_id=(nhtsa_id or "").strip(),
            limit=20,
        )

    def _emit_vehicle_report(
        self,
        report: dict[str, Any],
        *,
        format: str,
        write_html_path: Path | None,
        report_dir: Path | None,
    ) -> dict[str, Any]:
        if format.lower() != "html":
            return report
        html_text = render_vehicle_report_html(report)
        output: dict[str, Any] = {
            "schema": REPORT_SCHEMA,
            "format": "html",
            "vin": report.get("vin"),
            "fetched_at": report.get("fetched_at"),
            "html": html_text,
        }
        if write_html_path is not None:
            write_html_path.parent.mkdir(parents=True, exist_ok=True)
            write_html_path.write_text(html_text, encoding="utf-8")
            output["file_path"] = str(write_html_path)
        elif report_dir is not None:
            path = write_report_file(report_dir, str(report.get("vin") or "report"), html_text)
            output["file_path"] = str(path)
        return output

    async def vehicle_report(
        self,
        vin: str,
        model_year: int | None = None,
        *,
        format: str = "json",
        write_html_path: Path | None = None,
        report_dir: Path | None = None,
    ) -> dict[str, Any]:
        normalized, problem = normalize_vin(vin)
        if problem or normalized is None:
            return problem or error_body("invalid_vin", "glovebox", False, "VIN is empty.")
        fetched_at = utc_now_iso()
        decode_params = {"vin": normalized}
        if model_year:
            decode_params["model_year"] = int(model_year)
        decoded = await self.decode_vin(normalized, model_year)
        decode_url = source_url("decode_vin", decode_params)
        if decoded.get("error") == "invalid_vin":
            skipped = {"error": "skipped", "detail": "Decode did not succeed."}
            sections = {
                "decode": section_shell("unavailable", decode_url, decoded),
                "recalls": section_shell("not_applicable", None, skipped),
                "complaints": section_shell("not_applicable", None, dict(skipped)),
                "ratings": section_shell("not_applicable", None, dict(skipped)),
                "investigations": section_shell("not_applicable", None, dict(skipped)),
                "coverage_limits": coverage_limits_section(),
            }
            report = {
                "schema": REPORT_SCHEMA,
                "vin": normalized,
                "fetched_at": fetched_at,
                "sections": sections,
                "notes": [SPEC_NOTE, REPAIR_NOTE],
            }
            return self._emit_vehicle_report(
                report,
                format=format,
                write_html_path=write_html_path,
                report_dir=report_dir,
            )
        applicable = identity_ready(decoded.get("specs") or {}, decoded.get("identity") or {})
        make = (decoded.get("specs") or {}).get("make")
        model = (decoded.get("specs") or {}).get("model")
        year_raw = (decoded.get("specs") or {}).get("model_year")
        model_year_int: int | None = None
        if model_year is not None:
            model_year_int = int(model_year)
        elif year_raw and str(year_raw).isdigit():
            model_year_int = int(year_raw)
        drive = (decoded.get("specs") or {}).get("drive")
        vehicle_params = (
            {"make": make, "model": model, "model_year": model_year_int}
            if make and model and model_year_int
            else {}
        )
        skipped = {"error": "skipped", "detail": "Need make, model, and model year from decode."}
        if applicable and vehicle_params:
            recalls, complaints, ratings, investigations = await asyncio.gather(
                self._section(lambda: self.get_recalls(make, model, model_year_int, include_remedy=True)),
                self._section(lambda: self.summarize_complaints(make or "", model or "", model_year_int or 0)),
                self._section(lambda: self.get_safety_ratings(make, model, model_year_int, drive_type=drive)),
                self._section(lambda: self.search_investigations(make, model, model_year_int)),
            )
            ratings = ratings_for_report_year(ratings, model_year_int)
            ratings = ratings_notice_for_report(
                ratings,
                make=make,
                model=model,
                model_year=model_year_int,
            )
        else:
            recalls = complaints = ratings = investigations = dict(skipped)
        recall_params = vehicle_params
        complaint_params = vehicle_params
        ratings_params = dict(vehicle_params)
        investigation_params = dict(vehicle_params)
        sections = {
            "decode": section_shell(
                status_for_payload(decoded, applicable=True),
                decode_url,
                decoded,
            ),
            "recalls": section_shell(
                status_for_payload(recalls, applicable=applicable),
                source_url("recalls_by_vehicle", recall_params) if recall_params else None,
                recalls,
            ),
            "complaints": section_shell(
                status_for_payload(complaints, applicable=applicable),
                source_url("complaints_by_vehicle", complaint_params) if complaint_params else None,
                complaints,
            ),
            "ratings": section_shell(
                status_for_payload(ratings, applicable=applicable),
                source_url("ratings_model", ratings_params) if ratings_params else None,
                ratings,
            ),
            "investigations": section_shell(
                status_for_payload(investigations, applicable=applicable),
                source_url("investigations_index", investigation_params) if investigation_params else None,
                investigations,
            ),
            "coverage_limits": coverage_limits_section(),
        }
        report: dict[str, Any] = {
            "schema": REPORT_SCHEMA,
            "vin": normalized,
            "fetched_at": fetched_at,
            "sections": sections,
            "notes": [SPEC_NOTE, REPAIR_NOTE],
        }
        return self._emit_vehicle_report(
            report,
            format=format,
            write_html_path=write_html_path,
            report_dir=report_dir,
        )

    async def render_vehicle_report_html(
        self,
        vin: str,
        model_year: int | None = None,
        *,
        report_dir: Path | None = None,
    ) -> dict[str, Any]:
        return await self.vehicle_report(vin, model_year, format="html", report_dir=report_dir)

    async def vehicle_profile(
        self,
        vin: str | None = None,
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
    ) -> dict[str, Any]:
        identity: dict[str, Any] | None = None
        specs: dict[str, Any] = {}
        status: dict[str, str] = {}
        if vin:
            decoded = await self.decode_vin(vin, model_year)
            if decoded.get("error") == "invalid_vin":
                return {
                    "section_status": {"identity": "unavailable"},
                    "identity": decoded,
                    "notes": [SPEC_NOTE, REPAIR_NOTE],
                }
            if "error" in decoded and "identity" not in decoded:
                status["identity"] = "unavailable"
                identity = decoded
            else:
                identity = decoded.get("identity", {})
                specs = decoded.get("specs", {})
                status["identity"] = "ok" if specs.get("make") or identity.get("make") else "empty"
                status["specs"] = "ok" if specs else "empty"
                make = make or specs.get("make")
                model = model or specs.get("model")
                if model_year is None and specs.get("model_year", "").isdigit():
                    model_year = int(specs["model_year"])
        elif make and model and model_year:
            status["identity"] = "ok"
            status["specs"] = "empty"
            identity = {"make": make.strip().upper(), "model": model.strip().upper(), "model_year": int(model_year)}
        else:
            return _invalid_arguments("Provide a VIN, or make, model, and model year.")

        drive = specs.get("drive")
        recalls, complaints, ratings, investigations = await asyncio.gather(
            self._section(lambda: self.get_recalls(make, model, model_year)),
            self._section(lambda: self.summarize_complaints(make or "", model or "", model_year or 0)),
            self._section(lambda: self.get_safety_ratings(make, model, model_year, drive_type=drive)),
            self._section(lambda: self.search_investigations(make, model, model_year)),
        )
        status["recalls"] = _status_of(recalls)
        status["complaints"] = _status_of(complaints)
        status["ratings"] = _status_of(ratings)
        status["investigations"] = _status_of(investigations)
        return {
            "identity": identity,
            "specs": specs,
            "recalls": recalls,
            "complaints": complaints,
            "ratings": ratings,
            "investigations": investigations,
            "section_status": status,
            "notes": [SPEC_NOTE, REPAIR_NOTE],
        }

    async def _section(self, factory) -> dict[str, Any]:
        try:
            return await factory()
        except UpstreamError as exc:
            return exc.to_dict()


def _status_of(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return "unavailable"
    count = payload.get("count")
    if count == 0:
        return "empty"
    return "ok"


def build_service(settings: Settings, *, cache_dir: Path | None = None) -> Service:
    directory = cache_dir if cache_dir is not None else settings.cache_dir
    cache = build_response_cache(directory, settings.resolved_cache_dir())
    if settings.fixtures_dir is not None:
        backend: FixtureBackend | LiveBackend | OfflineBackend = FixtureBackend(settings.fixtures_dir)
    elif settings.offline:
        backend = OfflineBackend()
    else:
        backend = LiveBackend(
            gap_seconds=settings.request_gap_seconds,
            timeout=settings.request_timeout_seconds,
        )
    investigations = InvestigationIndex(
        settings.investigations_file,
        settings.resolved_data_dir(),
        offline=settings.offline or settings.fixtures_dir is not None,
    )
    return Service(backend, cache, investigations)
