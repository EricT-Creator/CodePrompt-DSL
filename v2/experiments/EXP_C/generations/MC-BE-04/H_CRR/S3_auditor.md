## Constraint Review
- C1 [L]Python [F]FastAPI: PASS — Written in Python using FastAPI (`from fastapi import FastAPI, Request, Response`) with Starlette middleware for request interception.
- C2 [ALGO]TOKEN_BUCKET [!A]NO_COUNTER: PASS — Implements proper token bucket algorithm via `TokenBucket` dataclass with `capacity`, `tokens`, `rate`, `last_update` fields. `replenish()` adds tokens based on elapsed time, `try_consume()` deducts 1.0 token per request. Not a simple counter.
- C3 [D]STDLIB+FASTAPI [!D]NO_REDIS: PASS — Uses stdlib (`time`, `dataclasses`) and FastAPI ecosystem (`fastapi`, `starlette.middleware.base`, `pydantic`). Starlette is FastAPI's built-in dependency. No Redis imported.
- C4 [O]SINGLE_FILE: PASS — All code (token bucket logic, middleware, endpoints) resides in a single file.
- C5 [RESP]429_RETRY_AFTER [WL]IP: PASS — Rate-limited requests return HTTP 429 with `Retry-After` header calculated from tokens needed. IP whitelist (`RATE_LIMIT_WHITELIST = {"127.0.0.1", "::1"}`) bypasses rate limiting for whitelisted IPs.
- C6 [OUT]CODE_ONLY: PASS — Output is pure code with no extraneous narrative.

## Functionality Assessment (0-5)
Score: 5 — Complete rate limiter middleware with: per-IP token bucket algorithm, configurable rate (10 tokens/sec) and burst capacity (20), monotonic clock for timing, automatic token replenishment, `Retry-After` header with ceiling calculation, `X-RateLimit-Limit`/`X-RateLimit-Remaining` headers on all responses, IP whitelist bypass, stale bucket cleanup endpoint, and status endpoint showing configuration.

## Corrected Code
No correction needed.
