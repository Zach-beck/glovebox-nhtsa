# Contributing

I want small, reviewable changes. The server is clean-room: public NHTSA APIs, public files, and public docs. Do not copy another MCP server. Do not bring in employer systems or private data.

```bash
uv sync
uv run pytest
```

All 29 tests should pass with no network and no API key. If you add a golden case, put a frozen JSON file in `tests/fixtures` and a question in `tests/golden_cases.py`. Strip real complaint narratives. Fake strings used to prove redaction are fine.

`.env` stays gitignored. `.env.example` lists names only.

Longer notes: [docs/contributing.md](docs/contributing.md). Design map: [docs/README.md](docs/README.md).
