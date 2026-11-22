# Glovebox

Glovebox is a local [Model Context Protocol](https://modelcontextprotocol.io) server for public vehicle data from the National Highway Traffic Safety Administration. Give it a VIN, or a year, make, and model, and it returns a short profile: decoded specs, recall campaigns, complaint counts, NCAP ratings, and defect investigations.

The server shapes those answers before a model sees them. That work is Context Engineering: empty specs stay unknown, `Not Rated` stays `Not Rated`, and complaint narratives never enter the context.

Glovebox is not affiliated with, endorsed by, or published by NHTSA or the U.S. Department of Transportation. NHTSA's terms say the site is public information that may be copied, and they disclaim accuracy. See [their terms](https://www.nhtsa.gov/about-nhtsa/terms-use).

This package is not on PyPI. `uvx glovebox-nhtsa` will work only after a release, and this repo does not publish one. Install from a checkout.

## Names

The product is Glovebox. The repository, Docker image, PyPI distribution, and command are `glovebox-nhtsa`.

`glovebox-mcp` is already a GitHub repository: [segentic-lab/glovebox-mcp](https://github.com/segentic-lab/glovebox-mcp), an unrelated sandboxed computer-use server, also listed in the MCP registry. That is why this project does not use that name.

Checked on 2026-11-22 and not registered by us: PyPI `glovebox-nhtsa` returned 404. A GitHub search for repositories named `glovebox-nhtsa` returned none. An unrelated PyPI project named `glovebox` (0.0.5) still exists. Nothing here was published.

## Quickstart

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run glovebox-nhtsa
```

That process speaks MCP on stdin and stdout. Point a client at it:

```json
{
  "mcpServers": {
    "glovebox": {
      "command": "uv",
      "args": ["run", "glovebox-nhtsa"],
      "cwd": "/absolute/path/to/this/checkout"
    }
  }
}
```

Docker, still local, still stdio:

```bash
docker build -t glovebox-nhtsa .
docker run -i --rm glovebox-nhtsa
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
