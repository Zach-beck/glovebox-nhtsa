# Hosting

Where this server should run. v1 is local. A public URL in front of NHTSA is an open relay, and the terms do not invite one.

## The risk that decides v1

NHTSA's APIs are keyless. Whoever's IP calls them is the client they see. A hosted MCP endpoint with no auth lets every visitor's model spend that IP's budget. We did not find a published numeric quota, and a small test saw no 429s, but the vPIC downloads page says quotas exist and the API page says traffic is controlled. Details are in [research/rate-limits-and-terms.md](research/rate-limits-and-terms.md). An open relay is the way a project finds the quota the hard way, and it is the way one user's loop becomes everyone else's outage.

Complaint bodies make it worse. A proxy that forwards them also forwards partial VINs and narratives through our logs unless we are careful. Local stdio never puts that traffic on a machine we operate.

Two existing servers illustrate the split. NLMA's vin-mcp README says their hosted endpoint has an OAuth gate specifically so the process is not an open relay against NHTSA. cyanheads publishes a public Streamable HTTP URL with no auth described in the README we read. We did not test either host. The first is the pattern to copy in spirit, later. The second is the pattern to avoid.

## Options

### Local stdio

The client starts `uvx` or the Docker image and speaks MCP on stdin and stdout. No port, no account, no shared IP.

This is the v1 recommendation. It matches "download and run it yourself." Each user is a small client, which is the usage the vPIC FAQ describes. Caching stays on their disk. A bug in our backoff hurts them, not the whole user base.

Cost: nothing. Requirement: uv, or Docker. The ADR covers that tradeoff.

### Docker, still local

A container the client runs with `-i`, stdio attached. Same trust model as uvx. Useful for someone who will not install Python, and useful as the artifact a later host would run.

Cost: Docker Desktop or an engine. Image size will be a normal Python image, not a tiny static binary. That is acceptable.

Do not publish the image's HTTP port in the quickstart. The Dockerfile can default to stdio. An HTTP mode, if we include it, binds `127.0.0.1` and is documented as debug.

### Fly.io

A small always-on machine. Their pricing page lists `shared-cpu-1x` with 256 MB at about $2.19 per 30 days in Ashburn, billed per second, plus egress ([Fly pricing](https://fly.io/pricing/), [Fly resource pricing](https://docs.fly.io/about/pricing/)). The two pages describe the free allowance differently: the docs say there is no free tier and that a bill under $5 is waived, with a $1 trial; the pricing page says a Free plan with $5 of usage after a card is added. Read both before counting on zero. A 256 MB machine is enough for the investigations zip and a cache. Postgres for offline VIN decode does not fit that story. Leave Postgres on the user's machine.

Fly is the least-bad hosted option later: one process, a persistent disk for the zip and the cache, a region in the US close to NHTSA, and a bill you can see. It is still a relay if the URL is public.

### Google Cloud Run

Request-based billing has a free tier the official price page lists as 180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million requests per month, before you pay, with CPU at $0.000024 per vCPU-second while active in the default consumption model ([Cloud Run pricing](https://cloud.google.com/run/pricing)). A service that scales to zero can sit in that tier at hobby volume. A minimum instance, kept warm, is a different and larger bill. A third-party writeup estimated about $12 a month for one always-on vCPU before the free tier. That number is their arithmetic, not ours ([DreamHost comparison](https://www.dreamhost.com/guides/docker/always-on-container-bill/)).

Cloud Run fits a stateless MCP server, which the 2026-07-28 spec encourages. Our investigations file and the cache want a disk or a bucket. Cold starts make the first tool call slow. Manageable, not nicer than Fly for this workload.

### AWS Lambda

The official page lists a free tier of 1 million requests and 400,000 GB-seconds per month for event functions ([Lambda pricing](https://aws.amazon.com/lambda/pricing/)). The stateless spec removes one reason Lambda used to be a bad MCP host. It does not remove the others: a 4 MB zip fetched on cold start, a cache that disappears, and a Python MCP server that expects a process. Possible as a later experiment. A poor v1.

### Cloudflare Workers

The July 2026 MCP post says Cloudflare's Agents SDK supported the new spec immediately, and Workers are a natural TypeScript host. This project is Python by recommendation, and Workers are not a good place to parse a zip and keep a disk cache. We did not open the current Workers price page, so this doc does not quote a free-tier number. If the language decision flips to TypeScript, re-read that page before picking a host. It still would not justify a public unauthenticated URL.

## Auth, when a host exists

Not in v1. When it does:

- Streamable HTTP only, behind TLS.
- A bearer token or OAuth, one credential per user. OpenCode and Cursor can both send headers on a remote server.
- Our own per-token rate limit, stricter than anything we hope NHTSA enforces. A starting point to revisit with real numbers: 60 tool calls per hour per token, with `vehicle_profile` counting as one call even though it fans out.
- The cache shared across tokens, so ten users asking about the same Civic do not generate ten complaint downloads.
- No anonymous tier. NLMA's README is explicit that the OAuth wall exists to protect the upstream. Agree with that goal. Do not copy their implementation.
- Logs without complaint bodies, without VINs, and without tokens.

A shared demo token in the README would recreate the open relay. Do not print one.

## Recommendation

**v1.** Local stdio. Docker as an optional local package. HTTP only on localhost, off unless someone sets the transport. No Fly app, no Cloud Run service, no public DNS name.

**Later, and only if someone actually needs a shared server.** One Fly.io machine or one Cloud Run service, authenticated, cached, with the investigations file on a volume. Put the spend cap in the platform so a loop cannot become a surprise bill. Re-read the price pages at that time. The figures above are for the decision, not a quote.

**Not planned.** An open public endpoint. A Cloudflare deployment of the Python server. A Lambda rewrite. Hosting the vPIC Postgres database as a service for strangers.
