"""Rate Limiter Middleware — MC-BE-04 (H × RRS)"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Config ───
DEFAULT_RATE: float = 10.0   # tokens per second
DEFAULT_BURST: float = 20.0  # max bucket capacity

IP_WHITELIST: set[str] = {"127.0.0.1", "::1"}


# ─── Token Bucket ───
@dataclass
class TokenBucket:
    tokens: float
    last_access: float


class BucketStore:
    def __init__(self, rate: float = DEFAULT_RATE, burst: float = DEFAULT_BURST) -> None:
        self.rate: float = rate
        self.burst: float = burst
        self._buckets: dict[str, TokenBucket] = {}
        self._request_count: int = 0

    def get_or_create(self, ip: str) -> TokenBucket:
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(tokens=self.burst, last_access=time.monotonic())
        return self._buckets[ip]

    def consume(self, ip: str) -> tuple[bool, float]:
        now = time.monotonic()
        bucket = self.get_or_create(ip)

        # Lazy refill
        elapsed = now - bucket.last_access
        bucket.tokens = min(bucket.tokens + elapsed * self.rate, self.burst)
        bucket.last_access = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            self._maybe_cleanup()
            return True, 0.0
        else:
            deficit = 1.0 - bucket.tokens
            retry_after = deficit / self.rate
            self._maybe_cleanup()
            return False, retry_after

    def _maybe_cleanup(self) -> None:
        self._request_count += 1
        if self._request_count % 1000 == 0:
            now = time.monotonic()
            stale_ips = [
                ip for ip, bucket in self._buckets.items()
                if now - bucket.last_access > 3600
            ]
            for ip in stale_ips:
                del self._buckets[ip]


# ─── IP extraction ───
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ─── App ───
app = FastAPI(title="Rate Limiter Middleware")
bucket_store = BucketStore(rate=DEFAULT_RATE, burst=DEFAULT_BURST)


# ─── Middleware ───
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
    client_ip = get_client_ip(request)

    # Whitelist bypass
    if client_ip in IP_WHITELIST:
        return await call_next(request)

    # Consume token
    allowed, retry_after = bucket_store.consume(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(math.ceil(retry_after))},
        )

    response = await call_next(request)

    # Add rate limit info headers
    bucket = bucket_store.get_or_create(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))

    return response


# ─── Demo routes ───
class StatusResponse(BaseModel):
    message: str
    client_ip: str


@app.get("/", response_model=StatusResponse)
async def root(request: Request) -> StatusResponse:
    return StatusResponse(message="OK", client_ip=get_client_ip(request))


@app.get("/resource", response_model=StatusResponse)
async def resource(request: Request) -> StatusResponse:
    return StatusResponse(message="Resource accessed", client_ip=get_client_ip(request))


class RateLimitConfigResponse(BaseModel):
    rate: float
    burst: float
    whitelisted_ips: list[str]


@app.get("/rate-limit-config", response_model=RateLimitConfigResponse)
async def rate_limit_config() -> RateLimitConfigResponse:
    return RateLimitConfigResponse(
        rate=bucket_store.rate,
        burst=bucket_store.burst,
        whitelisted_ips=sorted(IP_WHITELIST),
    )
