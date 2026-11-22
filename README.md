# Vehicle-specs agent

A local [Model Context Protocol](https://modelcontextprotocol.io) server over the National Highway Traffic Safety Administration's public vehicle data. It is meant to be downloaded and run on your own machine, against NHTSA's public endpoints and downloadable files. No account, no API key, and no hosted relay.

This repository is the research and design set. There is no server implementation yet. Zacharias Beck will review these documents before any build.

The project is not affiliated with, endorsed by, or published by NHTSA or the U.S. Department of Transportation. NHTSA's own terms disclaim accuracy and say the site is public information that may be copied. See [docs/research/rate-limits-and-terms.md](docs/research/rate-limits-and-terms.md).

## What it is for

Ask a normal question about a vehicle and get a short, sourced profile: what the VIN decodes to, which recall campaigns are filed against that model, a complaint summary, and the NCAP star rating when one exists. The server shapes those answers so they fit an LLM's context, and it says when a field is unknown instead of letting the model invent it.

That shaping work is Context Engineering. The server's job is to decide what context the model sees.

## Read these first

| Document | What it decides |
| --- | --- |
| [docs/research/nhtsa-data.md](docs/research/nhtsa-data.md) | Which public datasets exist, what we called, and the quirks |
| [docs/research/rate-limits-and-terms.md](docs/research/rate-limits-and-terms.md) | Documented limits versus what a polite test actually saw |
| [docs/decisions/0001-language-and-runtime.md](docs/decisions/0001-language-and-runtime.md) | Language and SDK recommendation |
| [docs/architecture.md](docs/architecture.md) | Tools, resources, prompts, cache, errors, transports |
| [docs/evals.md](docs/evals.md) | Golden set, metrics, local runs, and the CI gate |
| [docs/hosting.md](docs/hosting.md) | Local stdio for v1, and why a public endpoint is a bad default |
| [docs/roadmap.md](docs/roadmap.md) | Phases, acceptance criteria, and how this differs from existing servers |
| [docs/documentation-plan.md](docs/documentation-plan.md) | The end-user docs to write once the server exists |

Numbers from the live probe are in [docs/research/spikes/2026-11-22-probe.json](docs/research/spikes/2026-11-22-probe.json).

## Recommendation in one paragraph

Build it in Python on the official MCP Python SDK, distribute it with `uvx`, and keep v1 local over stdio. Expose a few shaped tools, not a pass-through of every vPIC route. Gate CI on frozen fixtures and contract tests, and run model-judged evals only on a machine that has its own key in an untracked `.env`. Do not publish an open internet endpoint in front of NHTSA.

## Status

Design only. Nothing here calls NHTSA when you clone the repo, because there is no program to run yet.
