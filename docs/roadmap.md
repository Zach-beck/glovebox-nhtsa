# Roadmap

Phased build, after Zach accepts the design. No dates. The first sketch assumed Python, FastMCP, six vPIC tools, a golden set, and a CI gate. This roadmap keeps Python, drops FastMCP as a dependency, replaces the six tools with a smaller shaped set, and splits the CI gate from the model eval. The reasoning is in the ADR, the architecture, and the evals doc.

The attached first-pass plan was not in the workspace when this set was written. The hypothesis above is the one stated in the task, not a file we could quote.

## Why this is worth building

A person with a VIN, or a year, make, and model, should be able to ask one question and get a short, sourced profile: specs, recalls, a complaint summary, stars, and any open investigation. NHTSA already publishes every piece. The pieces disagree with each other in ways that make a raw API wrap answer confidently and wrongly.

We watched that happen on public calls. A partial VIN decoded as a 2011 BMW X3 and also returned error code 6. The recalls API had four campaigns for BMW X3 2011. The products model list for BMW 2011 did not contain X3. The NCAP call for that string returned zero rows. The safety-ratings example in NHTSA's own documentation, vehicle 7520, is `Not Rated`. A 2018 Civic complaint query returned 596 rows and 577 KB, including an 11-character VIN on each row. A thin client that hands those bodies to a model will produce long, leaky, oversure answers.

That is the product: a server that already did the careful part, plus a public eval that shows where the model still goes wrong. Context Engineering is the method. The golden set is the evidence.

## What already exists

Read on 2026-11-22 from public READMEs only. No code was copied, and no code was read. Behavior described below is what those READMEs claim.

