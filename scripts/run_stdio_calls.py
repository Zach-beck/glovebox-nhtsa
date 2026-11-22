"""Call Glovebox tools over stdio. One JSON object per line on stdin.

Each line is {"id", "name", "arguments"}. A line with "name": null records no call.
Writes a JSON list of {id, tool_calls} to the path in argv[1].
Uses fixtures unless GLOVEBOX_FIXTURES is already set to empty to force live mode.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


async def main() -> int:
    lines = [json.loads(line) for line in sys.stdin if line.strip()]
    fixtures = os.environ.get("GLOVEBOX_FIXTURES", str(ROOT / "tests" / "fixtures"))
    investigations = os.environ.get("GLOVEBOX_INVESTIGATIONS_FILE")
    env = {
        "GLOVEBOX_FIXTURES": fixtures,
        "GLOVEBOX_OFFLINE": "1",
        "GLOVEBOX_CACHE_DIR": os.environ.get("GLOVEBOX_CACHE_DIR", "/tmp/glovebox-agent-eval-cache"),
        "GLOVEBOX_REQUEST_GAP_SECONDS": "0",
    }
    if fixtures == "":
        env.pop("GLOVEBOX_FIXTURES")
        env["GLOVEBOX_OFFLINE"] = "0"
        env["GLOVEBOX_REQUEST_GAP_SECONDS"] = "0.4"
        if investigations:
            env["GLOVEBOX_INVESTIGATIONS_FILE"] = investigations
        elif os.environ.get("GLOVEBOX_REQUIRE_LIVE_INVESTIGATIONS", "").strip() in {"1", "true", "yes"}:
            print(
                "live mode: GLOVEBOX_INVESTIGATIONS_FILE is unset; investigations will use live FLAT_INV.zip",
                file=sys.stderr,
            )
    else:
        inv_path = investigations or str(ROOT / "tests" / "fixtures" / "investigations.txt")
        env["GLOVEBOX_INVESTIGATIONS_FILE"] = inv_path
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "glovebox_nhtsa"],
        cwd=str(ROOT),
        env=env,
    )
    out = []
    async with Client(params, mode="legacy") as client:
        for item in lines:
            if not item.get("name"):
                out.append({"id": item["id"], "tool_calls": []})
                continue
            result = await client.call_tool(item["name"], item.get("arguments") or {})
            text = result.content[0].text if result.content else ""
            try:
                body = json.loads(text)
            except json.JSONDecodeError:
                body = {"raw": text}
            out.append(
                {
                    "id": item["id"],
                    "tool_calls": [
                        {"name": item["name"], "arguments": item.get("arguments") or {}, "result": body}
                    ],
                }
            )
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} calls", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
