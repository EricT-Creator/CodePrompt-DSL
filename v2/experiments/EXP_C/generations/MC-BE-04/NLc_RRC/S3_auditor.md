# MC-BE-04 Code Review Report (NLc_RRC)

## Constraint Review

- C1 (Python + FastAPI): PASS — Uses Python with FastAPI framework (line 2477)
- C2 (Token Bucket, no counter): PASS — Implements proper Token Bucket algorithm with token refill based on elapsed time (lines 2500-2514)
- C3 (stdlib + fastapi, no Redis): FAIL — Uses `pydantic` (line 2479) which is a third-party package, not in stdlib
- C4 (Single file): PASS — All code delivered in a single Python file
- C5 (429 + Retry-After + whitelist): PASS — Returns HTTP 429 with Retry-After header (lines 2569-2573), supports IP whitelist bypass (lines 2558-2560)
- C6 (Code only): PASS — Output contains code only, no explanation text

## Functionality Assessment (0-5)
Score: 4 — The code correctly implements Token Bucket rate limiting with proper token refill calculation, returns HTTP 429 with Retry-After header when rate exceeded, supports IP whitelist bypass, and uses only stdlib + fastapi. However, it violates C3 by using pydantic which is not in Python standard library.

## Corrected Code

```py
import time
import math
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ─── Configuration ────────────────────────────────────────────────────────────

RATE: float = 10.0          # tokens per second
BURST: int = 20             # max bucket capacity
CLEANUP_THRESHOLD: float = 600.0  # seconds before stale bucket cleanup

WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1"}


# ─── Token Bucket ─────────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    rate: float = RATE
    burst: int = BURST

    def refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self) -> tuple[bool, float]:
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        else:
            deficit = 1.0 - self.tokens
            retry_after = math.ceil(deficit / self.rate)
            return False, float(retry_after)


# ─── Bucket Store ─────────────────────────────────────────────────────────────

buckets: dict[str, TokenBucket] = {}


def get_or_create_bucket(ip: str) -> TokenBucket:
    if ip not in buckets:
        buckets[ip] = TokenBucket(tokens=float(BURST), last_refill=time.time())
    return buckets[ip]


def cleanup_stale_buckets() -> None:
    now = time.time()
    stale = [ip for ip, b in buckets.items() if now - b.last_refill > CLEANUP_THRESHOLD]
    for ip in stale:
        del buckets[ip]


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Token Bucket Rate Limiter")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"

    if ip in WHITELIST:
        response = await call_next(request)
        return response

    if len(buckets) > 10000:
        cleanup_stale_buckets()

    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume()

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(int(retry_after))},
        )

    response = await call_next(request)
    return response


@app.get("/")
async def root() -> dict:
    return {"message": "Hello! This endpoint is rate-limited."}


@app.get("/status")
async def status(request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"
    whitelisted = ip in WHITELIST

    if whitelisted or ip not in buckets:
        tokens_remaining = float(BURST)
    else:
        bucket = buckets[ip]
        bucket.refill()
        tokens_remaining = bucket.tokens

    return {
        "ip": ip,
        "whitelisted": whitelisted,
        "tokens_remaining": round(tokens_remaining, 2),
        "rate": RATE,
        "burst": BURST,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
