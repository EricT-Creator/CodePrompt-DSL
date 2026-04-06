import math
import threading
import time
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

RATE_PER_SECOND = 1.5
BURST_CAPACITY = 6.0
WHITELIST_IPS = {"127.0.0.1", "::1"}
EXEMPT_PATHS = {"/status", "/docs", "/redoc", "/openapi.json"}


@dataclass
class Bucket:
    tokens: float
    updated_at: float


class TokenBucketLimiter:
    def __init__(self, rate: float, burst: float, whitelist: set[str] | None = None) -> None:
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or set()
        self.buckets: dict[str, Bucket] = {}
        self.lock = threading.Lock()

    def _refill(self, bucket: Bucket, now: float) -> None:
        elapsed = max(0.0, now - bucket.updated_at)
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
        bucket.updated_at = now

    def _get_or_create_bucket(self, ip: str) -> Bucket:
        bucket = self.buckets.get(ip)
        if bucket is None:
            bucket = Bucket(tokens=self.burst, updated_at=time.monotonic())
            self.buckets[ip] = bucket
        return bucket

    def consume(self, ip: str) -> tuple[bool, int, float]:
        if ip in self.whitelist:
            return True, 0, self.burst

        with self.lock:
            bucket = self._get_or_create_bucket(ip)
            now = time.monotonic()
            self._refill(bucket, now)

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0, round(bucket.tokens, 2)

            missing = 1.0 - bucket.tokens
            retry_after = max(1, math.ceil(missing / self.rate))
            return False, retry_after, round(bucket.tokens, 2)

    def current_tokens(self, ip: str) -> float:
        if ip in self.whitelist:
            return self.burst

        with self.lock:
            bucket = self._get_or_create_bucket(ip)
            self._refill(bucket, time.monotonic())
            return round(bucket.tokens, 2)


limiter = TokenBucketLimiter(RATE_PER_SECOND, BURST_CAPACITY, WHITELIST_IPS)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = get_client_ip(request)

    if request.url.path in EXEMPT_PATHS or ip in WHITELIST_IPS:
        return await call_next(request)

    allowed, retry_after, tokens_left = limiter.consume(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={
                "detail": "Rate limit exceeded",
                "ip": ip,
                "retry_after": retry_after,
                "tokens_left": tokens_left,
            },
        )

    return await call_next(request)


@app.get("/")
async def index(request: Request):
    ip = get_client_ip(request)
    return {
        "message": "Request accepted",
        "ip": ip,
        "tokens_left": limiter.current_tokens(ip),
    }


@app.get("/status")
async def status(request: Request):
    ip = get_client_ip(request)
    return {
        "ip": ip,
        "rate_per_second": RATE_PER_SECOND,
        "burst_capacity": BURST_CAPACITY,
        "whitelisted": ip in WHITELIST_IPS,
        "tokens_left": limiter.current_tokens(ip),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
