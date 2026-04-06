## Constraint Review
- C1 (Python + FastAPI): PASS — File uses `from fastapi import FastAPI, Request, Response` and defines `app = FastAPI()`.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` class implements the token bucket algorithm with `tokens`, `rate` (refill rate), and `burst` (max capacity). Tokens are refilled based on elapsed time (`bucket.tokens + elapsed * bucket.rate`) and consumed by decrementing (`bucket.tokens -= 1.0`). This is not a simple counter or fixed window.
- C3 (stdlib + fastapi, no Redis): PASS — Imports are `asyncio`, `math`, `time`, `typing` (all stdlib) plus `fastapi` and `starlette.middleware.base.BaseHTTPMiddleware` (starlette is bundled with FastAPI). No Redis or memcached.
- C4 (Single file): PASS — Everything is contained in a single Python file.
- C5 (429 + Retry-After + whitelist): PASS — Returns `JSONResponse(status_code=429, ...)` with `Retry-After` header when tokens < 1.0. Whitelist check `if client_ip in self.config.whitelist: return await call_next(request)` bypasses rate limiting for whitelisted IPs (default: `127.0.0.1`).
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 4 — Well-implemented token bucket rate limiter with per-IP buckets, configurable rate/burst, IP whitelist bypass, proper `Retry-After` calculation, rate limit headers (`X-RateLimit-Limit/Remaining/Reset`), and periodic stale bucket cleanup. Minor issues: `middleware` variable on line 101 creates a `RateLimiterMiddleware` instance manually, but `app.add_middleware(RateLimiterMiddleware, config=config)` on line 111 creates a second instance — the `startup()`/`shutdown()` events are wired to the first instance, not the one actually used by the middleware stack; `_calculate_reset_time` uses `time.monotonic()` which is not a wall-clock timestamp clients can use.

## Corrected Code
No correction needed.
