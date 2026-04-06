import time
import math
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ── Configuration ──

RATE: float = 10.0       # tokens per second
BURST: int = 20          # max bucket capacity
CLEANUP_THRESHOLD: float = 600.0  # seconds before stale bucket eviction

WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1"}


# ── Token Bucket ──

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    rate: float = field(default=RATE)
    burst: int = field(default=BURST)

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


# ── Bucket Storage ──

buckets: dict[str, TokenBucket] = {}


def get_or_create_bucket(ip: str) -> TokenBucket:
    now = time.time()

    stale_ips = [k for k, v in buckets.items() if now - v.last_refill > CLEANUP_THRESHOLD]
    for stale_ip in stale_ips:
        del buckets[stale_ip]

    if ip not in buckets:
        buckets[ip] = TokenBucket(
            tokens=float(BURST),
            last_refill=now,
            rate=RATE,
            burst=BURST,
        )

    return buckets[ip]


# ── App ──

app = FastAPI(title="Token Bucket Rate Limiter")


# ── Middleware ──

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):  # type: ignore
    ip = request.client.host if request.client else "unknown"

    if ip in WHITELIST:
        return await call_next(request)

    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume()

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(int(retry_after))},
        )

    response = await call_next(request)

    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(bucket.burst)

    return response


# ── Endpoints ──

@app.get("/")
async def root() -> dict:
    return {"message": "Hello! This endpoint is rate limited."}


@app.get("/status")
async def status(request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"

    if ip in WHITELIST:
        return {
            "ip": ip,
            "whitelisted": True,
            "rate": RATE,
            "burst": BURST,
        }

    bucket = buckets.get(ip)
    remaining = bucket.tokens if bucket else float(BURST)

    return {
        "ip": ip,
        "whitelisted": False,
        "rate": RATE,
        "burst": BURST,
        "remaining_tokens": round(remaining, 2),
        "total_tracked_ips": len(buckets),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
