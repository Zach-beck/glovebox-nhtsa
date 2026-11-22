# Caching and polite upstream access

## Why cache

A single `vehicle_report` can hit vPIC, recalls, complaints, NCAP, and the local investigations index. NHTSA data changes slowly compared to interactive chat. Caching shaped tool JSON avoids duplicate calls when a user or agent re-asks about the same VIN or the same make, model, and year.

Glovebox never caches raw complaint bodies. Shaped complaint output is counts and component buckets only.

## Modes

| Setting | Behavior |
| --- | --- |
| Default | In-memory TTL cache (`GLOVEBOX_CACHE` unset or `memory`) |
| `GLOVEBOX_CACHE=disk` or `GLOVEBOX_CACHE_DIR=/path` | On-disk JSON files under the directory (default `~/.cache/glovebox-nhtsa` when only `disk` is set) |
| `GLOVEBOX_CACHE=off` | No cache reads or writes |

The cache stores successful shaped responses only. Upstream errors, `invalid_arguments`, and other `error` objects are never written. A past failure does not masquerade as a later success.

## TTLs

| Dataset | TTL | Rationale |
| --- | --- | --- |
| vPIC decode | 7 days | Identity fields rarely change; VIN decode is expensive to repeat in one session |
| Recalls | 6 hours | Campaigns update occasionally; short enough for same-day checks |
| Complaint counts | 6 hours | Same as recalls for a given model string |
| NCAP ratings and model lists | 7 days | Ratings and spellings change slowly |

These TTLs are a tradeoff between freshness and load on public NHTSA hosts. They are not a freshness guarantee.

## Live backend limits

When not using fixtures, `LiveBackend` keeps at most two in-flight requests per NHTSA host, waits `GLOVEBOX_REQUEST_GAP_SECONDS` (default 0.25) between calls to the same host, and retries HTTP 429 or 503 up to three times with exponential backoff (honoring `Retry-After` when present). Redirects off the allowlisted hosts are refused.

## Disabling cache

For debugging or tests:

```bash
export GLOVEBOX_CACHE=off
```

For reproducible disk inspection:

```bash
export GLOVEBOX_CACHE=disk
export GLOVEBOX_CACHE_DIR=/tmp/glovebox-cache
```