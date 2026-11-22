"""MCP server wiring. Tools return shaped JSON and do not see raw complaint text."""

from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server import MCPServer

from glovebox_nhtsa import __version__
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import Service, build_service
from glovebox_nhtsa.text import INSTRUCTIONS, REPAIR_NOTE, SPEC_NOTE


def create_server(settings: Settings | None = None) -> MCPServer:
    settings = settings or Settings.from_env()
    service = build_service(settings)

    @asynccontextmanager
    async def lifespan(_server: MCPServer):
        try:
            yield {"service": service}
        finally:
            await service.aclose()

    mcp = MCPServer(
        name="Glovebox",
        title="Glovebox",
        instructions=INSTRUCTIONS,
        version=__version__,
        lifespan=lifespan,
    )

    @mcp.tool(description=(
        "Decode one VIN with NHTSA vPIC. "
        "HTTP success is not a clean decode: read error_code. "
        "Empty specs mean NHTSA has no value, not that equipment is missing. "
        "model_year is optional. Partial VINs may use *."
    ))
    async def decode_vin(vin: str, model_year: int | None = None, include_raw_filled: bool = False) -> dict:
        return await service.decode_vin(vin, model_year, include_raw_filled)

    @mcp.tool(description=(
        "Recalls for a make, model, and model year, or one campaign number. "
        "Do not pass a VIN. A campaign is not proof a specific car was repaired. "
        "An empty list can be a spelling miss."
    ))
    async def get_recalls(
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        campaign_number: str | None = None,
        include_remedy: bool = False,
    ) -> dict:
        return await service.get_recalls(make, model, model_year, campaign_number, include_remedy)

    @mcp.tool(description=(
        "Complaint counts for a make, model, and model year. "
        "Returns totals and components only. Never returns narratives or VINs. "
        "Counts are consumer reports, not findings."
    ))
    async def summarize_complaints(
        make: str,
        model: str,
        model_year: int,
        component: str | None = None,
    ) -> dict:
        return await service.summarize_complaints(make, model, model_year, component)

    @mcp.tool(description=(
        "NCAP star ratings. Pass make, model, and model year, or a vehicle_id from a previous variant list. "
        "Not Rated is a real value. An empty variant list can be a spelling miss."
    ))
    async def get_safety_ratings(
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        vehicle_id: str | None = None,
    ) -> dict:
        return await service.get_safety_ratings(make, model, model_year, vehicle_id)

    @mcp.tool(description=(
        "Search the local NHTSA investigations file (FLAT_INV). "
        "There is no investigations REST API. "
        "Filter by make, model, model year, component, free text, or nhtsa_id. "
        "Summary text is included only when nhtsa_id selects one investigation, and it is clipped."
    ))
    async def search_investigations(
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
        component: str | None = None,
        query: str | None = None,
        nhtsa_id: str | None = None,
    ) -> dict:
        return await service.search_investigations(make, model, model_year, component, query, nhtsa_id)

    @mcp.tool(description=(
        "Model strings NHTSA uses in vPIC, the recall product list, and NCAP for one make and year. "
        "The recall product list is incomplete. Use it when a recall or rating search comes back empty."
    ))
    async def list_model_names(make: str, model_year: int) -> dict:
        return await service.list_model_names(make, model_year)

    @mcp.tool(description=(
        "One vehicle profile: decode if a VIN is given, then recalls, complaint counts, ratings, and investigations. "
        "Call this first. section_status tells you which parts failed. "
        "A failed section does not erase the others. This is not a repair-status check."
    ))
    async def vehicle_profile(
        vin: str | None = None,
        make: str | None = None,
        model: str | None = None,
        model_year: int | None = None,
    ) -> dict:
        return await service.vehicle_profile(vin, make, model, model_year)

    @mcp.resource("nhtsa://about", mime_type="text/plain", description="What Glovebox will and will not claim.")
    def about() -> str:
        return (
            "Glovebox is a local MCP server over public NHTSA data. "
            "It is not NHTSA and not an official decoder.\n\n"
            f"{SPEC_NOTE}\n\n{REPAIR_NOTE}\n\n"
            "Not Rated is not zero stars. Complaint tools return counts only.\n"
            "NHTSA terms: https://www.nhtsa.gov/about-nhtsa/terms-use"
        )

    @mcp.resource("nhtsa://coverage", mime_type="text/plain", description="Which datasets Glovebox reads and which it skips.")
    def coverage() -> str:
        investigations = "local FLAT_INV.zip" if settings.investigations_file or not settings.offline else "not configured"
        mode = "fixtures" if settings.fixtures_dir else "offline" if settings.offline else "live NHTSA APIs with a local cache"
        return (
            f"Mode: {mode}.\n"
            "vPIC decode: live API unless fixtures or offline.\n"
            "Recalls and complaint counts: live API, shaped before they reach the model.\n"
            "NCAP ratings: live API.\n"
            f"Investigations: {investigations}. No Postgres database in this version.\n"
            "Not included: fuel economy, title history, manufacturer communications, FARS.\n"
            "Recall API dates are read as day/month/year."
        )

    @mcp.resource("nhtsa://vehicle/{vin}", mime_type="application/json", description="Profile for one VIN.")
    async def vehicle_resource(vin: str) -> str:
        import json

        profile = await service.vehicle_profile(vin=vin)
        return json.dumps(profile, indent=2)

    @mcp.prompt(description="One-screen buyer brief. Quote only tool fields.")
    def buyer_brief(vin: str = "", make: str = "", model: str = "", model_year: str = "") -> str:
        subject = vin or " ".join(part for part in (model_year, make, model) if part)
        return (
            f"Write a one-screen brief for {subject or 'the vehicle'}. "
            "Call vehicle_profile first. Quote only fields the tool returned. "
            "Say unknown when a spec is absent. Say not rated when that is the value. "
            "Do not say a recall was repaired."
        )

    @mcp.prompt(description="Explain recall campaigns without claiming a VIN was repaired.")
    def recall_status(vin: str = "", make: str = "", model: str = "", model_year: str = "") -> str:
        return (
            "Explain the recall campaigns for "
            f"{vin or ' '.join(part for part in (model_year, make, model) if part) or 'the vehicle'}. "
            "Use get_recalls or vehicle_profile. Mention park-outside and do-not-drive flags when they are true. "
            "End by saying this does not show whether a specific vehicle was repaired."
        )

    @mcp.prompt(description="Check NCAP spellings before concluding a vehicle was not tested.")
    def ratings_gap(make: str, model: str, model_year: str) -> str:
        return (
            f"Look up NCAP ratings for {model_year} {make} {model}. "
            "Call get_safety_ratings. If the variant list is empty, call list_model_names "
            "and show the NCAP spellings before concluding the vehicle was not tested."
        )

    mcp._glovebox_service = service  # type: ignore[attr-defined]
    return mcp
