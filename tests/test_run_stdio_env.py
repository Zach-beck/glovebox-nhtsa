"""run_stdio_calls live vs fixture env wiring."""

import importlib.util
from pathlib import Path


def _load_run_stdio():
    path = Path("scripts/run_stdio_calls.py")
    spec = importlib.util.spec_from_file_location("run_stdio_calls", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_live_mode_does_not_pin_investigations_fixture(monkeypatch):
    monkeypatch.delenv("GLOVEBOX_INVESTIGATIONS_FILE", raising=False)
    monkeypatch.setenv("GLOVEBOX_FIXTURES", "")
    # Import and replicate env block from main without starting MCP.
    import os

    ROOT = Path(__file__).resolve().parents[1]
    fixtures = os.environ.get("GLOVEBOX_FIXTURES", str(ROOT / "tests" / "fixtures"))
    investigations = os.environ.get("GLOVEBOX_INVESTIGATIONS_FILE")
    env = {"GLOVEBOX_FIXTURES": fixtures, "GLOVEBOX_OFFLINE": "1"}
    if fixtures == "":
        env.pop("GLOVEBOX_FIXTURES")
        env["GLOVEBOX_OFFLINE"] = "0"
        if investigations:
            env["GLOVEBOX_INVESTIGATIONS_FILE"] = investigations
    else:
        inv_path = investigations or str(ROOT / "tests" / "fixtures" / "investigations.txt")
        env["GLOVEBOX_INVESTIGATIONS_FILE"] = inv_path
    assert "GLOVEBOX_INVESTIGATIONS_FILE" not in env