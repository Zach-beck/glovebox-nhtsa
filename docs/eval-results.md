# Eval results

I keep two measurements apart. Only the first one is the CI signal.

## CI gate

Offline pytest. Frozen fixtures. No network. No model key.

| Item | Result |
| --- | --- |
| Command | `uv run pytest` |
| Tests | 29 passed, 0 failed |
| Scripted cases inside that suite | 40, all passing |
| What a failure means | A shaper, a contract, a token budget, or the scorer itself broke |

Re-run it with `uv run pytest`. GitHub Actions runs the same command from `.github/workflows/ci.yml`, then `uv run python evals/local.py`, which prints `status: skipped` when no key is set. I have not watched a remote Actions log for this tree.

`uv run python evals/local.py` with `OPENAI_API_KEY` in `.env` only asks the model to name a tool. That is a thinner check than the agent run below, and I have not executed it against OpenAI.

## Agent-run, an upper bound, not the gate

On 2026-11-22 I ran all 40 golden cases in this Cursor cloud session (Grok 4.7) and scored the transcripts with `evals/score.py`.

| Metric | Passed | Total | Rate |
| --- | --- | --- | --- |
| Tool selection | 40 | 40 | 1.0 |
| Argument correctness | 40 | 40 | 1.0 |
| Field accuracy | 40 | 40 | 1.0 |
| Faithfulness | 40 | 40 | 1.0 |

Failures under those rules: none.

I do not want you to read 40/40 as independent accuracy. I wrote `tests/golden_cases.py`, then I answered it in the same project. Before I called the tools I had already seen the expected tool name, the arguments, and the phrase lists. Tool selection and argument correctness are an upper bound. The answers were written after the tool JSON came back, and they quote that JSON, but I also knew which phrases the scorer forbids. A model that had never seen the key would score lower, or at least I have no evidence it would not.

The calls used frozen fixtures through `scripts/run_stdio_calls.py`, not live NHTSA. Complaint rows, the investigations sample, the fake model name `NO-SUCH`, and `OtherEngineInfo` only exist in those fixtures. Scoring them live would mix NHTSA changes into a model score. I wrote `.cursor/mcp.json`, and this session's tool list still did not show Glovebox, so I used the stdio client.

Transcripts: [../evals/runs/2026-11-22-cursor-agent/](../evals/runs/2026-11-22-cursor-agent/).

A few cases are not ordinary questions. They tell the model to send an invalid mix (campaign number and vehicle in one `get_recalls` call, ratings with both a vehicle id and a make, an investigation search with no filter). Passing means the model obeyed and reported `invalid_arguments`.

## Blinded live runs (Nov 21, 2026), pre-fix

Three agents ran all 40 golden questions against live NHTSA (fixtures unset) before `fix/eval-findings`. Branches hold transcripts and reports.

| Model | Full pass | Tool | Args | Fields | Faith | Main causes |
| --- | --- | --- | --- | --- | --- | --- |
| Composer 2.5 | 31/40 | 40/40 | 39/40 | 31/40 | 39/40 | HTTP 400 empty body mapped to `upstream_unavailable`; out-of-scope exact phrases missed; investigations default fixture file in `run_stdio_calls` |
| Grok 4.5 | 29/40 | 40/40 | 39/40 | 29/40 | 39/40 | Same 400 mapping; live investigations drift; component `brake` vs `BRAKES` |
| Grok 4.6 | 28/40 | 40/40 | 39/40 | 30/40 | 37/40 | Same 400 mapping; faithfulness on `invalid_vin` wording and rejected campaign ids |

The unblinded fixture run in this repo remains **40/40** on the same scorer. That is an upper bound, not a live claim.

Post-fix rerun (one cloud agent session, live NHTSA): **35/40** full pass (field accuracy 35/40; tool/args/faithfulness 40/40). Report: `evals/runs/2026-11-21-blind-composer-2.5-postfix/report.md`.

Remaining field misses: three `fixture_only` complaint or investigation cases scored against live data, plus live decode lacking fixture-only `OtherEngineInfo`. Out-of-scope and HTTP-400 spelling cases improved versus the pre-fix 31/40 Composer run.

## Planned blinded run

After server fixes, re-score blinded live runs with the same `evals/score.py` and treat `eval_mode: fixture_only` cases separately when NHTSA drift is expected. The CI signal remains offline pytest on frozen fixtures.

## Golden set categories

Forty cases. Each one is aimed at a way NHTSA data misleads a model.

| Category | What I am testing |
| --- | --- |
| `decode_partial` | NHTSA's sample VIN `5UXWX7C5*BA` returns HTTP 200 and error code 6, and still names a 2011 BMW X3. Spaces inside the VIN are removed. |
| `decode_invalid` | `VIN!`, a blank string, an 18-character string, and `ABC` (codes 6, 7, and 11, manufacturer not registered). None of these should become a car. |
| `decode_check_digit` | Code 1 still returns a Chevrolet HHR. The warning stays visible. |
| `missing_means_unknown` | A field that is absent is not "this car has no side airbags." |
| `not_applicable_dropped` | `Not Applicable` bus and trailer fields are removed. Plant city Munich remains. The raw-filled view keeps `OtherEngineInfo` and still drops sentinels. |
| `recalls_hit` | 2012 Acura RDX has two campaigns, `19V182000` and `16V061000`. Dates are day/month/year, so `06/03/2019` becomes `2019-03-06`, and the tool says that reading is ambiguous. `park_outside` is false. A campaign lookup includes `potential_units`. 2011 BMW X3 returns `17V683000`. |
| `recalls_spelling` | `BMW` `NO-SUCH` returns zero rows and a notice that this is not proof nothing was filed. Make alone, or a campaign number mixed with a vehicle, is `invalid_arguments`. |
| `recalls_not_repair_status` | Asking whether the 2012 RDX recall was repaired must not become "the repair was done." |
| `complaints_summary` | 2011 BMW X3 fixture counts, an engine filter, a brake filter that matches nothing, and a fire count on the 2012 RDX. Counts, not stories. |
| `complaints_redaction` | The answer must not contain the fixture's fake VIN, email, or narrative, and must not echo `"vin"` or `"summary"` keys. |
| `ratings_not_rated` | Vehicle 7520 is `Not Rated`, not five stars and not zero stars. 2011 BMW X3 has no NCAP row under that string. |
| `ratings_variant` | 2013 Acura RDX has two variants, ids 7520 and 7731. The model must not collapse them. Passing both a vehicle id and a make is `invalid_arguments`. |
| `profile_partial` | A full profile keeps recalls when ratings are empty or unavailable. No identity means `invalid_arguments`. |
| `investigation_link` | The sample file links `EA15001` to campaign `17V683000` and `PE14001` to the 2012 RDX. A search with no filter is `invalid_arguments`. The live zip has tens of thousands of rows for `EA15001`. This case uses the small fixture. |
| `out_of_scope` | Title history, fuel economy, and per-VIN repair completion are not in this server. No tool call. |

## Live smoke, separate from both scores

I called NHTSA directly on 2026-11-22 with `scripts/live_smoke.py`. That is not CI and not the agent-run score.

| Call | Result |
| --- | --- |
| Decode `5UXWX7C5*BA`, model year 2011 | error code 6, BMW X3 2011 |
| Recalls, 2012 Acura RDX | count 2, first campaign `19V182000` |
| Ratings vehicle 7520 | `Not Rated`, 2013 Acura RDX SUV FWD |
| Investigations `EA15001` on the real zip | 71,004 product rows, 20 returned |

The RDX recall fixture matches that live pair. The complaint and investigation cases do not.
