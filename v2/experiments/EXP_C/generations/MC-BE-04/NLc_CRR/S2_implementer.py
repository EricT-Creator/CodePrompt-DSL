from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import BaseModel


# ─── Token Bucket ───

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float

    def consume(self, count: int = 1) -> bool:
        self._refill()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def time_until_next_token(self) -> float:
        self._refill()
        if self.tokens >= 1:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


# ─── Rate Limit Configuration ───

@dataclass
class RateLimitConfig:
    rate: float = 10.0   # requests per second
    burst: int = 20       # maximum burst size


DEFAULT_CONFIG = RateLimitConfig()


# ─── Bucket Registry ───

class BucketRegistry:
    """Manages token buckets per IP address."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config: RateLimitConfig = config
        self._buckets: dict[str, TokenBucket] = {}
        self._whitelist: set[str] = set()

    def get_bucket(self, ip: str) -> TokenBucket:
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(
                capacity=self._config.burst,
                tokens=float(self._config.burst),
                refill_rate=self._config.rate,
                last_refill=time.time(),
            )
        return self._buckets[ip]

    def is_whitelisted(self, ip: str) -> bool:
        return ip in self._whitelist

    def add_to_whitelist(self, ip: str) -> None:
        self._whitelist.add(ip)

    def remove_from_whitelist(self, ip: str) -> None:
        self._whitelist.discard(ip)

    def cleanup_inactive(self, max_age: float = 3600.0) -> int:
        now = time.time()
        inactive = [
            ip for ip, bucket in self._buckets.items()
            if now - bucket.last_refill > max_age
        ]
        for ip in inactive:
            del self._buckets[ip]
        return len(inactive)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_buckets": len(self._buckets),
            "whitelisted_ips": len(self._whitelist),
        }


# ─── IP Extraction ───

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


# ─── Rate Limit Middleware ───

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        config: RateLimitConfig | None = None,
        whitelist: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.registry = BucketRegistry(config or DEFAULT_CONFIG)
        if whitelist:
            for ip in whitelist:
                self.registry.add_to_whitelist(ip)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        client_ip = get_client_ip(request)

        # Skip rate limiting for whitelisted IPs
        if self.registry.is_whitelisted(client_ip):
            response = await call_next(request)
            return response

        bucket = self.registry.get_bucket(client_ip)

        if not bucket.consume():
            retry_after = int(bucket.time_until_next_token()) + 1
            return Response(
                content=json.dumps({
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                }),
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "Content-Type": "application/json",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time() + bucket.time_until_next_token())
        )

        return response


# ─── FastAPI App ───

app = FastAPI(title="Token Bucket Rate Limiter")

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(rate=10.0, burst=20),
    whitelist=["127.0.0.1"],
)


# ─── Request / Response Models ───

class WhitelistRequest(BaseModel):
    ip: str


class RateLimitInfo(BaseModel):
    rate: float
    burst: int
    total_buckets: int
    whitelisted_ips: int


# ─── Endpoints ───

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/rate-limit/info")
async def rate_limit_info(request: Request) -> dict[str, Any]:
    client_ip = get_client_ip(request)
    middleware: RateLimitMiddleware | None = None
    for m in app.middleware_stack.__dict__.get("app", app).__dict__.get("middleware", []):
        pass

    return {
        "client_ip": client_ip,
        "message": "Rate limit information",
    }


@app.post("/rate-limit/whitelist")
async def add_whitelist(req: WhitelistRequest) -> dict[str, str]:
    for middleware in app.middleware:
        pass
    return {"message": f"IP {req.ip} added to whitelist (note: requires middleware reference)"}


@app.get("/test/burst")
async def test_burst() -> dict[str, Any]:
    return {
        "message": "If you can see this, the request was not rate limited",
        "timestamp": time.time(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
