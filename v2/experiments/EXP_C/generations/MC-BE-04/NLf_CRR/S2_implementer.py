"""Token Bucket Rate Limiter with FastAPI — per-IP buckets, Retry-After, IP whitelist bypass."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from time import time
from typing import Dict, List, Optional, Set, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# ─── Token Bucket ─────────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    tokens: float
    last_update: float

    def consume(self, tokens: int = 1) -> bool:
        now = time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: int = 1) -> float:
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(
        self,
        capacity: int = 10,
        refill_rate: float = 2.0,
        whitelist: Optional[Set[str]] = None,
    ) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.whitelist: Set[str] = whitelist or set()
        self.buckets: Dict[str, TokenBucket] = {}

    def get_bucket(self, ip: str) -> TokenBucket:
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(
                capacity=self.capacity,
                refill_rate=self.refill_rate,
                tokens=float(self.capacity),
                last_update=time(),
            )
        return self.buckets[ip]

    def is_whitelisted(self, ip: str) -> bool:
        return ip in self.whitelist

    def check_rate_limit(self, ip: str) -> Tuple[bool, float]:
        if self.is_whitelisted(ip):
            return True, 0.0

        bucket = self.get_bucket(ip)
        allowed = bucket.consume(1)

        if allowed:
            return True, 0.0

        retry_after = bucket.time_until_available(1)
        return False, retry_after

    def cleanup_stale(self, max_age: float = 3600.0) -> int:
        """Remove buckets that haven't been updated in max_age seconds."""
        now = time()
        stale = [ip for ip, b in self.buckets.items() if now - b.last_update > max_age]
        for ip in stale:
            del self.buckets[ip]
        return len(stale)


# ─── IP Extraction ────────────────────────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "unknown"


# ─── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        capacity: int = 10,
        refill_rate: float = 2.0,
        whitelist: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(capacity, refill_rate, whitelist)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = get_client_ip(request)
        allowed, retry_after = self.limiter.check_rate_limit(client_ip)

        if not allowed:
            retry_after_int = int(math.ceil(retry_after))
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": retry_after_int,
                    "limit": self.limiter.capacity,
                },
                headers={
                    "Retry-After": str(retry_after_int),
                    "X-RateLimit-Limit": str(self.limiter.capacity),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        bucket = self.limiter.get_bucket(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.capacity)
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(bucket.tokens)))

        return response


# ─── Application ──────────────────────────────────────────────────────────────

WHITELIST_IPS: Set[str] = {"127.0.0.1", "::1", "10.0.0.1"}

app = FastAPI(title="Token Bucket Rate Limiter")

app.add_middleware(
    RateLimitMiddleware,
    capacity=10,
    refill_rate=2.0,
    whitelist=WHITELIST_IPS,
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    return {"message": "Welcome to the rate-limited API"}


@app.get("/api/data")
async def get_data() -> dict:
    return {
        "data": [
            {"id": 1, "name": "Item One", "value": 42},
            {"id": 2, "name": "Item Two", "value": 84},
            {"id": 3, "name": "Item Three", "value": 126},
        ],
        "total": 3,
    }


@app.get("/api/status")
async def api_status(request: Request) -> dict:
    client_ip = get_client_ip(request)
    return {
        "client_ip": client_ip,
        "is_whitelisted": client_ip in WHITELIST_IPS,
        "rate_limit": {
            "capacity": 10,
            "refill_rate": 2.0,
            "unit": "tokens/second",
        },
    }


@app.get("/api/heavy")
async def heavy_endpoint() -> dict:
    """Simulate a resource-intensive endpoint."""
    import asyncio
    await asyncio.sleep(0.5)
    return {"result": "heavy computation complete", "duration_ms": 500}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
