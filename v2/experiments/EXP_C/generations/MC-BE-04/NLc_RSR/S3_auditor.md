## Constraint Review
- C1 (Python + FastAPI): PASS — File uses Python with `from fastapi import FastAPI, Request, Response` and defines a FastAPI application with middleware.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` class implements proper token bucket algorithm with `refill()` (adds tokens based on elapsed time × rate, capped at burst) and `consume()` (checks and deducts tokens); not a simple counter or fixed-window approach.
- C3 (stdlib + fastapi, no Redis): PASS — All imports are from Python stdlib (`math`, `time`, `dataclasses`, `typing`) or FastAPI/Pydantic (`fastapi`, `pydantic`); no Redis, memcached, or external storage used. All state is in-memory.
- C4 (Single file): PASS — All code (TokenBucket, RateLimiter, middleware, API endpoints) defined in a single file.
- C5 (429 + Retry-After + whitelist): PASS — Middleware returns `JSONResponse(status_code=429, ...)` with `headers={"Retry-After": str(retry_after)}` when rate limit exceeded; `WHITELIST_IPS` set checked via `is_whitelisted()` to bypass rate limiting for trusted IPs.
- C6 (Code only): PASS — File contains only executable Python code with no embedded documentation or non-code content.

## Functionality Assessment (0-5)
Score: 5 — Complete token bucket rate limiter with configurable rate/burst, proper time-based refill with deficit-based Retry-After calculation, IP whitelist with add/remove management, stale bucket cleanup (5-minute threshold), rate limit response headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset), status/config/health endpoints, and demo endpoints for whitelist and bucket inspection. The middleware correctly applies to all routes and adds informative headers to successful responses.

## Corrected Code
No correction needed.
