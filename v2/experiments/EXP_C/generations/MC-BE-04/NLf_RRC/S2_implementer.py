"""Token Bucket Rate Limiter Middleware — FastAPI."""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


# ── Configuration ────────────────────────────────────────────────────────────


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
        self.rate: float = rate
        self.burst: int = burst
        self.whitelist: set[str] = whitelist or {"127.0.0.1"}
        self.cleanup_interval: int = cleanup_interval
        self.bucket_ttl: int = bucket_ttl


# ── Token Bucket ─────────────────────────────────────────────────────────────


class TokenBucket:
    __slots__ = ("tokens", "last_refill", "rate", "burst", "last_access")

    def __init__(self, rate: float, burst: int) -> None:
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()
        self.rate: float = rate
        self.burst: int = burst
        self.last_access: float = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
        self.last_refill = now
        self.last_access = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> int:
        deficit = 1.0 - self.tokens
        wait_seconds = deficit / self.rate
        return max(1, math.ceil(wait_seconds))

    def remaining(self) -> int:
        return max(0, int(self.tokens))

    def reset_time(self) -> int:
        if self.tokens >= float(self.burst):
            return int(time.time())
        deficit = float(self.burst) - self.tokens
        return int(time.time() + deficit / self.rate)


# ── Bucket Store ─────────────────────────────────────────────────────────────

bucket_store: dict[str, TokenBucket] = {}


# ── Middleware ───────────────────────────────────────────────────────────────


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, config: RateLimitConfig | None = None) -> None:
        super().__init__(app)
        self.config: RateLimitConfig = config or RateLimitConfig()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # Whitelist bypass
        if client_ip in self.config.whitelist:
            response = await call_next(request)
            return response

        # Get or create bucket
        bucket = bucket_store.get(client_ip)
        if bucket is None:
            bucket = TokenBucket(rate=self.config.rate, burst=self.config.burst)
            bucket_store[client_ip] = bucket

        # Try to consume token
        if bucket.consume():
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.config.burst)
            response.headers["X-RateLimit-Remaining"] = str(bucket.remaining())
            response.headers["X-RateLimit-Reset"] = str(bucket.reset_time())
            return response
        else:
            retry = bucket.retry_after()
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry,
                },
                headers={
                    "Retry-After": str(retry),
                    "X-RateLimit-Limit": str(self.config.burst),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(bucket.reset_time()),
                },
            )


# ── App ──────────────────────────────────────────────────────────────────────

config = RateLimitConfig(
    rate=10.0,
    burst=20,
    whitelist={"127.0.0.1", "10.0.0.1"},
    cleanup_interval=300,
    bucket_ttl=3600,
)

app = FastAPI(title="Token Bucket Rate Limiter")
app.add_middleware(RateLimiterMiddleware, config=config)

cleanup_task: asyncio.Task[None] | None = None


async def cleanup_stale_buckets() -> None:
    while True:
        await asyncio.sleep(config.cleanup_interval)
        now = time.monotonic()
        stale_ips: list[str] = []
        for ip, bucket in bucket_store.items():
            if now - bucket.last_access > config.bucket_ttl:
                stale_ips.append(ip)
        for ip in stale_ips:
            bucket_store.pop(ip, None)


@app.on_event("startup")
async def startup() -> None:
    global cleanup_task
    cleanup_task = asyncio.create_task(cleanup_stale_buckets())


@app.on_event("shutdown")
async def shutdown() -> None:
    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


# ── Demo Endpoints ───────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to the rate-limited API"}


@app.get("/api/data")
async def get_data() -> dict[str, Any]:
    return {
        "data": [
            {"id": 1, "value": "item_1"},
            {"id": 2, "value": "item_2"},
            {"id": 3, "value": "item_3"},
        ]
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/stats")
async def stats() -> dict[str, Any]:
    return {
        "total_buckets": len(bucket_store),
        "config": {
            "rate": config.rate,
            "burst": config.burst,
            "whitelist": list(config.whitelist),
        },
    }


@app.post("/admin/whitelist")
async def update_whitelist(request: Request) -> dict[str, Any]:
    body = await request.json()
    action: str = body.get("action", "add")
    ip: str = body.get("ip", "")

    if not ip:
        return {"error": "IP address is required"}

    if action == "add":
        config.whitelist.add(ip)
        return {"message": f"Added {ip} to whitelist", "whitelist": list(config.whitelist)}
    elif action == "remove":
        config.whitelist.discard(ip)
        return {"message": f"Removed {ip} from whitelist", "whitelist": list(config.whitelist)}
    else:
        return {"error": "Action must be 'add' or 'remove'"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
