## Constraint Review
- C1 (Python + FastAPI): PASS — Uses `from fastapi import FastAPI, Request` and defines `app = FastAPI(title="Token Bucket Rate Limiter")`.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` dataclass with `tokens` float, `last_refill` timestamp, `refill()` method that adds `elapsed * rate` tokens capped at `burst`, and `consume()` that checks/deducts; not a simple counter.
- C3 (stdlib + fastapi, no Redis): PASS — Imports only stdlib modules (time, math, dataclasses, typing) plus fastapi; no Redis or external packages.
- C4 (Single file): PASS — All code (TokenBucket, bucket store, middleware, endpoints) in one file.
- C5 (429 + Retry-After + whitelist): PASS — Returns `JSONResponse(status_code=429, ..., headers={"Retry-After": str(...)})` when rate exceeded; `WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1"}` checked before rate limiting.
- C6 (Code only): PASS — File contains only code with minimal section comments.

## Functionality Assessment (0-5)
Score: 5 — Complete token bucket rate limiter with: proper token refill based on elapsed time, burst capacity, configurable rate/burst, IP-based bucketing, whitelist bypass, 429 response with Retry-After header, X-RateLimit-Remaining/Limit response headers, stale bucket cleanup (triggered at 1000+ buckets), /status endpoint showing per-IP bucket state with lazy refill calculation, and clean middleware implementation.

## Corrected Code
No correction needed.
