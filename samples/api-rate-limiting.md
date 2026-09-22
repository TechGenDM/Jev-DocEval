# API Rate Limiting Design

## Goal

Protect the public API from abuse while keeping latency low for legitimate
clients. This note is the design input for the Q3 platform work.

## Proposal

Introduce a token-bucket limiter at the edge (Cloudflare Worker) keyed by
API key, with a second soft limit keyed by IP for unauthenticated health
checks.

| Tier | Steady rate | Burst |
| --- | --- | --- |
| Free | 60 req/min | 20 |
| Pro | 600 req/min | 100 |
| Enterprise | negotiated | negotiated |

## Failure behavior

When a client exceeds its budget:

1. Return `429 Too Many Requests`
2. Include `Retry-After` (seconds) and `X-RateLimit-Remaining`
3. Do **not** queue the request server-side

## Tradeoffs

- Edge limiting is cheap and fails closed if the origin is down, but cannot
  see authenticated user identity after custom auth at the origin.
- Origin limiting sees the real principal, but adds hop latency and is a
  single point of overload under attack.

**Decision:** edge primary, origin secondary for authenticated routes that
bypass the edge (internal VPC).

## Rollout

1. Ship shadow mode (headers only) for one week
2. Enable 429s for Free tier
3. Enable for Pro after dashboards look clean

## Open questions

- Should Websocket upgrade requests share the HTTP budget?
- Do we need per-route overrides for `/v1/search`?
