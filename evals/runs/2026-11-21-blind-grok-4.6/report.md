# Blinded agent-run eval (Grok 4.6)

This is an agent-run measurement, not the CI gate.

- Date: 2026-11-22
- Model: Cursor Grok 4.6 (this cloud agent session)
- Branch: `evals/blind-grok-4.6`
- Data: live NHTSA APIs via `scripts/run_stdio_calls.py` (`GLOVEBOX_FIXTURES` empty, live `FLAT_INV.zip`)
- Blinding: questions, ids, and categories only until `answers.jsonl` was written
- Transcript: `evals/runs/2026-11-21-blind-grok-4.6/answers.jsonl`
- Scorer: `evals/score.py` against `tests/golden_cases.py`

## Score

**28/40** cases passed all four scorer metrics.

| Metric | Passed | Total | Rate |
| --- | --- | --- | --- |
| Tool selection | 40 | 40 | 1.000 |
| Argument correctness | 39 | 40 | 0.975 |
| Field accuracy | 30 | 40 | 0.750 |
| Faithfulness | 37 | 40 | 0.925 |
| All four metrics | 28 | 40 | 0.700 |

`uv run pytest`: **29 passed, 0 failed** (1.24s). Offline fixtures, no network, no model key.

The 2026-11-22 unblinded Grok 4.7 run scored 40/40 against frozen fixtures. This live blinded run is a different measurement.

## Category breakdown

| Category | All-pass | n | Notes |
| --- | --- | --- | --- |
| decode_partial | 3 | 3 | |
| decode_invalid | 4 | 4 | |
| decode_check_digit | 0 | 1 | phrase leak in the answer |
| missing_means_unknown | 1 | 1 | live decode now lists `airbags_side` |
| not_applicable_dropped | 1 | 2 | fixture-only `OtherEngineInfo` |
| recalls_hit | 6 | 6 | live RDX pair still matches |
| recalls_spelling | 2 | 4 | live HTTP 400; campaign restated after reject |
| recalls_not_repair_status | 1 | 1 | |
| complaints_summary | 1 | 4 | live X3 complaints 400; one argument miss |
| complaints_redaction | 0 | 1 | same X3 400, so the shaped note is missing |
| ratings_not_rated | 2 | 2 | |
| ratings_variant | 2 | 2 | |
| profile_partial | 3 | 3 | live profile kept recalls when complaints failed |
| investigation_link | 1 | 3 | live zip is not the frozen sample |
| out_of_scope | 1 | 3 | exact-phrase misses on fuel and repair |

## Failures

### Model mistake

1. `decode_check_digit` (faithfulness). Tool named a Chevrolet HHR and kept the check-digit warning. The answer said the result was "not marked invalid_vin", which contains the forbidden substring.
2. `out_of_scope_fuel` (field accuracy on the answer). No tool, correctly. Missed the exact string `does not have fuel economy`.
3. `out_of_scope_repair` (field accuracy on the answer). No tool, correctly. Missed the exact string `does not show repair completion`.
4. `recalls_reject_mixed_arguments` (faithfulness). Tool returned `invalid_arguments`. The answer repeated campaign `19V182000` from the prompt. The scorer treats that as an invented campaign because it is not in the tool JSON.
5. `complaints_unknown_component_is_zero` (argument correctness). Passed `component=brake`. Golden arguments use `BRAKES`.
6. `decode_raw_filled_drops_sentinels` (faithfulness half). The answer used the words `Not Applicable` while saying sentinels were dropped.

### Server bug (suspected)

1. `recalls_spelling_miss`. Live NHTSA returned HTTP 400 for `BMW` / `NO-SUCH` / `2011`. `LiveBackend.fetch` raises `upstream_unavailable` for any status `>= 400` other than 429/503/403-auth. The spelling notice (`not proof`) is only attached when a recalls body shapes to `count: 0`. Fixtures froze that empty body. A 400 for an unknown model should probably be treated as an empty list plus the spelling notice, not as an upstream outage.

The same mapping is why the live 2011 BMW X3 complaints cases never produce a shaped summary:

2. `complaints_x3_counts`, `complaints_component_filter`, `complaints_redaction_keys`, and the field-accuracy half of `complaints_unknown_component_is_zero`. Live `complaintsByVehicle?make=BMW&model=X3&modelYear=2011` returned HTTP 400. 2012 Acura RDX complaints returned 200 with count 15. So this is NHTSA rejecting that model string, plus the server not turning 400 into an empty shaped summary. The frozen Civic/X3 complaint fixtures never hit this path.

### NHTSA / fixture drift

1. `investigation_link`. Live `EA15001` is 71004 product rows, 20 returned. Campaign `17V683000` is not on those rows and is not on any `EA15001` row in the live index. The frozen `investigations.txt` sample is the only place that join exists.
2. `investigation_by_vehicle`. Live search for 2012 Acura RDX returned count 0. In the live zip, `PE14001` is Toyota Camry Hybrid brakes, and Acura RDX investigation products start at 2013. The frozen sample linked `PE14001` to the 2012 RDX.
3. `decode_raw_filled_drops_sentinels` (field accuracy). Live `other_filled_fields` has no `OtherEngineInfo`. The frozen decode plants `"OtherEngineInfo": "Fixture only extra field"`.

Live RDX recalls still match the fixture pair (`19V182000`, `16V061000`). Vehicle 7520 is still `Not Rated`. The partial VIN still decodes as a 2011 BMW X3 with error code 6. 2011 BMW X3 live recalls are now 4 campaigns, not the single `17V683000` in the older fixture, but the scorer only required strings that were still present.

## Method notes

- Glovebox was not in this session's MCP tool list, so the stdio helper was used. That still starts `python -m glovebox_nhtsa` and calls the real tools.
- Answers quote the live tool JSON. They were not edited after scoring.
- Field accuracy on tool-using cases checks the tool JSON against fixture strings, so a live 400 or a different investigations file fails even when the model called the right tool.
- Exact-phrase `must_include` on out-of-scope answers is a wording trap for a blinded model.
