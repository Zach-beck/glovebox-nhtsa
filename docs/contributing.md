# Contributing

Glovebox is clean-room. Use NHTSA's public APIs, public files, and public docs. Do not copy another MCP server's code. Do not bring in employer systems, private schemas, or private data.

## Tests

```bash
uv sync
uv run pytest
```

The suite uses `tests/fixtures`. It does not call NHTSA. A socket opened during the missing-fixture test fails the run.

What the tests lock:

- Shaper contracts: dates, `Not Applicable`, complaint redaction, empty recall notice.
- Token budgets: each shaped sample stays under the character estimate in `glovebox_nhtsa.shaping.BUDGETS` (characters divided by 4).
- Scripted traces: `tests/golden_cases.py`. A canned caller checks `must_include` and `must_not_include`. That is not a model score.
- stdio: an MCP client in legacy mode lists the tools and calls `decode_vin` and `vehicle_profile`.

`uv run python evals/local.py` skips when no key is set. CI runs that command and expects the skip. Do not add a provider key to GitHub Actions.

## Adding a case

1. Put a frozen JSON file in `tests/fixtures`. The file has `_request` (`name` and `params` exactly as the service sends them) and `body` (the upstream JSON).
2. Strip complaint `summary` and `vin` unless the case exists to prove those fields are removed. If you keep them, use obvious fake values, never a real narrative.
3. Add a dict to `tests/golden_cases.py` with `must_include` strings copied from the shaped result.
4. If you change a fixture, say so in the pull request. Do not loosen an assertion to hide an NHTSA content change.

## Refreshing live data

A human runs `scripts/live_smoke.py` when they want to see current NHTSA responses. That script is not part of CI. Copy a redacted fragment into `tests/fixtures` only after you have read it.

## Secrets

`.env` is gitignored. `.env.example` lists names and nothing else. Do not print keys. Do not log complaint bodies or VINs at info level.
