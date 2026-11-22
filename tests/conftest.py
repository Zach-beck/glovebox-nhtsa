from __future__ import annotations

from pathlib import Path

import pytest

import anyio

from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service


def run(async_fn, *args, **kwargs):
    async def wrapper():
        return await async_fn(*args, **kwargs)

    return anyio.run(wrapper)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
INVESTIGATIONS = FIXTURES / "investigations.txt"


@pytest.fixture
def service(tmp_path: Path):
    settings = Settings(
        fixtures_dir=FIXTURES,
        investigations_file=INVESTIGATIONS,
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        offline=True,
        request_gap_seconds=0,
    )
    built = build_service(settings)
    yield built
