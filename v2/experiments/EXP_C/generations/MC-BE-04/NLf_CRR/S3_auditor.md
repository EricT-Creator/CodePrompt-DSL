## Constraint Review
- C1 (Python + FastAPI): PASS — `from fastapi import FastAPI, HTTPException, Request`; `app = FastAPI(title="Token Bucket Rate Limiter")`.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` dataclass with `capacity`, `refill_rate`, `tokens`, `last_update`; `consume()` refills tokens based on elapsed time before checking—classic token bucket algorithm, not a simple counter or fixed window.
- C3 (stdlib + fastapi, no Redis): PASS — Imports are `json`, `math`, `dataclasses`, `time`, `typing` (all stdlib) plus `fastapi` and `starlette` (bundled with fastapi). No Redis, memcached, or external storage.
- C4 (Single file): PASS — All code in one file: TokenBucket, RateLimiter, middleware, IP extraction, endpoints.
- C5 (429 + Retry-After + whitelist): PASS — Returns `JSONResponse(status_code=429, headers={"Retry-After": str(retry_after_int), ...})` when rate exceeded. `WHITELIST_IPS = {"127.0.0.1", "::1", "10.0.0.1"}` bypasses rate limiting via `is_whitelisted()`.
- C6 (Code only): PASS — No explanatory prose; file is pure code.

## Functionality Assessment (0-5)
Score: 5 — Production-quality rate limiter with: per-IP token bucket, configurable capacity/refill rate, X-Forwarded-For/X-Real-IP support, Retry-After header with ceiling, X-RateLimit-Limit/Remaining headers, IP whitelist bypass, stale bucket cleanup, middleware integration, and multiple demo endpoints including a simulated heavy one.

## Corrected Code
No correction needed.
