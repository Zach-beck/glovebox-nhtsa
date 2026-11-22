# Blind eval post-fix: Composer 2.5

Overall: 35/40 cases fully passed.

## Metric rates

- Tool selection: 40/40
- Argument correctness: 40/40
- Field accuracy: 35/40
- Faithfulness: 40/40

## Category breakdown (full pass only)

- complaints_redaction: 1/1
- complaints_summary: 2/4
- decode_check_digit: 1/1
- decode_invalid: 4/4
- decode_partial: 3/3
- investigation_link: 1/3
- missing_means_unknown: 1/1
- not_applicable_dropped: 1/2
- out_of_scope: 3/3
- profile_partial: 3/3
- ratings_not_rated: 2/2
- ratings_variant: 2/2
- recalls_hit: 6/6
- recalls_not_repair_status: 1/1
- recalls_spelling: 4/4

## Failures

### complaints_x3_counts
tool=True args=True fields=False faith=True
missing_fields: ['ENGINE']
Cause: fixture_only case; live NHTSA returns count 0 (HTTP 400 empty body handled correctly).

### complaints_component_filter
tool=True args=True fields=False faith=True
missing_fields: ['ENGINE']
Cause: fixture_only case; live complaint count is 0 for this model string.

### investigation_link
tool=True args=True fields=False faith=True
missing_fields: ['17V683000']
Cause: fixture_only case; live FLAT_INV sample does not include the frozen campaign join.

### investigation_by_vehicle
tool=True args=True fields=False faith=True
missing_fields: ['PE14001']
Cause: fixture_only case; live index has no 2012 Acura RDX row with PE14001.

### decode_raw_filled_drops_sentinels
tool=True args=True fields=False faith=True
missing_fields: ['OtherEngineInfo']
Cause: fixture_only case; live vPIC omits that extra field.

