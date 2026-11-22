# Rate limits, traffic control, and terms

What NHTSA publishes, what a small test showed on 2026-11-22, and what is still unknown. The raw counts for the paced run are in [spikes/2026-11-22-probe.json](spikes/2026-11-22-probe.json).

## How the test was run

One Python process, concurrency 1, User-Agent `vehicle-specs-agent-research/0.1`. No API key. Calls went to `vpic.nhtsa.dot.gov`, `api.nhtsa.gov`, `static.nhtsa.gov`, and one Crash API URL.

| Wave | When (UTC) | Requests | Kept |
| --- | --- | --- | --- |
| Saved probe plus paced phases | 2026-11-22 00:58:49 to 01:00:44 | 188 (71 probes, then 117 paced) | Yes. This is the latency table. |
| Short follow-ups the same morning | after 01:00 | 12 | Statuses and a few fields, written up in the data inventory. |
| An earlier pass of the same probe list | just before 00:58 | about 55, then the script crashed before the paced phase | Status codes only, in the terminal log. Not used for latency. |

About 255 requests in total. That is the whole test. It was not an attempt to find the ceiling. The fastest gap was 100 milliseconds between 15 calls, and those calls themselves took 180 to 1,300 milliseconds, so the offered rate stayed under a few requests per second.

We stored status, latency, size, selected headers, and a few non-sensitive fields. We did not store complaint narratives, complaint VINs, or manufacturer staff contact details.

## Documented

### vPIC says three things that do not fully agree

