# Tool reference

Glovebox exposes seven tools, three resources, and three prompts. Arguments are the JSON the model sends. Results are already shaped. A missing spec is unknown. `Not Rated` is a value. Complaint results have no owner text and no VIN.

## decode_vin

Decode one VIN with vPIC `DecodeVinValues`.

| Argument | Required | Notes |
| --- | --- | --- |
| `vin` | yes | Letters, digits, and `*`. At most 17 characters. |
| `model_year` | no | Sent to vPIC when you know it. |
| `include_raw_filled` | no | Default false. When true, adds other non-empty fields. |

`identity.error_code` comes from NHTSA. `6` means the VIN is incomplete. `1` means the check digit failed. The call can still name a vehicle. Do not treat HTTP success, or a populated make, as a clean decode.

`specs` omits empty strings and `Not Applicable`. `spec_note` says a missing field is not proof the equipment is absent.

## get_recalls

| Argument | Required | Notes |
| --- | --- | --- |
| `make`, `model`, `model_year` | together | Not a VIN. |
| `campaign_number` | instead of the three | One campaign. |
| `include_remedy` | no | Adds clipped consequence and remedy text. |

Dates are converted from day/month/year to ISO. If both the day and the month are 12 or less, `report_received.note` says a US month/day reading would differ.

`note` says these rows do not show whether a specific VIN was repaired. `count: 0` includes a notice that the spelling may be wrong.

## summarize_complaints

| Argument | Required | Notes |
| --- | --- | --- |
| `make`, `model`, `model_year` | yes | |
| `component` | no | Case-insensitive substring of the component string. |

Returns `count`, crash and fire report totals, injuries, deaths, and up to eight components. There is no narrative and no VIN field, including when you ask for examples. That argument does not exist.

## get_safety_ratings

| Argument | Required | Notes |
| --- | --- | --- |
| `make`, `model`, `model_year` | together | Returns variants. |
| `vehicle_id` | instead | One variant, including `Not Rated`. |

Two variants, such as FWD and AWD, are listed and not collapsed. Pass `vehicle_id` for the stars. An empty list is a spelling miss until `list_model_names` says otherwise.

## search_investigations

Reads the local investigations file. The first run can download `FLAT_INV.zip` from `static.nhtsa.gov` unless `GLOVEBOX_INVESTIGATIONS_FILE` points at a file you already have, or offline mode is on.

| Argument | Required | Notes |
| --- | --- | --- |
| `make`, `model`, `model_year`, `component`, `query`, `nhtsa_id` | at least one | Combined with AND. |

At most 20 rows, newest open date first. `count` can be much larger than 20: the flat file repeats an investigation once per product row. A live lookup of `EA15001` on 2026-11-22 matched 71,004 rows and returned 20. `summary` is present only for an `nhtsa_id` lookup, and it is clipped to 1,000 characters. The zip is about 4 MB. The text inside is about 370 MB. The index keeps the short columns and does not keep every summary in memory.

## list_model_names

| Argument | Required |
| --- | --- |
| `make`, `model_year` | yes |

Three lists: `vpic`, `recall_product_list`, and `ncap`. The recall product list is incomplete. During research, BMW X3 2011 had recall campaigns and was missing from that list. Each list is capped at 40 names.

## vehicle_profile

| Argument | Required | Notes |
| --- | --- | --- |
| `vin` | or the next three | Optional `model_year` alongside the VIN. |
| `make`, `model`, `model_year` | or a VIN | |

Returns `identity`, `specs`, `recalls`, `complaints`, `ratings`, `investigations`, and `section_status` of `ok`, `empty`, or `unavailable` per section. One failed section does not clear the others.

## Resources

| URI | What it is |
| --- | --- |
| `nhtsa://about` | The claims Glovebox will not make, and a link to NHTSA's terms. |
| `nhtsa://coverage` | Which datasets are live, which are local, and what is left out. |
| `nhtsa://vehicle/{vin}` | The same object as `vehicle_profile` for that VIN. |

## Prompts

These are user-chosen templates, not hidden instructions.

| Prompt | What it asks the model to do |
| --- | --- |
| `buyer_brief` | Call `vehicle_profile` and quote only returned fields. |
| `recall_status` | Explain campaigns and say this is not repair status. |
| `ratings_gap` | If ratings are empty, call `list_model_names` before concluding the vehicle was not tested. |

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GLOVEBOX_TRANSPORT` | `stdio` | `stdio` or `http` |
| `GLOVEBOX_HTTP_HOST` | `127.0.0.1` | HTTP bind address |
| `GLOVEBOX_HTTP_PORT` | `8741` | HTTP port |
| `GLOVEBOX_HTTP_TOKEN` | unset | If set, HTTP requires `Authorization: Bearer` |
| `GLOVEBOX_CACHE_DIR` | `~/.cache/glovebox-nhtsa` | Shaped results |
| `GLOVEBOX_DATA_DIR` | under the cache dir | Downloaded investigations zip |
| `GLOVEBOX_OFFLINE` | off | No live calls. Investigations still work from a local file. |
| `GLOVEBOX_FIXTURES` | unset | Directory of frozen JSON. Tests set this. Do not set it for real use. |
| `GLOVEBOX_INVESTIGATIONS_FILE` | unset | A zip or text file to use instead of downloading. |
| `GLOVEBOX_REQUEST_GAP_SECONDS` | `0.25` | Minimum gap between calls to one host. |

Cache lifetimes: VIN decode 30 days, recalls and complaint counts 12 hours, ratings and model lists 7 days. Timeouts are 20 seconds. A 429 or 503 waits and retries up to three times. Hosts are limited to `vpic.nhtsa.dot.gov`, `api.nhtsa.gov`, and `static.nhtsa.gov`. Redirects are refused.
