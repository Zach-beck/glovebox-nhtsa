# Glovebox

I built Glovebox so I can hand a model a VIN and get one short, sourced vehicle profile from public NHTSA data. It is a local [Model Context Protocol](https://modelcontextprotocol.io) server. The package and command are `glovebox-nhtsa`.

A raw dump of NHTSA is a bad context for a model. Empty spec fields mean "no value on file," not "this car lacks the part." `Not Rated` is a real rating. Recall rows are campaigns for a model string, not proof that your VIN was repaired. Complaint files are huge and can carry partial VINs. Glovebox does that shaping before the model sees the data. I call that work Context Engineering.

Glovebox is not affiliated with, endorsed by, or published by NHTSA or the U.S. Department of Transportation. Their [terms](https://www.nhtsa.gov/about-nhtsa/terms-use) say the site is public information that may be copied, and they disclaim accuracy. I am not NHTSA.

## Install

You need Python 3.12 and [uv](https://docs.astral.sh/uv/). This package is **not on PyPI**. Installing from PyPI would need a separate publish step and maintainer approval. For now, install from git:

```bash
uvx --from git+https://github.com/Zach-beck/glovebox-nhtsa glovebox-nhtsa
```

That runs the MCP server on stdio. For a one-off HTML or JSON report without an MCP client:

```bash
uvx --from git+https://github.com/Zach-beck/glovebox-nhtsa glovebox report 5UXWX7C5*BA --model-year 2011 --html report.html
```

From a checkout, `uv sync` and `uv run glovebox-nhtsa` behave the same. Set `GLOVEBOX_REPORT_DIR` when you want HTML tools to write files agents can open. Caching defaults and TTLs are in [docs/caching.md](docs/caching.md).

### MCP client config

**Cursor** ([`.cursor/mcp.json`](.cursor/mcp.json) in this repo):

```json
{
  "mcpServers": {
    "glovebox-nhtsa": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Zach-beck/glovebox-nhtsa", "glovebox-nhtsa"]
    }
  }
}
```

**Claude Desktop** (paths vary by OS; see [docs/clients/claude-desktop.md](docs/clients/claude-desktop.md)):

```json
{
  "mcpServers": {
    "glovebox": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Zach-beck/glovebox-nhtsa", "glovebox-nhtsa"]
    }
  }
}
```

**OpenCode** (`opencode.json`):

```json
{
  "mcp": {
    "servers": {
      "glovebox": {
        "type": "local",
        "command": ["uvx", "--from", "git+https://github.com/Zach-beck/glovebox-nhtsa", "glovebox-nhtsa"]
      }
    }
  }
}
```

## 60-second quickstart

```bash
uv sync
uv run glovebox-nhtsa
```

That process speaks MCP on stdin and stdout. It does not need an API key.

**Cursor (checkout dev).** The file in this repo is [`.cursor/mcp.json`](.cursor/mcp.json):

```json
{
  "mcpServers": {
    "glovebox-nhtsa": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "glovebox-nhtsa"]
    }
  }
}
```

**Claude Desktop.** I have not re-checked the config path against Anthropic's own page. The usual files are `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows, and `~/.config/Claude/claude_desktop_config.json` on Linux.

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

**Claude Code**, from this checkout:

```bash
claude mcp add --transport stdio glovebox -- uv run glovebox-nhtsa
```

More clients: [Cursor](docs/clients/cursor.md), [Claude Desktop](docs/clients/claude-desktop.md), [Claude Code](docs/clients/claude-code.md), [VS Code](docs/clients/vscode.md), [OpenCode](docs/clients/opencode.md).

Docker, still local, still stdio:

```bash
docker build -t glovebox-nhtsa .
docker run -i --rm glovebox-nhtsa
```

## Tools, resources, and prompts

| Name | What it does |
| --- | --- |
| `vehicle_report` | One VIN dossier with `source_url`, `fetched_at`, and per-section status. JSON or HTML. |
| `render_vehicle_report_html` | Self-contained HTML for one VIN. Writes a file when `GLOVEBOX_REPORT_DIR` is set. |
| `vehicle_profile` | Specs, recalls, complaint counts, ratings, investigations, and a status per section. |
| `decode_vin` | One VIN. Read `error_code`. HTTP 200 is not a clean decode. |
| `get_recalls` | Campaigns for a make, model, and year, or one campaign number. Not a VIN, and not repair status. |
| `summarize_complaints` | Counts and components only. No owner text and no VIN. |
| `get_safety_ratings` | Stars for one variant, or the variant list. `Not Rated` stays words. |
| `search_investigations` | Local search of NHTSA's investigations file. There is no investigations REST API. |
| `list_model_names` | Spellings vPIC, the recall list, and NCAP use for one make and year. |

| Resource | What it is |
| --- | --- |
| `nhtsa://about` | What I will not claim, plus NHTSA's terms link. |
| `nhtsa://coverage` | Which datasets are live, which are local, and what I left out. |
| `nhtsa://vehicle/{vin}` | The same object as `vehicle_profile`. |

| Prompt | What it asks the model to do |
| --- | --- |
| `buyer_brief` | Call `vehicle_profile` and quote only returned fields. |
| `recall_status` | Explain campaigns and say this is not repair status. |
| `ratings_gap` | If ratings are empty, check spellings before saying the car was not tested. |

Full arguments: [docs/tool-reference.md](docs/tool-reference.md).

## Example

This is the fixture result for NHTSA's own partial VIN `5UXWX7C5*BA`, model year 2011. The live API returned the same identity when I smoked it: error code 6, BMW X3.

```json
{
  "identity": {
    "vin": "5UXWX7C5*BA",
    "error_code": "6",
    "error_text": "6 - Incomplete VIN",
    "spec_note": "A missing spec means NHTSA has no value on file. Do not read a missing field as evidence that the vehicle lacks that equipment."
  },
  "specs": {
    "make": "BMW",
    "model": "X3",
    "model_year": "2011",
    "trim": "xDrive35i",
    "plant_city": "MUNICH",
    "plant_country": "GERMANY"
  }
}
```

I omitted the rest of the spec block here. Empty fields and `Not Applicable` are already gone.

A full HTML dossier for the same fixture VIN is committed at [docs/sample-report.html](docs/sample-report.html) (no screenshot; open the file in a browser).

## Evals

The CI signal is offline pytest on frozen fixtures. No network and no model key.

I also ran those 40 cases myself, in this agent session, and scored 40/40. That run is not blinded: I wrote the golden set and then answered it. Treat 40/40 as an upper bound. The write-up, the categories, and the blinded rerun I want next are in [docs/eval-results.md](docs/eval-results.md). The method is [docs/evals.md](docs/evals.md).

```bash
make eval-fixture   # same as uv run pytest, frozen fixtures
make eval-live      # live tool calls for non-fixture-only golden cases (network)
uv run python evals/local.py
```

`make eval-fixture` is the CI gate. `make eval-live` is a maintainer smoke against NHTSA, not a model score. The OpenAI helper skips unless you put `OPENAI_API_KEY` in a gitignored `.env`. I do not want that key in CI.

## Data, terms, and rate limits

Glovebox reads public NHTSA endpoints and one public file:

- vPIC VIN decode at `vpic.nhtsa.dot.gov`
- Recalls, complaint counts, and NCAP ratings at `api.nhtsa.gov`
- Defect investigations from `FLAT_INV.zip` on `static.nhtsa.gov`

NHTSA's pages disagree about a numeric quota. A small polite test I ran on 2026-11-22 saw no HTTP 429 and no rate-limit headers. Details and citations: [docs/research/rate-limits-and-terms.md](docs/research/rate-limits-and-terms.md).

In the server I wait 0.25 seconds between calls to the same host, keep at most two calls in flight, and retry 429 and 503 up to three times. I cache shaped results in memory by default (decode 7 days, recalls and complaint counts 6 hours, ratings and model lists 7 days). Set `GLOVEBOX_CACHE=off` to disable. I refuse redirects off those three hosts. I do not cache complaint narratives because I never keep them. Details: [docs/caching.md](docs/caching.md).

## Limitations

- A recall campaign is not proof that your car was repaired.
- A missing spec is unknown, not "the car lacks it."
- `Not Rated` is not zero stars.
- Model strings differ across vPIC, recalls, and NCAP. An empty list can be a spelling miss.
- Recall dates from the API are day/month/year.
- I do not ship fuel economy, title history, manufacturer communications, or FARS.
- There is no Postgres offline decode. Offline mode is the investigations file plus whatever is already in the cache.
- The investigations zip is about 4 MB. The text inside is about 370 MB. I index the short columns.

## Roadmap

v1 is this local server. Later, if I do it at all: manufacturer communications from the public flat files, an optional authenticated host (not an open proxy), and a blinded eval on two or three models. I am not putting a public URL in front of NHTSA. The longer plan is [docs/roadmap.md](docs/roadmap.md).

## Name

The product is Glovebox. The repo, image, distribution, and command are `glovebox-nhtsa` because `glovebox-mcp` is already [segentic-lab/glovebox-mcp](https://github.com/segentic-lab/glovebox-mcp), a different project. On 2026-11-22, PyPI returned 404 for `glovebox-nhtsa`, and a GitHub name search found no repository with that name. I have not published this.

## Docs and license

Index: [docs/README.md](docs/README.md). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

MIT, 2026, Zacharias Beck. See [LICENSE](LICENSE).
