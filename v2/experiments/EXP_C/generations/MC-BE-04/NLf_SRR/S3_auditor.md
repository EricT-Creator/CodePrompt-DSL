## Constraint Review
- C1 (Python + FastAPI): PASS — Code uses `from fastapi import FastAPI, Request` and defines `app = FastAPI(title="Token-Bucket Rate Limiter")`.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` class implements the token bucket algorithm with `rate`, `capacity`, `tokens` fields, `_refill()` method that adds `elapsed * self.rate` tokens, and `consume()` that deducts tokens. This is not a simple counter or fixed window.
- C3 (stdlib + fastapi, no Redis): PASS — Only imports from Python standard library (`asyncio`, `math`, `time`, `typing`), `fastapi`, and `uvicorn`. No Redis, memcached, or external storage.
- C4 (Single file): PASS — All code is contained in a single Python file.
- C5 (429 + Retry-After + whitelist): PASS — Returns HTTP 429 with `"Retry-After": str(retry_after)` header when rate exceeded. IP whitelist is implemented: `IP_WHITELIST: set[str] = {"127.0.0.1", "::1"}` with bypass check `if ip in IP_WHITELIST`. Also includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.
- C6 (Code only): PASS — The file contains only code, no explanation text.

## Functionality Assessment (0-5)
Score: 5 — Robust token bucket rate limiter with per-IP bucket management, automatic refill based on elapsed time, middleware integration, X-Forwarded-For / X-Real-IP header support, IPv6 normalization, periodic stale bucket cleanup, whitelist add/remove endpoints, status endpoint showing remaining tokens, and comprehensive rate limit headers on all responses.

## Corrected Code
No correction needed.
