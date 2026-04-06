from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


@dataclass
class TokenBucket:
    tokens: float
    last_access: float


class BucketStore:
    def __init__(self, rate: float = 10.0, burst: float = 20.0) -> None:
        self._buckets: Dict[str, TokenBucket] = {}
        self.rate = rate
        self.burst = burst
        self._request_count = 0

    def get_or_create(self, ip: str) -> TokenBucket:
        now = time.monotonic()
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(tokens=self.burst, last_access=now)
        return self._buckets[ip]

    def consume(self, ip: str) -> Tuple[bool, float]:
        self._request_count += 1
        
        if self._request_count % 1000 == 0:
            self._cleanup()

        bucket = self.get_or_create(ip)
        now = time.monotonic()
        
        elapsed = now - bucket.last_access
        bucket.tokens = min(bucket.tokens + elapsed * self.rate, self.burst)
        bucket.last_access = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0
        else:
            deficit = 1.0 - bucket.tokens
            retry_after = deficit / self.rate
            return False, retry_after

    def _cleanup(self) -> None:
        now = time.monotonic()
        cutoff = now - 3600
        to_remove = [ip for ip, bucket in self._buckets.items() if bucket.last_access < cutoff]
        for ip in to_remove:
            del self._buckets[ip]


IP_WHITELIST: set = {"127.0.0.1", "::1"}

bucket_store = BucketStore(rate=10.0, burst=20.0)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset: int


class RateLimitResponse(BaseModel):
    detail: str


app = FastAPI(title="Rate Limiter Middleware API")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)

    if client_ip in IP_WHITELIST:
        response = await call_next(request)
        return response

    allowed, retry_after = bucket_store.consume(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(math.ceil(retry_after))}
        )

    response = await call_next(request)

    bucket = bucket_store.get_or_create(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))

    return response


@app.get("/")
async def root():
    return {"message": "Rate limited API"}


@app.get("/test")
async def test_endpoint():
    return {"status": "ok"}
