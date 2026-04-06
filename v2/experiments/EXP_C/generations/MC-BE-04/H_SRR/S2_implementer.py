"""MC-BE-04: Token-Bucket Rate Limiter Middleware — no Redis, no counter algo, IP whitelist"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ── Token Bucket ────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    rate: float          # tokens per second
    burst: int           # max capacity
    tokens: float = 0.0
    last_refresh: float = 0.0

    def __post_init__(self) -> None:
        if self.tokens == 0.0 and self.last_refresh == 0.0:
            self.tokens = float(self.burst)
            self.last_refresh = time.monotonic()

    def _refresh(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refresh
        if elapsed > 0:
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refresh = now

    def consume(self, n: float = 1.0) -> Tuple[bool, Optional[float]]:
        """Try to consume n tokens. Returns (allowed, retry_after_seconds)."""
        self._refresh()
        if self.tokens >= n:
            self.tokens -= n
            return True, None
        needed = n - self.tokens
        wait = needed / self.rate if self.rate > 0 else 60.0
        return False, wait

    def get_remaining(self) -> float:
        self._refresh()
        return self.tokens


# ── IP Bucket Manager ───────────────────────────────────────────────

class IPBucketManager:
    def __init__(
        self,
        default_rate: float = 10.0,
        default_burst: int = 20,
    ) -> None:
        self.default_rate = default_rate
        self.default_burst = default_burst
        self._buckets: Dict[str, TokenBucket] = {}
        self._last_access: Dict[str, float] = {}
        self._whitelist: Set[str] = set()
        self._custom: Dict[str, Dict[str, Any]] = {}

    def get_bucket(self, ip: str) -> TokenBucket:
        self._last_access[ip] = time.monotonic()
        if ip not in self._buckets:
            cfg = self._custom.get(ip, {})
            rate = cfg.get("rate", self.default_rate)
            burst = cfg.get("burst", self.default_burst)
            self._buckets[ip] = TokenBucket(rate=rate, burst=burst)
        return self._buckets[ip]

    def is_whitelisted(self, ip: str) -> bool:
        return ip in self._whitelist

    def add_whitelist(self, ip: str) -> None:
        self._whitelist.add(ip)

    def remove_whitelist(self, ip: str) -> bool:
        if ip in self._whitelist:
            self._whitelist.discard(ip)
            return True
        return False

    def set_custom(self, ip: str, rate: float, burst: int) -> None:
        self._custom[ip] = {"rate": rate, "burst": burst}
        if ip in self._buckets:
            self._buckets[ip] = TokenBucket(rate=rate, burst=burst)

    def check(self, ip: str) -> Tuple[bool, Optional[float], str]:
        """Returns (allowed, retry_after, reason)."""
        if self.is_whitelisted(ip):
            return True, None, "whitelisted"
        bucket = self.get_bucket(ip)
        allowed, wait = bucket.consume()
        if allowed:
            return True, None, "allowed"
        return False, wait, "rate_limited"

    def cleanup(self, max_age: float = 3600.0) -> int:
        now = time.monotonic()
        stale = [ip for ip, ts in self._last_access.items() if now - ts > max_age]
        for ip in stale:
            self._buckets.pop(ip, None)
            self._last_access.pop(ip, None)
        return len(stale)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_buckets": len(self._buckets),
            "whitelist_size": len(self._whitelist),
            "default_rate": self.default_rate,
            "default_burst": self.default_burst,
        }


# ── Middleware ───────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        manager: IPBucketManager,
        exclude_paths: Optional[List[str]] = None,
    ) -> None:
        super().__init__(app)
        self.manager = manager
        self.exclude_paths = exclude_paths or ["/docs", "/openapi.json", "/api/v1/health"]
        self._stats = {
            "total": 0,
            "allowed": 0,
            "limited": 0,
            "whitelisted": 0,
        }

    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        self._stats["total"] += 1

        path = request.url.path
        for ep in self.exclude_paths:
            if path.startswith(ep):
                return await call_next(request)

        ip = self._get_ip(request)
        allowed, wait, reason = self.manager.check(ip)

        if reason == "whitelisted":
            self._stats["whitelisted"] += 1
        elif allowed:
            self._stats["allowed"] += 1
        else:
            self._stats["limited"] += 1

        if not allowed:
            retry_after = max(1, math.ceil(wait)) if wait else 1
            body = {
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
                "retry_after": retry_after,
            }
            return JSONResponse(
                status_code=429,
                content=body,
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Add rate-limit headers
        bucket = self.manager.get_bucket(ip)
        remaining = bucket.get_remaining()
        response.headers["X-RateLimit-Limit"] = str(bucket.burst)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        if self.manager.is_whitelisted(ip):
            response.headers["X-RateLimit-Status"] = "whitelisted"

        return response


# ── FastAPI app ─────────────────────────────────────────────────────

bucket_manager = IPBucketManager(default_rate=10.0, default_burst=20)
# Default whitelist entries
bucket_manager.add_whitelist("127.0.0.1")
bucket_manager.add_whitelist("::1")

app = FastAPI(title="Rate Limiter API")
app.add_middleware(RateLimitMiddleware, manager=bucket_manager)


# ── Demo / management endpoints ─────────────────────────────────────

@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/v1/rate-limit/stats")
async def rl_stats() -> Dict[str, Any]:
    return bucket_manager.stats()


class WhitelistBody(BaseModel):
    ip: str


@app.post("/api/v1/rate-limit/whitelist")
async def add_wl(body: WhitelistBody) -> Dict[str, str]:
    bucket_manager.add_whitelist(body.ip)
    return {"message": f"{body.ip} added to whitelist"}


@app.delete("/api/v1/rate-limit/whitelist/{ip}")
async def remove_wl(ip: str) -> Dict[str, str]:
    ok = bucket_manager.remove_whitelist(ip)
    if not ok:
        return {"message": f"{ip} was not in whitelist"}
    return {"message": f"{ip} removed from whitelist"}


@app.get("/api/v1/rate-limit/whitelist")
async def list_wl() -> Dict[str, Any]:
    return {"whitelist": sorted(bucket_manager._whitelist)}


class CustomConfigBody(BaseModel):
    ip: str
    rate: float
    burst: int


@app.post("/api/v1/rate-limit/config")
async def set_custom(body: CustomConfigBody) -> Dict[str, str]:
    bucket_manager.set_custom(body.ip, body.rate, body.burst)
    return {"message": f"Custom config set for {body.ip}"}


@app.get("/api/v1/demo")
async def demo() -> Dict[str, str]:
    return {"message": "Hello! This endpoint is rate-limited."}
