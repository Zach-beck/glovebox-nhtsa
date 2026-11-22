# ADR 0001: Language and runtime

- Status: Accepted on 2026-11-22. Package name is `glovebox-mcp`. Complaints are counts only. Offline data is the investigations file, not Postgres.
- Date: 2026-11-22
- Deciders: Zacharias Beck, after this recommendation.

## Decision

Build the server in Python 3.12 on the official MCP Python SDK (`mcp` on PyPI, 2.3.0 when this was written). Distribute it so a contributor can run `uvx` against the package, and ship a Docker image as the path that does not need a local Python. Do not take a dependency on Prefect's FastMCP for v1.

TypeScript is the serious alternative if the priority changes from evals and data shaping to "match the existing NHTSA servers and sit on Cloudflare later." Go is the serious alternative if the priority changes to a single static binary. Rust is a credible SDK and a poor fit for this project.

## Context

The first sketch of this project assumed Python and FastMCP, six thin vPIC tools, a golden-set eval, and a CI gate. The language half of that sketch is still right. The "six vPIC tools" half is not, and it is discussed in the roadmap rather than here. The FastMCP half needs a sharper name, because two different projects use it.

This server is a data client plus a context shaper. It calls JSON APIs, parses a few tab-delimited files, drops empty fields, redacts partial VINs, and has to be testable without a network. It does not need OAuth, server-initiated sampling, or a plugin system in v1.

