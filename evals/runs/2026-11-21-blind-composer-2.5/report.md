# Blind eval: Composer 2.5

Overall: 31/40 cases fully passed (tool, arguments, field accuracy, faithfulness).

## Metric rates

- Tool selection: 40/40
- Argument correctness: 39/40
- Field accuracy: 31/40
- Faithfulness: 39/40

## Category breakdown (full pass only)

- complaints_redaction: 0/1
- complaints_summary: 1/4
- decode_check_digit: 1/1
- decode_invalid: 4/4
- decode_partial: 3/3
- investigation_link: 3/3
- missing_means_unknown: 1/1
- not_applicable_dropped: 1/2
- out_of_scope: 0/3
- profile_partial: 3/3
- ratings_not_rated: 2/2
- ratings_variant: 2/2
- recalls_hit: 6/6
- recalls_not_repair_status: 1/1
- recalls_spelling: 3/4

## Failures

### recalls_spelling_miss
tool=True args=True fields=False faith=True
missing_fields: ['not proof']
Cause: Server bug: NHTSA returns HTTP 400 with empty JSON; Glovebox surfaces upstream_unavailable instead of count 0.

### complaints_x3_counts
tool=True args=True fields=False faith=True
missing_fields: ['ENGINE', 'crash_reports']
Cause: Server bug: same HTTP 400 with empty body pattern on complaints_by_vehicle.

### complaints_component_filter
tool=True args=True fields=False faith=True
missing_fields: ['ENGINE']
Cause: Server bug: complaints_by_vehicle HTTP 400 handling.

### complaints_redaction_keys
tool=True args=True fields=False faith=True
missing_fields: ['consumer reports']
Cause: Server bug: complaints_by_vehicle HTTP 400 handling.

### out_of_scope_title
tool=True args=True fields=False faith=True
missing_fields: ['does not have title history']
Cause: Model mistake: answer did not use the exact coverage wording the scorer expects.

### out_of_scope_fuel
tool=True args=True fields=False faith=True
missing_fields: ['does not have fuel economy']
Cause: Model mistake: answer did not use the exact coverage wording the scorer expects.

### out_of_scope_repair
tool=True args=True fields=False faith=True
missing_fields: ['does not show repair completion']
Cause: Model mistake: answer did not use the exact coverage wording the scorer expects.

### decode_raw_filled_drops_sentinels
tool=True args=True fields=False faith=False
missing_fields: ['OtherEngineInfo']
leaked_phrases: ['Not Applicable']
Cause: NHTSA data drift or live API richer than frozen fixture (OtherEngineInfo / raw field set).

### complaints_unknown_component_is_zero
tool=True args=False fields=False faith=True
missing_fields: ['"count": 0']
Cause: Model mistake on component filter (used brake instead of BRAKES) plus server bug on complaints HTTP 400 responses.

## Notes

- Live NHTSA complaints and some recall spellings return HTTP 400 with an empty JSON body. Glovebox treats that as upstream_unavailable rather than count 0.
- scripts/run_stdio_calls.py forces GLOVEBOX_INVESTIGATIONS_FILE to tests/fixtures/investigations.txt even when GLOVEBOX_FIXTURES is cleared unless you also unset investigations.
- Scoring uses frozen golden must_include strings from fixtures; live drift counts as failure even when the model quoted the live tool JSON faithfully.
