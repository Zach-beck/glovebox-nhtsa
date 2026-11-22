# Blinded agent-run eval: Grok 4.5

Label: blinded agent-run eval, not the CI gate.

| Field | Value |
| --- | --- |
| Model | Cursor Grok 4.5 (this cloud agent session) |
| Date | 2026-11-21 (run folder); executed 2026-11-22 |
| Cases | 40 |
| Case pass (all four metrics) | **29/40** |
| Data source | Live NHTSA APIs via `glovebox-nhtsa` stdio (`scripts/run_stdio_calls.py` and a direct stdio client). Fixtures env unset. |
| Blinding | Prompts extracted as `id` + `question` (+ category) only before answering. Expected tool args and must_include / must_not_include were not read until after `answers.jsonl` was written. |
| Branch | `evals/blind-grok-4.5` |

## Metric summary

| Metric | Passed | Total | Rate |
| --- | --- | --- | --- |
| Tool selection | 40 | 40 | 1.0 |
| Argument correctness | 39 | 40 | 0.975 |
| Field accuracy | 29 | 40 | 0.725 |
| Faithfulness | 39 | 40 | 0.975 |

## Per-category case pass

| Category | Passed | Total | Failures |
| --- | --- | --- | --- |
| decode_partial | 3 | 3 | |
| decode_invalid | 4 | 4 | |
| decode_check_digit | 1 | 1 | |
| missing_means_unknown | 1 | 1 | |
| not_applicable_dropped | 1 | 2 | decode_raw_filled_drops_sentinels |
| recalls_hit | 6 | 6 | |
| recalls_spelling | 3 | 4 | recalls_spelling_miss |
| recalls_not_repair_status | 1 | 1 | |
| complaints_summary | 1 | 4 | complaints_x3_counts, complaints_component_filter, complaints_unknown_component_is_zero |
| complaints_redaction | 0 | 1 | complaints_redaction_keys |
| ratings_not_rated | 2 | 2 | |
| ratings_variant | 2 | 2 | |
| profile_partial | 3 | 3 | |
| investigation_link | 1 | 3 | investigation_link, investigation_by_vehicle |
| out_of_scope | 0 | 3 | out_of_scope_title, out_of_scope_fuel, out_of_scope_repair |

## Failures and causes

### Model mistake

- **out_of_scope_title / out_of_scope_fuel / out_of_scope_repair**: Correct refusal and no tool call, but the answer text missed the exact golden phrases (`does not have title history`, `does not have fuel economy`, `does not show repair completion`). Field accuracy for no-tool cases scores the answer string.
- **complaints_unknown_component_is_zero**: Called `summarize_complaints` with `component: "brake"`; golden expects `"BRAKES"`. Argument correctness failed before live data issues.
- **decode_raw_filled_drops_sentinels** (faithfulness only): The answer mentioned `BusType` and `Not Applicable` while saying they were absent. The scorer treats those as leaked `must_not_include` phrases in the answer.

### NHTSA data drift (live vs frozen fixtures)

- **complaints_x3_counts**, **complaints_component_filter**, **complaints_redaction_keys**: Live `complaintsByVehicle` for BMW / X3 / 2011 returned HTTP 400. Tool JSON is `upstream_unavailable`, so fixture strings (`ENGINE`, `crash_reports`, `consumer reports`) are missing. Acura RDX 2012 complaints still work (count 15).
- **investigation_link**: Live `EA15001` returns count 71004 (20 rows). The golden field check wants campaign `17V683000` in the tool JSON; the first 20 live product rows did not include that string (fixture slice did).
- **investigation_by_vehicle**: Live search for 2012 Acura RDX returned count 0; golden expects fixture id `PE14001`.
- **decode_raw_filled_drops_sentinels** (field accuracy): Live `other_filled_fields` has no `OtherEngineInfo` key (fixture did).

### Server bug / shaping suspicion

- **recalls_spelling_miss**: Live NHTSA returns HTTP 400 for model `NO-SUCH`. The server surfaces `upstream_unavailable` instead of an empty campaign list with the usual `not proof` / spelling notice that fixtures encode. Golden field accuracy wants `not proof` in the tool JSON. Treating a 400 misspelling like an empty spelling miss would match the documented product behavior better.
- **get_safety_ratings `vehicle_id`**: Passing integer `7520` fails Pydantic (`Input should be a valid string`) before the tool body runs. String `"7520"` works. Easy agent footgun; coerce int-or-string would help.
- BMW X3 complaints HTTP 400 mapped only as `upstream_unavailable` with no retry via `list_model_names` alternate spellings. May be NHTSA-side, but the shaped error gives the model nothing countable.

## Pytest (CI gate, separate)

```text
uv run pytest
29 passed in 1.15s
```

Recorded in `pytest.txt`. This is the offline fixture gate, not the agent score.

## Artifacts

- `answers.jsonl`: 40 transcripts (question, tool_calls, answer)
- `tool-results.json`: merged live tool payloads
- `scores.json`: `evals.score` summary
- `pytest.txt`: CI suite output
