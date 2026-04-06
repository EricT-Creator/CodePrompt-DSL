import time
import math
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---- Configuration ----

RATE: float = 10.0       # tokens per second
BURST: int = 20          # max bucket capacity
CLEANUP_THRESHOLD: float = 600.0  # 10 minutes

WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1"}


# ---- Token Bucket ----

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    last_access: float

    def refill(self, rate: float, burst: int) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(burst, self.tokens + elapsed * rate)
        self.last_refill = now
        self.last_access = now

    def consume(self, rate: float, burst: int) -> tuple[bool, float]:
        self.refill(rate, burst)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        else:
            deficit = 1.0 - self.tokens
            retry_after = math.ceil(deficit / rate)
            return False, float(retry_after)


# ---- Bucket Store ----

buckets: dict[str, TokenBucket] = {}


def get_or_create_bucket(ip: str) -> TokenBucket:
    if ip not in buckets:
        now = time.time()
        buckets[ip] = TokenBucket(tokens=float(BURST), last_refill=now, last_access=now)
    return buckets[ip]


def cleanup_stale_buckets() -> int:
    now = time.time()
    stale = [ip for ip, b in buckets.items() if now - b.last_access > CLEANUP_THRESHOLD]
    for ip in stale:
        del buckets[ip]
    return len(stale)


# ---- FastAPI App ----

app = FastAPI(title="Token Bucket Rate Limiter")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
    ip = request.client.host if request.client else "unknown"

    if ip in WHITELIST:
        return await call_next(request)

    # Periodic cleanup (every request, lightweight check)
    if len(buckets) > 1000:
        cleanup_stale_buckets()

    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume(RATE, BURST)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(int(retry_after))},
        )

    response = await call_next(request)

    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(BURST)

    return response


# ---- Endpoints ----

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello! This endpoint is rate-limited."}


@app.get("/status")
async def status(request: Request) -> dict[str, Any]:
    ip = request.client.host if request.client else "unknown"
    is_whitelisted = ip in WHITELIST

    info: dict[str, Any] = {
        "ip": ip,
        "whitelisted": is_whitelisted,
        "rate": RATE,
        "burst": BURST,
    }

    if not is_whitelisted and ip in buckets:
        bucket = buckets[ip]
        # Lazy refill to show accurate tokens
        now = time.time()
        elapsed = now - bucket.last_refill
        current_tokens = min(BURST, bucket.tokens + elapsed * RATE)
        info["remaining_tokens"] = round(current_tokens, 2)
        info["last_refill"] = bucket.last_refill

    return info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