1. The [API home page](https://vpic.nhtsa.dot.gov/api/) says applications "will be controlled by an automated traffic rate control mechanism" so the public site stays usable. It publishes no threshold, no status code, and no `Retry-After` contract.

2. The [API FAQ](https://vpic.nhtsa.dot.gov/api/Home/Index/FAQ) answers "is there a daily limit?" with no. It then asks that large batches run at night US Eastern time or on the weekend, says the servers handle about 1000 to 2000 transactions per minute on a normal weekday, and says an upper limit has not been reached. The batch decode has a separate, non-numeric warning that too many VINs in one batch will bog it down. The documented batch maximum on the API page is 50 VINs. The FAQ tells heavy users to call the normal decode in a loop instead.

3. The [downloads page](https://vpic.nhtsa.dot.gov/downloads/) says there are quotas and rate limits on the API, and that the standalone database avoids them. It does not say what the quota is. The [about page](https://vpic.nhtsa.dot.gov/about/) repeats that sentence.

So the existence of some traffic control is documented. A numeric daily cap is not. The FAQ denies a daily cap and offers a capacity figure. The downloads page asserts quotas without defining them. **The number, if there is one, is unknown.**

Also documented on the FAQ: no registration, no license, free for public use. Target availability 99 percent between 6 AM and 6 PM US Eastern. Maintenance is usually on a weekend. The service is described as up 24 hours aside from that.

### api.nhtsa.gov

The [datasets page](https://www.nhtsa.gov/nhtsa-datasets-and-apis) documents the recalls, complaints, and safety-ratings paths. It does not mention a key, a quota, or a throttle status. We did not find a NHTSA page that assigns a number to `api.nhtsa.gov`.

### api.data.gov, which is a different statement

[api.data.gov's developer manual](https://api.data.gov/docs/developer-manual/) says participating APIs default to 1,000 requests per hour per key, return `X-RateLimit-Limit` and `X-RateLimit-Remaining`, and return HTTP 429 when the key is over the limit. `DEMO_KEY` is 30 requests per hour per IP and 50 per day. That document describes api.data.gov. It does not name the NHTSA vehicle APIs.

A third-party rate-limit profile claims `api.nhtsa.gov` is fronted by api.data.gov and inherits the 1,000-per-hour key limit. The profile's own page says it was not verified against a provider page. We do not adopt that number. It is **unverified**, and the observations below contradict the part about headers and keys.

### Terms of use

[NHTSA Terms of Use](https://www.nhtsa.gov/about-nhtsa/terms-use), read 2026-11-22:

- The site is a public service. It is monitored to confirm it works and that security features work. Using the system is consent to that monitoring.
- Attempts to modify stored information, defeat security, or use the system for other than its intended purposes are prohibited and may be prosecuted.
- NHTSA disclaims accuracy, completeness, and adequacy, and disclaims warranties, including fitness for a particular purpose.
- Information on the site "is considered public information and may be distributed or copied."
- Naming a commercial product is not an endorsement.

That is the license position we will repeat in the README: public information, no warranty, not an endorsement, not an invitation to bypass controls. We will not add a separate claim that every file is "public domain" under 17 USC 105. The terms page is the source we actually read, and manufacturer-submitted text sits inside some of these files. A lawyer can go further. This project should quote NHTSA and stop.

The vPIC FAQ's "no registration, free open data" line is consistent with those terms. It is not a grant to run an open proxy that spends NHTSA's capacity for anonymous internet clients.

### Crash API

The [Crash API](https://crashviewer.nhtsa.dot.gov/crashviewer/CrashAPI/) page says several list endpoints are limited to 5,000 records, and that exporting all states should be kept to a five-year range. That is a result-size cap, not a requests-per-minute cap. We did not try to trip it.

## Observed

No response in the saved run or the follow-ups was 429 or 503. No `Retry-After` header was present. No `X-RateLimit-Limit`, `X-RateLimit-Remaining`, or `RateLimit-*` header was present on the responses whose headers we inspected. vPIC and `api.nhtsa.gov` did not require a key.

### Paced phases

All of these used one URL, repeated, with a sleep between calls. Latency is the client-side time to headers and body.

| Phase | N | Gap | Statuses | min | p50 | p95 | max | mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vPIC `DecodeVinValues` of the documented partial VIN | 50 | 0.30 s | 200 only | 143 ms | 220 ms | 906 ms | 1,024 ms | 307 ms |
| Recalls, Acura RDX 2012 | 25 | 0.40 s | 200 only | 85 ms | 156 ms | 289 ms | 928 ms | 184 ms |
| Ratings, vehicle id 7520 | 15 | 0.40 s | 200 only | 93 ms | 129 ms | 153 ms | 163 ms | 127 ms |
| Complaints, Acura RDX 2012 | 12 | 0.50 s | 200 only | 364 ms | 389 ms | 488 ms | 520 ms | 408 ms |
| vPIC decode, a different example VIN | 15 | 0.10 s | 200 only | 181 ms | 480 ms | 1,143 ms | 1,312 ms | 518 ms |

The tighter vPIC gap had a higher median. Fifteen samples cannot prove a throttle. It is equally consistent with ordinary variance, which the first phase already showed (a 1 second outlier at a 300 millisecond gap). What it does show: at this volume, the server answered 200 every time, and it did not send a limit header when it was slow.

### Other observations that bear on traffic

- vPIC decode responses sent `Cache-Control: no-cache`. An HTTP cache in front of the client is being told not to store them. An application cache inside the agent is still our choice, and it is the right one, because the FAQ asks the public not to lean on the API for bulk work.
- vPIC often sent `set-cookie`. Values were not recorded. We do not know whether the cookie is load-balancer affinity. **Unknown.**
- Successful `api.nhtsa.gov` responses included `x-amz-apigw-id` and `x-amzn-requestid`. The host is behind Amazon API Gateway. That explains the error body below. It does not, by itself, mean the api.data.gov key system is in use.
- Unknown paths (`/recalls/recallsByVin`, a guessed investigations path, a guessed communications path) returned HTTP 403 and `{"message":"Missing Authentication Token"}`. Documented paths on the same host returned 200 with no key. The 403 is the Gateway's response when the route is not there. It is not evidence that recalls or complaints require a token.
- `GetAllMakes` was 616 KB and took 1.4 seconds once. `GetEquipmentPlantCodes` for one equipment type was 281 KB. A model that calls either of those in a loop would be both a context problem and a traffic problem.
- Complaint latency tracked payload size. The 17 KB Acura body was about 400 milliseconds. The 577 KB Civic body, called a few times outside the paced phase, was about 1.9 seconds. Serving that body through to a model would be the expensive mistake, not the HTTP call.
- Static flat-file HEAD requests returned 200. `FLAT_INV.zip`, both recall zips, the complaint zip, and two manufacturer-communication chunks were last modified on 21 November 2026. HEAD omitted `Content-Length`, so the page's published sizes were not remeasured.

The unsaved earlier pass printed the same 200s and the same 404s (`GetMakesForManufacturer`, equipment-plant path form) before it crashed. It did not show a 429 either. It is supporting evidence, not the table above.

## Unknown

- The numeric vPIC quota the downloads page alludes to. Not published, not encountered.
- Whether a faster client, a shared NAT, or a multi-hour batch would see 429, 403, or a silent delay. We deliberately did not try.
- Whether `api.nhtsa.gov` has an unpublished Gateway usage plan that would show up only after more traffic than we sent.
- Whether the `set-cookie` on vPIC changes routing or limits.
- Whether weekend evening (this run was Saturday night in US Eastern time) is quieter than a weekday afternoon. The FAQ asks large jobs to avoid weekday work hours. Our test was inside that requested window, at a tiny volume.
- Crash API stability. One analytics call returned JSON. A wrong base path returned the website HTML. Another project reports a 403 on a different day. See the data inventory.

## Implications for the agent

**Cache inside the process.** Suggested starting TTLs, as a design choice rather than a NHTSA rule:

| Data | TTL | Why |
| --- | --- | --- |
| VIN decode | 30 days | Manufacturer submissions change slowly. The monthly database refresh is the natural outer bound. |
| Recalls for a make, model, and year | 12 hours | The flat files were refreshed daily in the snapshot we saw. A shopper can tolerate half a day. |
| Complaint summary | 12 hours | Same reason, and the payload is large enough that repeating it is wasteful. |
| A single NCAP vehicle id | 7 days | The datasets page says the ratings release is annual. New model years appear, old rows sit still. |
| Investigations index | 24 hours | The zip's last-modified date moved daily in this snapshot. |

Cache keys must include the normalized arguments. Do not cache a 200 whose `ErrorCode` is non-zero as if it were a clean decode, or do cache it but keep the error visible. Never cache the 403 "missing token" body as a successful empty list.

**Backoff.** If a 429 or 503 ever appears, stop, honor `Retry-After` when it is present, and otherwise wait 1 second, then 2, then 4, up to three tries. Log the status and the path, not the complaint body. We have not seen the need. Shipping the behavior anyway is cheap.

**One in-flight call per host, two at most.** A profile fans out to decode, recalls, complaints, and ratings. Run those with a small pool. Do not give the model a tool that loops `GetAllMakes` or pages the entire complaint file.

**Identify the client.** Send a User-Agent with the project name and a URL once the repo is public. The research agent used a throwaway string. A public server should not pretend to be a browser.

**Prefer bulk files for anything that scans.** Investigations are a 4 MB zip. A local index answers search without touching the API. The vPIC Postgres dump is the supported way to decode large VIN lists. The FAQ's nighttime-batch guidance is for people who still choose the API. This project should not be that client.

**Do not operate an open relay.** A public unauthenticated URL would let the internet spend NHTSA's capacity from one address. That is the "not its intended purpose" line in the terms, read conservatively. Hosting is covered in [../hosting.md](../hosting.md). v1 is local stdio. Each user is their own small client, which is the usage the FAQ describes.

**Complaints are the sharp edge.** One Civic model year was 577 KB. Caching the raw body would also cache partial VINs and narratives onto disk. Cache the summary (counts by component, crash, fire, injury, death, date range) and drop the rest.

## What we will tell users

The README and the tool descriptions should say:

- Data is NHTSA's, offered as public information, without a warranty.
- This project is not NHTSA and not an official decoder.
- A recall row is a campaign filed against a model, not proof that this VIN is unrepaired.
- Empty spec fields mean NHTSA has no value, not that the equipment is missing.
- The server caches and slows itself down. It is not a bulk extraction tool. People who need bulk decoding should download the [standalone database](https://vpic.nhtsa.dot.gov/downloads/).
