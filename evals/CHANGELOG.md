# Eval golden set changelog

## 2026-11-22 (fix/eval-findings)

### LiveBackend HTTP 400 empty body

NHTSA returns HTTP 400 with `count`/`Count` 0 and an empty `results` list for unknown model strings on recalls and complaints. LiveBackend previously mapped every 4xx to `upstream_unavailable`. It now treats 400 plus a valid empty JSON body as a normal empty response so shapers attach spelling notices and complaint count 0 paths run. Non-JSON 400, other 4xx, 5xx, and timeouts still map to `upstream_unavailable`.

### Ratings `vehicle_id` coercion

MCP rejected integer `vehicle_id` values before the service ran. Tools and service now accept `int | str` and coerce to string.

### Complaint component filter

`summarize_complaints` matching is case insensitive with simple singular/plural overlap (`brake` matches `BRAKES`). Documented on the tool. The scorer treats equivalent component arguments as matching.

### `scripts/run_stdio_calls.py` live mode

When `GLOVEBOX_FIXTURES` is cleared for live mode, the helper no longer defaults `GLOVEBOX_INVESTIGATIONS_FILE` to the frozen sample. Live runs use the downloadable zip unless the caller sets the env var. Fixture mode still pins both paths.

### Golden `eval_mode` tags

- `fixture_only`: `investigation_link`, `investigation_by_vehicle`, `decode_raw_filled_drops_sentinels`, and the 2011 BMW X3 complaint trio (live NHTSA now returns count 0 with HTTP 400 empty body; the ENGINE rows exist only in fixtures).
- `live`: out-of-scope cases (no tool; exact refusal phrases).
- `fixture`: default for CI; frozen data in pytest.

`complaints_unknown_component_is_zero` now uses `component: brake` in golden arguments to match the question wording; scoring accepts plural forms.

### Out-of-scope discoverability

Added `coverage_limits` tool and expanded `nhtsa://coverage` plus server instructions with exact refusal phrases: `does not have title history`, `does not have fuel economy`, `does not show repair completion`.

### Faithfulness helpers

`invalid_arguments` responses include `answer_note` telling models not to repeat user-supplied identifiers. Raw-filled decode includes `sentinel_note` without embedding the literal `Not Applicable` string in tool JSON.