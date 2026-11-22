"""List Glovebox tools over stdio and call two of them against fixtures."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


async def main() -> int:
    fixtures = os.environ.get("GLOVEBOX_FIXTURES", str(ROOT / "tests" / "fixtures"))
    investigations = os.environ.get(
        "GLOVEBOX_INVESTIGATIONS_FILE",
        str(ROOT / "tests" / "fixtures" / "investigations.txt"),
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "glovebox_mcp"],
        cwd=str(ROOT),
        env={
            "GLOVEBOX_FIXTURES": fixtures,
            "GLOVEBOX_INVESTIGATIONS_FILE": investigations,
            "GLOVEBOX_OFFLINE": "1",
            "GLOVEBOX_CACHE_DIR": os.environ.get("GLOVEBOX_CACHE_DIR", str(ROOT / ".cache-stdio")),
        },
    )
    async with Client(params, mode="legacy") as client:
        listed = await client.list_tools()
        names = [tool.name for tool in listed.tools]
        print("tools:", ", ".join(names))
        decoded = await client.call_tool("decode_vin", {"vin": "5UXWX7C5*BA", "model_year": 2011})
        print(decoded.content[0].text)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
