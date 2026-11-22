# Glovebox

Glovebox is a local [Model Context Protocol](https://modelcontextprotocol.io) server for public vehicle data from the National Highway Traffic Safety Administration. Give it a VIN, or a year, make, and model, and it returns a short profile: decoded specs, recall campaigns, complaint counts, NCAP ratings, and defect investigations.

The server shapes those answers before a model sees them. That work is Context Engineering: empty specs stay unknown, `Not Rated` stays `Not Rated`, and complaint narratives never enter the context.

Glovebox is not affiliated with, endorsed by, or published by NHTSA or the U.S. Department of Transportation. NHTSA's terms say the site is public information that may be copied, and they disclaim accuracy. See [their terms](https://www.nhtsa.gov/about-nhtsa/terms-use).

This package is not on PyPI. `uvx glovebox-mcp` will work only after a release, and this repo does not publish one. Install from a checkout.

## Name collision

`glovebox-mcp` is free on PyPI (the project URL returns 404). It is not free on GitHub. [segentic-lab/glovebox-mcp](https://github.com/segentic-lab/glovebox-mcp) is a different MIT project: a sandboxed computer-use server. It is also listed in the official MCP registry. An unrelated PyPI project named `glovebox` (0.0.5) exists and is not this server. Nothing here was registered or published.

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run glovebox-mcp
```

That process speaks MCP on stdin and stdout. Point a client at it:

```json
{
  "mcpServers": {
    "glovebox": {
      "command": "uv",
      "args": ["run", "glovebox-mcp"],
      "cwd": "/absolute/path/to/this/checkout"
    }
  }
}
```

Docker, still local, still stdio:

```bash
docker build -t glovebox-mcp .
docker run -i --rm glovebox-mcp
```

Ask for a profile of a VIN. A useful answer quotes `error_code`, names the vehicle, and does not claim a recall was repaired.

## What you can ask

| Tool | Use it for |
| --- | --- |
| `vehicle_profile` | The first call. Specs, recalls, complaint counts, ratings, investigations. |
| `decode_vin` | One VIN. Read `error_code`. |
| `get_recalls` | Campaigns for a make, model, and year, or one campaign number. |
| `summarize_complaints` | Counts only. No owner text. |
| `get_safety_ratings` | Stars, or the variant list. |
| `search_investigations` | The local investigations file. |
| `list_model_names` | Spellings that differ across NHTSA datasets. |

Details: [docs/tool-reference.md](docs/tool-reference.md).

## Clients

- [Cursor](docs/clients/cursor.md)
- [Claude Desktop](docs/clients/claude-desktop.md)
- [Claude Code](docs/clients/claude-code.md)
- [VS Code](docs/clients/vscode.md)
- [OpenCode](docs/clients/opencode.md)

## Tests and evals

Deterministic tests run offline. They do not call NHTSA and they do not need a model key.

```bash
uv run pytest
uv run python evals/local.py
```

`evals/local.py` prints a skip report when `.env` has no key. It does not prompt. The method is [docs/evals.md](docs/evals.md). The latest numbers are [docs/eval-results.md](docs/eval-results.md).

## Design notes

The research that led here is still in the repo:

- [Data inventory](docs/research/nhtsa-data.md)
- [Rate limits and terms](docs/research/rate-limits-and-terms.md)
- [Language decision](docs/decisions/0001-language-and-runtime.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)

## License

MIT. See [LICENSE](LICENSE).
