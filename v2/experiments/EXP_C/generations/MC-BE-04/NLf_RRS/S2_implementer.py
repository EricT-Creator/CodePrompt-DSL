"""Token Bucket Rate Limiter Middleware with FastAPI."""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# ── Token Bucket ─────────────────────────────────────────────────────────────


class TokenBucket:
    __slots__ = ("tokens", "last_refill", "rate", "burst")

    def __init__(self, rate: float, burst: int) -> None:
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()
        self.rate: float = rate
        self.burst: int = burst

    def refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
        self.last_refill = now

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


# ── Configuration ────────────────────────────────────────────────────────────


class RateLimitConfig:
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


# ── Bucket Store ─────────────────────────────────────────────────────────────


class BucketStore:
    def __init__(self, config: RateLimitConfig) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._last_access: dict[str, float] = {}
        self._config = config

    def get_bucket(self, ip: str) -> TokenBucket:
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(self._config.rate, self._config.burst)
        self._last_access[ip] = time.monotonic()
        return self._buckets[ip]

    def evict_stale(self) -> int:
        now = time.monotonic()
        stale = [
            ip
            for ip, last in self._last_access.items()
            if now - last > self._config.bucket_ttl
        ]
        for ip in stale:
            del self._buckets[ip]
            del self._last_access[ip]
        return len(stale)


# ── Middleware ────────────────────────────────────────────────────────────────


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, config: RateLimitConfig | None = None) -> None:
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.store = BucketStore(self.config)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        client_ip = request.client.host if request.client else "unknown"

        # Whitelist bypass
        if client_ip in self.config.whitelist:
            return await call_next(request)

        bucket = self.store.get_bucket(client_ip)

        if bucket.consume():
            response = await call_next(request)
            # Add rate-limit headers
            response.headers["X-RateLimit-Limit"] = str(self.config.burst)
            response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
            reset_time = time.time() + bucket.time_until_full()
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            return response
        else:
            # Rate exceeded
            wait = bucket.time_until_available()
            retry_after = math.ceil(wait)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.config.burst),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + wait)),
                },
            )


# ── Background Cleanup ───────────────────────────────────────────────────────

_cleanup_task: asyncio.Task[None] | None = None


async def _cleanup_loop(store: BucketStore, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        store.evict_stale()


# ── App ──────────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager


config = RateLimitConfig(
    rate=10.0,
    burst=20,
    whitelist={"127.0.0.1", "10.0.0.1"},
    cleanup_interval=300,
    bucket_ttl=3600,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cleanup_task
    middleware_instance = None
    for mw in app.user_middleware:
        if hasattr(mw, "cls") and mw.cls == RateLimiterMiddleware:
            break
    # Start cleanup task using the config's store
    store = BucketStore(config)
    _cleanup_task = asyncio.create_task(_cleanup_loop(store, config.cleanup_interval))
    yield
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Token Bucket Rate Limiter", lifespan=lifespan)
app.add_middleware(RateLimiterMiddleware, config=config)


# ── Demo Endpoints ───────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to the rate-limited API"}


@app.get("/api/data")
async def get_data() -> dict[str, Any]:
    return {"data": list(range(10)), "timestamp": time.time()}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/admin/whitelist")
async def update_whitelist(request: Request) -> dict[str, Any]:
    body = await request.json()
    action: str = body.get("action", "add")
    ip: str = body.get("ip", "")
    if not ip:
        return JSONResponse(status_code=400, content={"detail": "IP required"})

    if action == "add":
        config.whitelist.add(ip)
        return {"message": f"Added {ip} to whitelist", "whitelist": sorted(config.whitelist)}
    elif action == "remove":
        config.whitelist.discard(ip)
        return {"message": f"Removed {ip} from whitelist", "whitelist": sorted(config.whitelist)}
    else:
        return JSONResponse(status_code=400, content={"detail": "Invalid action"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
