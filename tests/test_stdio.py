import sys

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from tests.conftest import FIXTURES, INVESTIGATIONS, ROOT


def test_stdio_client_lists_and_calls_tools(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "glovebox_nhtsa"],
        cwd=str(ROOT),
        env={
            "GLOVEBOX_FIXTURES": str(FIXTURES),
            "GLOVEBOX_INVESTIGATIONS_FILE": str(INVESTIGATIONS),
            "GLOVEBOX_CACHE_DIR": str(tmp_path / "cache"),
            "GLOVEBOX_DATA_DIR": str(tmp_path / "data"),
            "GLOVEBOX_OFFLINE": "1",
        },
    )

    async def run():
        async with Client(params, mode="legacy") as client:
            listed = await client.list_tools()
            names = sorted(tool.name for tool in listed.tools)
            decoded = await client.call_tool("decode_vin", {"vin": "5UXWX7C5*BA", "model_year": 2011})
            profile = await client.call_tool(
                "vehicle_profile",
                {"vin": "5UXWX7C5*BA", "model_year": 2011},
            )
            prompts = await client.list_prompts()
            return names, decoded, profile, [item.name for item in prompts.prompts]

    names, decoded, profile, prompts = anyio.run(run)
    assert names == [
        "decode_vin",
        "get_recalls",
        "get_safety_ratings",
        "list_model_names",
        "search_investigations",
        "summarize_complaints",
        "vehicle_profile",
    ]
    assert "BMW" in decoded.content[0].text
    assert "17V683000" in profile.content[0].text
    assert "buyer_brief" in prompts
    assert "person@example.com" not in profile.content[0].text
