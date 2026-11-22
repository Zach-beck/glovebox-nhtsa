"""Public NHTSA source URLs for shaped tool output."""

from __future__ import annotations

from typing import Any

from glovebox_nhtsa.backend import build_url
from glovebox_nhtsa.investigations import INV_URL as INVESTIGATIONS_ARCHIVE_URL

COVERAGE_RESOURCE = "glovebox://coverage_limits"


def source_url(fetch_name: str, params: dict[str, Any]) -> str:
    if fetch_name == "investigations_index":
        return INVESTIGATIONS_ARCHIVE_URL
    return build_url(fetch_name, params)