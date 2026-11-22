# Eval results

Numbers from the build on 2026-11-22. The method is [evals.md](evals.md). Two different measurements are listed, and they are not one score.

## CI gate

Deterministic pytest, no network, no model key.

| Item | Result |
| --- | --- |
| Tests | 29 passed, 0 failed |
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

The 2012 Acura RDX recall fixture now has both campaigns from the 2026-11-22 live fetch. Other fixtures are still reduced or synthetic. They are not a live mirror.

## Agent-run eval, not the CI gate

Date: 2026-11-22. Model: Cursor Grok 4.7, this cloud agent session. Data: frozen fixtures, through the stdio client in `scripts/run_stdio_calls.py`. `.cursor/mcp.json` was written, and this session's tool list did not pick Glovebox up. Transcripts: `evals/runs/2026-11-22-cursor-agent/`.

This run is not blinded. The same agent wrote the golden cases and read the expected tools, arguments, and phrase lists again before answering. Tool selection and argument scores are an upper bound. Answers were written from the tool JSON after the calls returned.

| Metric | Passed | Total | Rate |
| --- | --- | --- | --- |
| Tool selection | 40 | 40 | 1.0 |
| Argument correctness | 40 | 40 | 1.0 |
| Field accuracy | 40 | 40 | 1.0 |
| Faithfulness | 40 | 40 | 1.0 |

Failures: none under those rules. A fresh session that sees only the question and the tool list is the blinded rerun. Cases that tell the model to send an invalid argument mix (`recalls_reject_mixed_arguments`, `ratings_reject_mixed_arguments`, and the empty-filter cases) are instructions to provoke a server error, not ordinary user questions.