Clients do not care which language speaks MCP, as long as the transport is stdio or Streamable HTTP. Cursor documents both, for any language that can do stdio or HTTP ([Cursor MCP](https://cursor.com/docs/mcp)). The language choice is about contributors, evals, packaging, and hosting, not about whether Claude or VS Code can connect.

## What "the SDK" means in November 2026

The [2026-07-28 specification](https://blog.modelcontextprotocol.io/posts/2026-07-28/) made the protocol stateless. The `initialize` handshake and `Mcp-Session-Id` are retired. Server-to-client sampling and elicitation move to multi-round-trip requests. Roots, sampling, and logging are deprecated with at least a twelve-month window. The old HTTP+SSE transport is deprecated. List results can carry cache hints. The blog lists TypeScript, Python, Go, and C# as the Tier 1 SDKs that spoke that revision on the day it shipped, and says the Rust SDK supported it in beta at that moment.

Versions observed on 2026-11-22 from the public registries:

| SDK | Where | Version observed | Requirement observed |
| --- | --- | --- | --- |
| Official Python | PyPI `mcp` | 2.3.0 | `Requires-Python >=3.10` |
| Prefect FastMCP | PyPI `fastmcp` | 4.2.4 | `Requires-Python >=3.11` |
| Official TypeScript | npm `@modelcontextprotocol/sdk` | 1.32.2 | not re-read from its changelog |
| Official Go | `proxy.golang.org`, module `github.com/modelcontextprotocol/go-sdk` | v1.8.0 | Go's supported-release policy, per the repo README |
| Official Rust | crates.io `rmcp` | 3.11.0 (max stable) | tokio |

The Python docs at [py.sdk.modelcontextprotocol.io](https://py.sdk.modelcontextprotocol.io/) say the current line is v2 and that it needs Python 3.11 or newer. PyPI's metadata for 2.3.0 says `>=3.10`. Both were true of the pages we fetched. We would pin 3.12 anyway, so the disagreement does not change the choice. We did not line-by-line diff npm 1.32.2 or Go v1.8.0 against the spec. The July blog is the spec-coverage citation for the Tier 1 set. The [Go SDK README](https://github.com/modelcontextprotocol/go-sdk/) says v1.7.0 and later implement 2026-07-28, and v1.8.0 is past that. The [Rust SDK README](https://github.com/modelcontextprotocol/rust-sdk/) now says the crate implements 2026-07-28 and stays compatible with 2025-11-25. That is ahead of the July blog's "beta" label. We did not run either SDK.

The Python v2 server class is `MCPServer` in `mcp.server`. Tools, resources, and prompts are decorators. `mcp.run(transport="stdio")` is the default. `transport="streamable-http"` serves Starlette through uvicorn, default path `/mcp`. SSE still runs and the docs tell you not to build on it ([Running your server](https://py.sdk.modelcontextprotocol.io/run/)). Prompts are documented as user-chosen templates ([Prompts](https://py.sdk.modelcontextprotocol.io/servers/prompts/)). That is the whole surface v1 needs.

Prefect FastMCP 4 sits on that SDK. Its 4.0 notes describe stateless requests, tasks, auth, and gateway headers. Those are real features. They are also a second release train and a larger API for a server that, in v1, reads public JSON and writes shaped JSON. Taking it now means every contributor has to learn FastMCP's conventions on top of MCP's. Leave it as an option to revisit if we later need OAuth or tasks. Do not start there.

## Options

### Python, official SDK

Strengths:

- The eval and test story is the one this project is supposed to be known for. pytest, fixture files, and a local model runner are ordinary Python. Inspect AI talks to MCP servers from Python ([Inspect tools](https://inspect.aisi.org.uk/tools.html)).
- Flat files, caching, and redaction are short programs in this language. The investigations file is a 4 MB zip of tab-separated text. Pandas is unnecessary. The stdlib is enough.
- `uvx` is the same shape as `npx`: one command, no clone, an isolated environment. Contributors who already use `uv` get lockfiles and a fast install.
- The SDK covers tools, resources, prompts, stdio, and Streamable HTTP. That is spec coverage enough for v1. We should speak the 2025 protocol as well as 2026-07-28, because OpenCode still defaults to the legacy handshake and only opts into the new revision per server ([OpenCode MCP](https://opencode.ai/docs/mcp-servers/)). The Python SDK's compatibility with older clients was not executed in this research. **Unknown** until we run Inspector against a real build. The docs say the SDK speaks the standard transports, which is the claim we are relying on.

Costs:

- Not a single binary. A person without Python installs uv, or runs Docker.
- Cold start of a uvx environment is slower than a Go binary the first time, then fine.
- Hosting on Cloudflare Workers is not the natural path. That is acceptable, because v1 should not be hosted. See the hosting doc.

### TypeScript, official SDK

Strengths:

- Tier 1, and the language of the two closest public servers (see the roadmap). Tutorial readers expect `npx`.
- Node is already on the machines of people who install MCP servers from npm. VS Code's "add a command" flow uses `npx` in its own example ([VS Code MCP](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)).
- Streamable HTTP on a small Node host is a well-worn path if we ever host.

Costs:

- The differentiator of this project is the eval harness and the data-quality contract. Python is where that harness wants to live. Doing both the server and the evals in TypeScript is possible (promptfoo is a Node tool) and it gives up Inspect and the boring pytest style for the fixture gate.
- Another TypeScript NHTSA server does not help the portfolio. The README would spend its first screen explaining how it is not cyanheads' server.
- We did not audit npm 1.32.2 feature by feature. Spec coverage is "Tier 1 as of July 2026," not a checklist we ticked.

Choose TypeScript if Zach wants the install story to be `npx` and nothing else, and is willing to write the golden-set gate in Node.

### Go, official SDK

Strengths:

- Tier 1. v1.8.0 is current. The README's support table says v1.7.0 and later cover 2026-07-28, with earlier revisions still accepted, and with roots, sampling, and logging kept during the deprecation window.
- A static binary is the best "download and run" artifact. No uv, no Node, no Docker required. Cross-compile in CI.
- A long-running local process and a small Fly.io or Cloud Run container are both easy. Memory stays low, which matters if we later memory-map the investigations file.

Costs:

- The eval ecosystem is the weak point. There is no Inspect equivalent we found that we would want to adopt. The CI gate would be Go tests, which is fine for contracts and weak for "run my model against the golden set" unless the eval runner stays a separate Python tool. A split repo (Go server, Python evals) is a real option and also a real tax.
- Contributors who are comfortable shaping messy JSON and writing narrative tests will move slower. This codebase will be more parsing and policy than algorithms.
- Table-driven tests are good. Freezing HTTP fixtures is fine. The day-to-day of redaction rules and token budgets is just more verbose.

Choose Go if the primary user is someone who will not install a language toolchain, and the eval story can live beside the server rather than in it.

### Rust, official SDK (`rmcp`)

Strengths:

- The current README describes 2026-07-28 support and compatibility back to 2025-11-25. crates.io showed stable 3.11.0.
- A static binary, same operational story as Go, with a stricter type system around the protocol.

Costs:

- Steepest contributor curve of the four, for a program whose hard part is policy (what to omit, what to redact, what a golden answer looks like) rather than throughput.
- We did not survey Rust eval tooling. It would not be the reason to pick Rust.
- The July spec post still called Rust beta. The README has moved on. A portfolio project does not need to live on that edge either way.

Rust is credible and not recommended.

### Others

C# is Tier 1 per the July post. We did not evaluate it. Java was not researched. Neither has an advantage for this dataset or for local MCP install stories that Python, TypeScript, and Go do not already cover.

## Comparison

|  | Python official | TypeScript official | Go official | Rust official |
| --- | --- | --- | --- | --- |
| Spec standing, July 2026 blog | Tier 1 | Tier 1 | Tier 1 | Beta at that date; README now claims the revision |
| Tools, resources, prompts | Documented on the Python SDK site | Not re-audited here | README says the SDK aims at the full spec | README claims the revision |
| Local install for a user | `uvx`, or Docker | `npx`, or Docker | One binary, or Docker | One binary, or Docker |
| Local install for a contributor | `uv sync`, pytest | `npm install`, a Node test runner | Go toolchain, `go test` | Rust toolchain |
| Eval ecosystem | pytest, Inspect, optional promptfoo | promptfoo fits naturally; pytest does not | Contract tests in Go; model evals want another language | Not surveyed |
| Package registry | PyPI | npm | GitHub release plus `go install` | crates.io plus a binary |
| Client compatibility | Same as the others, via stdio and Streamable HTTP | Same | Same | Same |
| Hosting fit | A small container. Not Workers. | Container or Workers | Container, small image | Container, small image |
| Risk we actually carry | SDK v2 is young. Pin it. | Looking like a clone of existing servers | Eval story splits in two | Contributor friction |

Client notes, so the "same" cell is sourced:

- Cursor: stdio, SSE, and Streamable HTTP ([docs](https://cursor.com/docs/mcp)).
- VS Code: command (stdio) or HTTP, user or workspace config ([docs](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)).
- OpenCode: local command or remote Streamable HTTP. Default protocol mode is still the legacy handshake, with `protocol: "2026-07-28"` or `"auto"` as an opt-in ([docs](https://opencode.ai/docs/mcp-servers/)).
- Claude Code: `claude mcp add` for stdio and HTTP ([docs](https://code.claude.com/docs/en/mcp)).
- Claude Desktop: a JSON `mcpServers` config is the usual integration. The file path was not re-read from an Anthropic page in this pass. **Unverified** here. The documentation plan flags it as a page to confirm against Anthropic before the user guide is published.

## Consequences

- v1 depends on `mcp` and a small HTTP client. No FastMCP, no web framework beyond what the SDK pulls in for the optional HTTP transport.
- The package name is `glovebox-mcp`. PyPI had no project by that name on 2026-11-22. GitHub already has an unrelated `segentic-lab/glovebox-mcp`. This repo does not publish.
- CI installs with uv, runs pytest, and does not call NHTSA or a model. See the evals doc.
- Docker is a release artifact, not the development loop.
- We pin the SDK and re-read its transport notes when implementation starts, because 2.x is new and the 2026-07-28 migration is the kind of change that breaks idle clients.
- If a later version of the server needs OAuth for a hosted endpoint, that is the moment to reconsider FastMCP or a small hand-rolled auth layer. It is not a reason to take the dependency now.

## Open point for Zach

Confirm Python. If the answer is "I want a single binary more than I want the evals in the same language," switch the ADR to Go before any code is written. If the answer is "npx, and I will live with looking similar to the TypeScript servers," switch to TypeScript. Both are defensible. Starting in one and porting later is not, because the eval fixtures and the tool schemas will calcify around the first language.
