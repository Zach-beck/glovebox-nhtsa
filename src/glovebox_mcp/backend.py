"""Fetch NHTSA JSON, or a frozen fixture, with a small polite limiter."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx

from glovebox_mcp import __version__
from glovebox_mcp.shaping import error_body

ALLOWED_HOSTS = frozenset({"vpic.nhtsa.dot.gov", "api.nhtsa.gov", "static.nhtsa.gov"})
USER_AGENT = f"Glovebox/{__version__} (local MCP; public NHTSA data)"
COMPLAINT_BYTE_CAP = 8_000_000
DEFAULT_BYTE_CAP = 2_000_000

VPIC = "https://vpic.nhtsa.dot.gov/api"
API = "https://api.nhtsa.gov"


class UpstreamError(Exception):
    def __init__(self, code: str, detail: str, retryable: bool, source: str = "nhtsa") -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.retryable = retryable
        self.source = source

    def to_dict(self) -> dict[str, Any]:
        return error_body(self.code, self.source, self.retryable, self.detail)


def request_key(name: str, params: dict[str, Any]) -> str:
    clean = {key: value for key, value in params.items() if value is not None and value != ""}
    encoded = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return f"{name}|{encoded}"


def build_url(name: str, params: dict[str, Any]) -> str:
    if name == "decode_vin":
        query = {"format": "json"}
        if params.get("model_year"):
            query["modelyear"] = str(params["model_year"])
        vin = quote(str(params["vin"]), safe="*")
        return f"{VPIC}/vehicles/DecodeVinValues/{vin}?{urlencode(query)}"
    if name == "recalls_by_vehicle":
        return f"{API}/recalls/recallsByVehicle?{urlencode({'make': params['make'], 'model': params['model'], 'modelYear': params['model_year']})}"
    if name == "recalls_by_campaign":
        return f"{API}/recalls/campaignNumber?{urlencode({'campaignNumber': params['campaign_number']})}"
    if name == "complaints_by_vehicle":
        return f"{API}/complaints/complaintsByVehicle?{urlencode({'make': params['make'], 'model': params['model'], 'modelYear': params['model_year']})}"
    if name == "ratings_model":
        year = quote(str(params["model_year"]), safe="")
        make = quote(str(params["make"]), safe="")
        model = quote(str(params["model"]), safe="")
        return f"{API}/SafetyRatings/modelyear/{year}/make/{make}/model/{model}"
    if name == "ratings_make":
        year = quote(str(params["model_year"]), safe="")
        make = quote(str(params["make"]), safe="")
        return f"{API}/SafetyRatings/modelyear/{year}/make/{make}"
    if name == "ratings_vehicle":
        return f"{API}/SafetyRatings/VehicleId/{quote(str(params['vehicle_id']), safe='')}"
    if name == "products_models":
        return (
            f"{API}/products/vehicle/models?"
            + urlencode({"modelYear": params["model_year"], "make": params["make"], "issueType": "r"})
        )
    if name == "vpic_models":
        make = quote(str(params["make"]), safe="")
        year = quote(str(params["model_year"]), safe="")
        return f"{VPIC}/vehicles/GetModelsForMakeYear/make/{make}/modelyear/{year}?format=json"
    raise UpstreamError("not_found", f"Unknown NHTSA request {name}.", False, "glovebox")


def _host_allowed(url: str) -> bool:
    host = urlparse(url).hostname
    return host in ALLOWED_HOSTS


class HostLimiter:
    def __init__(self, gap_seconds: float, max_in_flight: int = 2) -> None:
        self.gap_seconds = gap_seconds
        self.max_in_flight = max_in_flight
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._next_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self, host: str) -> AsyncIterator[None]:
        async with self._lock:
            semaphore = self._semaphores.setdefault(host, asyncio.Semaphore(self.max_in_flight))
        await semaphore.acquire()
        try:
            async with self._lock:
                now = time.monotonic()
                scheduled = max(now, self._next_time.get(host, 0.0))
                self._next_time[host] = scheduled + self.gap_seconds
            delay = scheduled - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            yield
        finally:
            semaphore.release()


class FixtureBackend:
    def __init__(self, directory: Path) -> None:
        self._map: dict[str, dict[str, Any]] = {}
        if not directory.is_dir():
            raise FileNotFoundError(f"Fixture directory does not exist: {directory}")
        for path in sorted(directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            request = payload["_request"]
            self._map[request_key(request["name"], request["params"])] = payload["body"]

    async def fetch(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        key = request_key(name, params)
        if key not in self._map:
            raise UpstreamError("not_found", f"No fixture for {name}.", False, "fixture")
        return self._map[key]


class OfflineBackend:
    async def fetch(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        del name, params
        raise UpstreamError(
            "upstream_unavailable",
            "Offline mode answers from local files only. This dataset is not on disk.",
            False,
            "glovebox",
        )


class LiveBackend:
    def __init__(
        self,
        *,
        gap_seconds: float = 0.25,
        timeout: float = 20.0,
        client: httpx.AsyncClient | None = None,
        sleeper: Any = asyncio.sleep,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=False)
        self._owns_client = client is None
        self._limiter = HostLimiter(gap_seconds)
        self._sleeper = sleeper

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        url = build_url(name, params)
        if not _host_allowed(url):
            raise UpstreamError("not_found", "Refused a request outside the NHTSA host list.", False, "glovebox")
        host = urlparse(url).hostname or ""
        async with self._limiter.slot(host):
            return await self._fetch_with_backoff(name, url)

    async def _fetch_with_backoff(self, name: str, url: str) -> dict[str, Any]:
        last_error: UpstreamError | None = None
        for attempt in range(3):
            try:
                response = await self._client.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            except httpx.TimeoutException as exc:
                last_error = UpstreamError("upstream_unavailable", f"Timed out calling {name}.", True)
                if attempt == 2:
                    raise last_error from exc
                await self._sleeper(2**attempt)
                continue
            except httpx.HTTPError as exc:
                raise UpstreamError("upstream_unavailable", f"Could not reach {name}.", True) from exc
            if 300 <= response.status_code < 400:
                raise UpstreamError("upstream_unavailable", "Refused a redirect away from the NHTSA host.", False)
            if response.status_code in {429, 503}:
                delay = _retry_delay(response, attempt)
                last_error = UpstreamError("upstream_unavailable", f"NHTSA returned {response.status_code} for {name}.", True)
                if attempt == 2:
                    raise last_error
                await self._sleeper(delay)
                continue
            if response.status_code == 403 and "Missing Authentication Token" in response.text:
                raise UpstreamError("not_found", "NHTSA has no route at that path.", False)
            if response.status_code >= 400:
                raise UpstreamError("upstream_unavailable", f"NHTSA returned HTTP {response.status_code} for {name}.", response.status_code >= 500)
            self._enforce_size(name, response)
            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                raise UpstreamError("upstream_unavailable", f"{name} did not return JSON.", True) from exc
            if not isinstance(payload, dict):
                raise UpstreamError("upstream_unavailable", f"{name} returned an unexpected JSON type.", False)
            return payload
        assert last_error is not None
        raise last_error

    def _enforce_size(self, name: str, response: httpx.Response) -> None:
        cap = COMPLAINT_BYTE_CAP if name == "complaints_by_vehicle" else DEFAULT_BYTE_CAP
        header = response.headers.get("content-length")
        if header and header.isdigit() and int(header) > cap:
            raise UpstreamError("too_large", f"{name} response is {header} bytes, over the {cap} byte cap.", False)
        if len(response.content) > cap:
            raise UpstreamError("too_large", f"{name} response exceeded the {cap} byte cap.", False)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("retry-after", "").strip()
    if header.isdigit():
        return float(header)
    return float(2**attempt)