| Project | What the README says it is | What it does not give us |
| --- | --- | --- |
| [viguza/nhtsa-mcp-server](https://github.com/viguza/nhtsa-mcp-server) | TypeScript. A wide 1:1 wrap of vPIC: several decode shapes, makes, models, manufacturers, parts, variables, Canadian specs. Docker. HTTP and the older SSE transport. | No recalls, complaints, ratings, or investigations in the tool list we saw. No eval story in the portion read. |
| [NextLevelManagementAdvisors/vin-mcp](https://github.com/NextLevelManagementAdvisors/vin-mcp) | Python FastMCP. VIN decode, makes, models, types, WMI. stdio locally. A hosted Streamable HTTP endpoint behind OAuth, with the README saying the gate exists so they are not an open relay. AGPL-3.0, plus a commercial license. Specs only. | No safety data. AGPL is a harder default than this project should pick for a portfolio sample. The license is an open decision for us, and MIT is the recommendation. |
| [taimoorgit/vin-lookup-mcp](https://github.com/taimoorgit/vin-lookup-mcp) | Python, described as the official SDK via FastMCP. Two tools: 17-character decode through the extended flat endpoint, and Canadian specs. `uv run`. | Two tools, no safety profile, rejects partial VINs that NHTSA itself accepts. |
| [pipeworx-io/mcp-nhtsa](https://github.com/pipeworx-io/mcp-nhtsa) | A pack inside a commercial MCP gateway. The README lists recalls, complaints, investigations, NCAP, VIN decode, TSBs, FARS aggregates, and fueleconomy.gov. The npm package is a stdio bridge to their gateway, with a daily cap (50 anonymous, 200 with a free key, as the README states). They say the live crash API returned an Akamai 403 on 2026-10-12, so FARS in that pack comes from bulk files. | Not a local server over NHTSA. Fuel economy is a different agency. The README's "recall by VIN" claim was not checked against their code. NHTSA's documented recalls API is not keyed by VIN. |
| [cyanheads/nhtsa-vehicle-safety-mcp-server](https://github.com/cyanheads/nhtsa-vehicle-safety-mcp-server) | The closest. TypeScript, seven tools, a combined safety profile, recalls, complaint summaries, ratings, VIN decode, investigations from `FLAT_INV.zip`, and a lookup that knows model strings differ by dataset. stdio, Streamable HTTP, Docker, npm, and a public hosted URL. The README is careful about `Not Rated`, partial failure, and empty results. | No eval suite is described. Complaint narratives are still returned, paged. A public unauthenticated host is part of the pitch. We should not reimplement this tool for tool and stop. |

Also visible in search, not studied beyond the description: multi-agency recall servers such as `santex85/us-recalls-mcp` and `G-ojies/recall-check`. They are recall products, not vehicle profiles.

The honest gap: cyanheads already built the combined safety profile, and viguza already built the wide vPIC wrap. A sixth vPIC pass-through would be noise. The room left is a server whose context is small and redacted, whose failure rules are tested by a frozen golden set, and whose default is local. We can learn the failure modes those READMEs name (model-string mismatch, Not Rated, partial outages, open relays) without taking their schemas, their names, or their code.

## MVP

A local process a reviewer can run.

In:

- `decode_vin`, `get_recalls`, `summarize_complaints`, `get_safety_ratings`, `vehicle_profile`.
- Shaper rules from the architecture: drop empty and `Not Applicable`, ISO dates, complaint summary without VIN or narrative, `section_status`, `Not Rated` left as words.
- In-memory cache and a two-deep host pool. Disk cache can wait if it slips.
- stdio only.
- pytest contract tests on checked-in fixtures. No live calls in CI.
- README quickstart for Cursor, plus the disclaimer.

Out: investigations, prompts, resources, Docker, HTTP, offline Postgres, the local model runner.

Acceptance:

- `uv run` starts the server on stdio, and MCP Inspector lists the five tools.
- A scripted `vehicle_profile` for the documented partial BMW VIN returns the warning code 6, the X3 identity, and a recalls section, from fixtures in CI and from the network only when a human passes `--live`.
- The Civic-sized complaint fixture never appears in a tool result. The summary does.
- CI is green with no secrets and no network.
- A live smoke, run by hand once, records the same error code and the same "do not treat empty as absent" behavior against current NHTSA. The transcript of that smoke is a fixture refresh, not a permanent live test.

## v1 public

The version someone else can install.

In, on top of the MVP:

- `search_investigations` on a local copy of `FLAT_INV.zip`, refreshed by `Last-Modified`.
- `list_model_names`, with the products list marked incomplete.
- The three prompts, the `nhtsa://about` and `nhtsa://coverage` resources, and server instructions.
- Disk cache and the backoff path.
- Docker image, stdio entrypoint.
- Localhost Streamable HTTP, off by default.
- The local model eval runner, and a committed results table from one maintainer run.
- Client pages from the documentation plan, after each client's docs are re-read.
- PyPI publishing only if Zach asks. The package name is an open decision.

Acceptance:

- A clean machine with uv can run the server from the README without cloning, or the Docker line works. One of those is the promise. Both is the goal.
- Inspector against Claude Desktop or Cursor, whichever Zach uses, completes `buyer_brief` on a VIN and does not claim a repair. This is a manual test we write down.
- OpenCode either connects with the default protocol mode or the README shows the one setting it needs. We do not know which until the SDK is pinned. The task is to find out and document it.
- Deterministic CI at 100 percent.
- The README table from a local model run shows tool selection, arguments, faithfulness, and token estimate, and says it is not the CI gate.
- The investigations tool answers from the zip with the network blocked, after the file has been downloaded once.

## Later

- Optional vPIC Postgres for offline decode. Document the restore. Do not require it.
- Offline recalls from the flat files, for the same offline flag.
- Manufacturer communications as a separate tool over the CSV chunks, returning document id, date, type, and a short summary.
- Authenticated hosting, if there is a real user for it. See the hosting doc. Not an open URL.
- A crash-stats tool only with a written caveat that FARS is fatal crashes and is not a safety rate. Default is still no.
- Fuel economy stays out. It is not NHTSA.

## Acceptance we will not fake

- We will not claim per-VIN repair status.
- We will not claim a numeric rate limit we did not see.
- We will not mark CI green because a judge model was in a good mood.
- We will not publish a hosted demo that proxies anonymous traffic at NHTSA.

## Decisions, accepted

1. **Language.** Python 3.12 and the official MCP SDK. `uv` for a checkout. `uvx` after a future publish. Docker is optional and local.
2. **Complaints.** Counts and component totals only. No narratives and no VIN field.
3. **Name and license.** Product name Glovebox. Repository, image, PyPI distribution, and command are `glovebox-nhtsa`, because `glovebox-mcp` is the unrelated segentic-lab project. MIT. PyPI returned 404 for `glovebox-nhtsa` on 2026-11-22, and a GitHub name search found no such repository. Nothing was published.
4. **Offline data.** Investigations from `FLAT_INV.zip` only. No Postgres. The zip is small. The text inside is hundreds of megabytes, so the loader indexes the short columns.
