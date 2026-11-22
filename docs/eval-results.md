# Eval results

Numbers from the build on 2026-11-22. The method is [evals.md](evals.md). Two different measurements are listed, and they are not one score.

## CI gate

Deterministic pytest, no network, no model key.

| Item | Result |
| --- | --- |
| Tests | 26 passed, 0 failed |
| Scripted traces | 40 cases, all passing inside that suite |
| Categories covered | decode (partial, invalid, check digit, missing means unknown, Not Applicable dropped), recalls (hit, spelling, not repair status), complaints (summary and redaction), ratings (Not Rated and variants), profile partial failure, investigations, out of scope |
| Token budgets | All seven shaped samples and the instruction block are under the character estimate (length divided by 4) |
| Model calls | None |

`uv run python evals/local.py` with no key prints `status: skipped` and exits 0. That skip is what CI runs after pytest. It is not an accuracy number.

Re-run with `uv run pytest`. A future GitHub Actions run uses `.github/workflows/ci.yml`. This environment did not wait on a remote CI result.

## Maintainer model run

Not run against a provider. No key was in the environment. `evals/local.py` exits 0 with `status: skipped` in that case.

If `OPENAI_API_KEY` is set, the runner sends each scripted case id to OpenAI and scores whether the reply names the expected tool. That HTTP path was checked with a fake response in `tests/test_eval_openai_fake.py`. It was not executed against OpenAI, so there is no live tool-selection rate to publish. An `ANTHROPIC_API_KEY` without an OpenAI key still skips. Do not read the 40 scripted traces as a model score. They check a canned caller against frozen fixtures.

## Live smoke, separate from the gate

A manual script, `scripts/live_smoke.py`, called NHTSA on 2026-11-22 after the tests. It is not part of CI.

| Call | Result |
| --- | --- |
| Decode `5UXWX7C5*BA` model year 2011 | error code 6, BMW X3 2011 |
| Recalls for Acura RDX 2012 | count 2, first campaign `19V182000` |
| Ratings vehicle 7520 | `Not Rated`, 2013 Acura RDX SUV FWD |
| Investigations id `EA15001` from the local zip | 71,004 matching product rows, 20 returned |

The fixture for Acura RDX recalls contains one campaign, not the live count of 2. Fixtures are reduced on purpose. They are not a mirror of the live feed.
