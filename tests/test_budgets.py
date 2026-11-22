import json

import anyio

from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.server import create_server
from glovebox_nhtsa.shaping import BUDGETS, estimate_tokens
from glovebox_nhtsa.text import INSTRUCTIONS
from tests.conftest import FIXTURES, INVESTIGATIONS, run


def test_shaped_tools_stay_inside_token_budgets(service):
    samples = {
        "decode_vin": run(service.decode_vin, "5UXWX7C5*BA", 2011),
        "get_recalls": run(service.get_recalls, "ACURA", "RDX", 2012, None, True),
        "summarize_complaints": run(service.summarize_complaints, "BMW", "X3", 2011),
        "get_safety_ratings": run(service.get_safety_ratings, vehicle_id="7520"),
        "search_investigations": run(service.search_investigations, "BMW", "X3", 2011),
        "list_model_names": run(service.list_model_names, "BMW", 2011),
        "vehicle_profile": run(service.vehicle_profile, "5UXWX7C5*BA", None, None, 2011),
    }
    over = {name: estimate_tokens(payload) for name, payload in samples.items() if estimate_tokens(payload) > BUDGETS[name]}
    assert over == {}


def test_instructions_and_tool_descriptions_fit():
    settings = Settings(fixtures_dir=FIXTURES, investigations_file=INVESTIGATIONS, offline=True)
    server = create_server(settings)

    async def collect() -> str:
        tools = await server.list_tools()
        descriptions = "\n".join(tool.description or "" for tool in tools)
        return INSTRUCTIONS + "\n" + descriptions

    text = anyio.run(collect)
    assert estimate_tokens(text) <= BUDGETS["instructions_and_tools"]
    banned = "Prompt" + " Engineering"
    assert banned not in text
    assert json.dumps(text)
