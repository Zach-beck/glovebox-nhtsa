"""A few live NHTSA calls. Not used by CI.

Prints status fields only. Does not print complaint narratives.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service


async def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="glovebox-smoke-"))
    investigations = os.environ.get("GLOVEBOX_INVESTIGATIONS_FILE")
    settings = Settings(
        cache_dir=root / "cache",
        data_dir=root / "data",
        investigations_file=Path(investigations) if investigations else None,
        request_gap_seconds=0.4,
        offline=False,
    )
    service = build_service(settings)
    try:
        decoded = await service.decode_vin("5UXWX7C5*BA", 2011)
        print(
            "decode",
            decoded.get("identity", {}).get("error_code"),
            decoded.get("specs", {}).get("make"),
            decoded.get("specs", {}).get("model"),
            decoded.get("specs", {}).get("model_year"),
        )
        recalls = await service.get_recalls("acura", "rdx", 2012)
        print("recalls", recalls.get("count"), "first", (recalls.get("campaigns") or [{}])[0].get("campaign_number"))
        ratings = await service.get_safety_ratings(vehicle_id="7520")
        rating = ratings.get("rating") or {}
        print("ratings", rating.get("overall_rating"), rating.get("vehicle_description"))
        if investigations:
            found = await service.search_investigations(nhtsa_id="EA15001")
            print("investigations", found.get("count"), "returned", found.get("returned"), "error", found.get("error"))
    finally:
        await service.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
