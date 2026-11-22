# Documentation plan

The user-facing pages below are written. This file remains the map. The design set linked from the README is the research behind them.

Write them in the repo as Markdown. Keep the same rules as the design set: plain language, no em dashes, Context Engineering when we mean how context is shaped, and a citation or an "unverified" mark on anything we say about NHTSA.

## 1. Quickstart

One page, at the top of the README once the server exists.

- What the server does, in four lines.
- The install line, expected to be `uvx` once the package name is chosen. A Docker one-liner under it.
- The shortest Cursor config that starts stdio.
- One question to ask the model, and what a good answer looks like (a profile with a source line, an error code if the VIN is partial, and no claim that a recall was repaired).
- The sentence that this is not an official NHTSA tool, with a link to NHTSA's terms.

Do not make the quickstart teach MCP. Link out.

## 2. Client setup, one page per client

Each page is a config snippet, where the file lives, and the one restart or reload the client needs. Confirm every path against that client's current docs before publishing. As of this design:

| Client | Page should cite | Notes already known |
| --- | --- | --- |
| Cursor | [Cursor MCP docs](https://cursor.com/docs/mcp) | `mcp.json`, project or global. stdio via `command` and `args`. `envFile` works for stdio. |
| VS Code | [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/customization/mcp-servers) | Command (stdio) or HTTP. Workspace `.mcp.json` when sharing with a team. Do not put keys in the shared file. |
| OpenCode | [OpenCode MCP docs](https://opencode.ai/docs/mcp-servers/) | Local command array under `mcp.servers`. Remote URLs use Streamable HTTP. Default protocol mode is legacy. Document the `protocol` setting if our server is new-spec only. |
| Claude Code | [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) | `claude mcp add --transport stdio`. |
| Claude Desktop | Confirm against Anthropic's current page before writing the path. | A JSON `mcpServers` block is the usual shape. The on-disk path was not verified from an Anthropic page in the design pass. |

Also a short "which transport" note: stdio for a personal machine, Streamable HTTP only on localhost unless the hosting doc's later phase has been built. SSE is not offered.

## 3. Tool reference

Generated as far as possible from the server's own schemas, then edited so each tool has:

- What question it answers.
- Arguments, including which model-year spellings are fragile.
- A trimmed example of the JSON a model actually sees, not the raw NHTSA body.
- The failure cases: non-zero VIN `ErrorCode`, empty recalls that may be a spelling miss, `Not Rated`, a section of the profile whose upstream call failed.
- What the tool will not say. Repair status, title history, and "this equipment is absent" are the three to write out.

Keep the reference next to a separate "data sources" page that links to [research/nhtsa-data.md](research/nhtsa-data.md) and states the refresh expectations (live cache TTLs, investigations zip, optional Postgres).

## 4. Eval results

A page, linked from the README badge or a small table, produced by the eval runner.

- The golden-set version and the fixture fetch date.
- Deterministic CI result: pass or fail, commit SHA. This one is generated in GitHub Actions and can be a badge.
- The latest local model run: model name, date, tool-selection rate, argument rate, faithfulness notes, token size of the shaped profile. This one is not a CI badge, because CI has no model key. Label it as a maintainer run.
- A link to [evals.md](evals.md) for the method, so the numbers have a definition.

Do not publish a single "accuracy" number that mixes these.

## 5. Contributing

- How to run the contract tests with no network and no key.
- How to add a golden case: capture a fixture, redact it, name the category, update the expected tool call.
- How to refresh fixtures when NHTSA changes a field, and who is allowed to edit a frozen file (a human, in a PR, with the fetch date bumped).
- The clean-room rule: public NHTSA docs and public data only. No employer code, no copied server implementations. Read other NHTSA MCP servers for behavior if you must, and do not paste their code.
- `.env` stays untracked. `.env.example` lists names.

## 6. FAQ

Questions the design already knows people will ask:

- Does this tell me if my car's recall has been fixed? No.
- Why did a valid-looking VIN come back with an error code? Because HTTP 200 is not a decode. Explain code 1, 6, and 400 with the strings NHTSA returns.
- Why are there no star ratings? `Not Rated` is a value. Also, the model string may not match NCAP.
- Why is a complaint count smaller than the NHTSA website? Say what we know about spelling, and do not invent a cause when we have not measured it.
- Can I run this offline? What the optional indexes cover, and what still needs the network.
- Is there a rate limit? Link to the rate-limit doc's documented-versus-observed split. Do not quote a number we did not see.
- Where do model keys go? `.env`, local evals only.

## 7. Security and privacy page

Short. Point at the architecture's security section. Repeat: complaint VINs and narratives are not returned by default, the HTTP transport binds to localhost, logs do not store complaint bodies, and a public open proxy is out of scope for v1.

## Order to write them

Quickstart and the Cursor page ship with the first runnable server. The other client pages, the tool reference, and the FAQ ship with the public v1. The eval-results page ships as soon as the first maintainer run exists, even if the numbers are modest, as long as the method is linked.
