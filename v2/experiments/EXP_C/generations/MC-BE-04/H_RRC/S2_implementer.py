"""Rate Limiter Middleware — MC-BE-04 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Configuration ───

DEFAULT_RATE: float = 10.0   # tokens per second
DEFAULT_BURST: float = 20.0  # max bucket capacity

IP_WHITELIST: set[str] = {
    "127.0.0.1",
    "::1",
}

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
            self._buckets[ip] = TokenBucket(
                tokens=self.burst,
                last_access=time.monotonic(),
            )
        return self._buckets[ip]

    def consume(self, ip: str) -> tuple[bool, float]:
        bucket = self.get_or_create(ip)
        now = time.monotonic()
        elapsed = now - bucket.last_access

        # Refill tokens
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
            stale: list[str] = [
                ip
                for ip, bucket in self._buckets.items()
                if now - bucket.last_access > 3600
            ]
            for ip in stale:
                del self._buckets[ip]


# ─── IP Extraction ───


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ─── Application ───

app = FastAPI(title="Rate Limiter Middleware")
bucket_store = BucketStore(rate=DEFAULT_RATE, burst=DEFAULT_BURST)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    client_ip = get_client_ip(request)

    # Skip whitelisted IPs
    if client_ip in IP_WHITELIST:
        response = await call_next(request)
        return response

    allowed, retry_after = bucket_store.consume(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(math.ceil(retry_after))},
        )

    response = await call_next(request)

    # Add informational rate-limit headers
    bucket = bucket_store.get_or_create(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))

    return response


# ─── Response Models ───


class StatusResponse(BaseModel):
    status: str
    rate: float
    burst: float


class RateLimitInfoResponse(BaseModel):
    ip: str
    tokens_remaining: float
    rate: float
    burst: float


# ─── Routes ───


@app.get("/", response_model=StatusResponse)
async def root() -> StatusResponse:
    return StatusResponse(status="ok", rate=bucket_store.rate, burst=bucket_store.burst)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/rate-limit-info", response_model=RateLimitInfoResponse)
async def rate_limit_info(request: Request) -> RateLimitInfoResponse:
    client_ip = get_client_ip(request)
    bucket = bucket_store.get_or_create(client_ip)
    # Recalculate current tokens without consuming
    now = time.monotonic()
    elapsed = now - bucket.last_access
    current_tokens = min(bucket.tokens + elapsed * bucket_store.rate, bucket_store.burst)
    return RateLimitInfoResponse(
        ip=client_ip,
        tokens_remaining=round(current_tokens, 2),
        rate=bucket_store.rate,
        burst=bucket_store.burst,
    )


@app.get("/test")
async def test_endpoint() -> dict[str, str]:
    return {"message": "This endpoint is rate-limited"}
