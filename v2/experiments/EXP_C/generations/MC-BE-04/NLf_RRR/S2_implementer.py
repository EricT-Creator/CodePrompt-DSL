"""Token Bucket Rate Limiter Middleware — FastAPI implementation."""

from __future__ import annotations

import asyncio
import math
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


# ─── Configuration ────────────────────────────────────────────


class RateLimitConfig:
    __slots__ = ("rate", "burst", "whitelist", "cleanup_interval", "bucket_ttl")

    def __init__(
        self,
        rate: float = 10.0,
        burst: int = 20,
        whitelist: set[str] | None = None,
        cleanup_interval: int = 300,
        bucket_ttl: int = 3600,
    ) -> None:
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or {"127.0.0.1"}
        self.cleanup_interval = cleanup_interval
        self.bucket_ttl = bucket_ttl


# ─── Token Bucket ─────────────────────────────────────────────


class TokenBucket:
    __slots__ = ("tokens", "last_refill", "rate", "burst", "last_access")

    def __init__(self, rate: float, burst: int) -> None:
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()
        self.rate: float = rate
        self.burst: int = burst
        self.last_access: float = time.monotonic()

    def refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
        self.last_refill = now
        self.last_access = now

    def consume(self) -> bool:
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def time_until_available(self) -> float:
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.rate

    def time_until_full(self) -> float:
        deficit = float(self.burst) - self.tokens
        if deficit <= 0:
            return 0.0
        return deficit / self.rate


# ─── Bucket Store ─────────────────────────────────────────────


class BucketStore:
    def __init__(self, config: RateLimitConfig) -> None:
        self.buckets: dict[str, TokenBucket] = {}
        self.config = config

    def get_bucket(self, ip: str) -> TokenBucket:
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.config.rate, self.config.burst)
        return self.buckets[ip]

    def cleanup_stale(self) -> int:
        now = time.monotonic()
        stale_keys = [
            ip
            for ip, bucket in self.buckets.items()
            if (now - bucket.last_access) > self.config.bucket_ttl
        ]
        for key in stale_keys:
            del self.buckets[key]
        return len(stale_keys)


# ─── Middleware ────────────────────────────────────────────────

config = RateLimitConfig()
store = BucketStore(config)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # Whitelist bypass
        if client_ip in config.whitelist:
            response = await call_next(request)
            return response

        bucket = store.get_bucket(client_ip)

        if bucket.consume():
            response = await call_next(request)
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(config.burst)
            response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
            reset_time = time.time() + bucket.time_until_full()
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            return response
        else:
            wait = bucket.time_until_available()
            retry_after = math.ceil(wait)
            reset_time = time.time() + bucket.time_until_full()
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(config.burst),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                },
            )


# ─── Background Cleanup Task ─────────────────────────────────

cleanup_task: asyncio.Task[None] | None = None


async def cleanup_loop() -> None:
    while True:
        await asyncio.sleep(config.cleanup_interval)
        store.cleanup_stale()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cleanup_task
    cleanup_task = asyncio.create_task(cleanup_loop())
    yield
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(title="Token Bucket Rate Limiter", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello! This endpoint is rate-limited."}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
async def stats() -> dict[str, Any]:
    return {
        "active_buckets": len(store.buckets),
        "config": {
            "rate": config.rate,
            "burst": config.burst,
            "whitelist": list(config.whitelist),
            "cleanup_interval": config.cleanup_interval,
            "bucket_ttl": config.bucket_ttl,
        },
    }


@app.post("/admin/whitelist/add")
async def add_to_whitelist(ip: str) -> dict[str, str]:
    config.whitelist.add(ip)
    return {"message": f"IP {ip} added to whitelist"}


@app.post("/admin/whitelist/remove")
async def remove_from_whitelist(ip: str) -> dict[str, str]:
    config.whitelist.discard(ip)
    return {"message": f"IP {ip} removed from whitelist"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
