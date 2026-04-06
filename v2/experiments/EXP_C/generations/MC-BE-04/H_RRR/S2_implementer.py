"""Rate Limiter Middleware — MC-BE-04 (H × RRR)"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Configuration ──
DEFAULT_RATE: float = 10.0    # tokens per second
DEFAULT_BURST: float = 20.0   # max bucket capacity

# ── IP Whitelist ──
IP_WHITELIST: set[str] = {"127.0.0.1", "::1"}

# ── Token Bucket ──
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
        """Try to consume one token. Returns (allowed, retry_after_seconds)."""
        bucket = self.get_or_create(ip)
        now = time.monotonic()

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
        """Periodically clean up stale buckets."""
        self._request_count += 1
        if self._request_count % 1000 != 0:
            return
        now = time.monotonic()
        stale_ips: list[str] = []
        for ip, bucket in self._buckets.items():
            if now - bucket.last_access > 3600:  # 1 hour
                stale_ips.append(ip)
        for ip in stale_ips:
            del self._buckets[ip]

# ── IP Extraction ──
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

# ── Application ──
app = FastAPI(title="Rate Limiter API")
bucket_store = BucketStore(rate=DEFAULT_RATE, burst=DEFAULT_BURST)

# ── Middleware ──
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
    client_ip = get_client_ip(request)

    # Check whitelist
    if client_ip in IP_WHITELIST:
        response = await call_next(request)
        return response

    # Consume token
    allowed, retry_after = bucket_store.consume(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(math.ceil(retry_after))},
        )

    response = await call_next(request)

    # Add rate limit headers to successful responses
    bucket = bucket_store.get_or_create(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))

    return response

# ── Pydantic Models ──
class HealthResponse(BaseModel):
    status: str
    message: str

class RateLimitInfoResponse(BaseModel):
    rate: float
    burst: float
    your_ip: str
    tokens_remaining: float
    whitelisted: bool

# ── Routes ──
@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    return HealthResponse(status="ok", message="Rate-limited API is running")

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", message="Service is healthy")

@app.get("/rate-limit-info", response_model=RateLimitInfoResponse)
async def rate_limit_info(request: Request) -> RateLimitInfoResponse:
    client_ip = get_client_ip(request)
    bucket = bucket_store.get_or_create(client_ip)

    # Recalculate current tokens
    now = time.monotonic()
    elapsed = now - bucket.last_access
    current_tokens = min(bucket.tokens + elapsed * bucket_store.rate, bucket_store.burst)

    return RateLimitInfoResponse(
        rate=bucket_store.rate,
        burst=bucket_store.burst,
        your_ip=client_ip,
        tokens_remaining=round(current_tokens, 2),
        whitelisted=client_ip in IP_WHITELIST,
    )

@app.post("/whitelist/{ip}")
async def add_to_whitelist(ip: str) -> dict[str, str]:
    IP_WHITELIST.add(ip)
    return {"detail": f"IP {ip} added to whitelist"}

@app.delete("/whitelist/{ip}")
async def remove_from_whitelist(ip: str) -> dict[str, str]:
    IP_WHITELIST.discard(ip)
    return {"detail": f"IP {ip} removed from whitelist"}
