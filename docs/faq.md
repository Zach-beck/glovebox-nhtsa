# FAQ

## Does this tell me if my car's recall was fixed?

No. Recall rows are campaigns filed against a model string. Whether a particular VIN was repaired is not in these APIs. Use NHTSA's own recall lookup on their website for that question, and treat Glovebox as the model-level history.

## Why did a normal-looking VIN come back with an error code?

vPIC returns HTTP 200 even when `ErrorCode` is not zero. Code `6` means the VIN is incomplete (`*` or a short VIN). Code `1` means the check digit did not match, and the response can still name a vehicle. Code `400` means a character was invalid. The strings are NHTSA's, returned on the decode.

## Why are there no stars?

`Not Rated` is a published value. It is not zero stars. The model string can also miss. `list_model_names` shows the spellings NCAP and the recall list use. An empty list is not, by itself, proof the vehicle was never tested under another name.

## Why is a complaint count different from the NHTSA website?

Glovebox counts the rows the complaints API returns for that exact make, model, and year, after an optional component filter. A different spelling returns a different set. Glovebox does not show the narratives, so you cannot reconcile a single story from here. The count is the count of reports, not a defect rate.

## Can I run it offline?

Investigations can, if `GLOVEBOX_INVESTIGATIONS_FILE` points at `FLAT_INV.zip` or the text file, or if a previous run already downloaded the zip into the data directory. Set `GLOVEBOX_OFFLINE=1` and Glovebox will not call NHTSA. Decode, recalls, complaints, and ratings then return unavailable unless a shaped result is already in the cache. There is no Postgres database in this version.

## Is there a rate limit?

NHTSA's pages disagree, and a small polite test on 2026-11-22 saw no HTTP 429 and no rate-limit headers. The writeup is [research/rate-limits-and-terms.md](research/rate-limits-and-terms.md). Glovebox waits 0.25 seconds between calls to the same host, keeps two calls in flight at most, and retries 429 and 503. It is not a bulk downloader. For large VIN lists, use NHTSA's standalone vPIC database yourself. Glovebox does not bundle it.

## Where do model keys go?

Only in a gitignored `.env`, and only for `python evals/local.py`. The server never reads them. If neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set, the eval command prints a skip report and exits 0. It does not ask you to paste a key.

## Is the investigations file small?

The zip is about 4 MB. Unzipped, the text file we measured on 2026-11-22 was about 370 MB across about 154,000 lines, because summaries repeat. Glovebox indexes the short columns and loads one clipped summary when you pass `nhtsa_id`.

## What is left out on purpose?

Fuel economy (that is the Department of Energy and the EPA), title and accident history, manufacturer communications, FARS crash counts, and per-VIN repair status.

## Why is the GitHub name already taken?

`glovebox-mcp` on GitHub is an unrelated computer-use project, `segentic-lab/glovebox-mcp`. The PyPI name `glovebox-mcp` was free when this was built. This repo does not publish to either place.
