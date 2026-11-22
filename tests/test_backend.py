import httpx
import anyio

from glovebox_mcp.backend import LiveBackend, build_url


async def _noop(_seconds: float) -> None:
    return None


def test_urls_stay_on_nhtsa_hosts():
    url = build_url("decode_vin", {"vin": "5UXWX7C5*BA", "model_year": 2011})
    assert url.startswith("https://vpic.nhtsa.dot.gov/")
    assert "5UXWX7C5*BA" in url
    recalls = build_url("recalls_by_vehicle", {"make": "BMW", "model": "X3", "model_year": 2011})
    assert recalls.startswith("https://api.nhtsa.gov/recalls/")


def test_backoff_honors_retry_after_zero():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, headers={"retry-after": "0"})
        return httpx.Response(200, json={"Count": 0, "results": []})

    async def run() -> dict:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        backend = LiveBackend(gap_seconds=0, client=client, sleeper=_noop)
        try:
            return await backend.fetch("recalls_by_vehicle", {"make": "BMW", "model": "X3", "model_year": 2011})
        finally:
            await backend.aclose()

    payload = anyio.run(run)
    assert payload["Count"] == 0
    assert calls["n"] == 2


def test_redirects_are_refused():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        backend = LiveBackend(gap_seconds=0, client=client, sleeper=_noop)
        try:
            await backend.fetch("ratings_vehicle", {"vehicle_id": "7520"})
        finally:
            await backend.aclose()

    try:
        anyio.run(run)
    except Exception as exc:
        assert "redirect" in str(exc).lower()
    else:
        raise AssertionError("redirect was followed or ignored")
