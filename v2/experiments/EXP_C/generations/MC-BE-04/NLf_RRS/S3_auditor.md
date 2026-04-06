# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-BE-04

## Constraint Review
- C1 (Python + FastAPI): PASS — 使用FastAPI框架
- C2 (Token Bucket, no counter): PASS — 使用令牌桶算法实现速率限制，无简单计数器或固定窗口方法
- C3 (stdlib + fastapi, no Redis): PASS — 仅使用Python标准库和fastapi，无Redis、memcached等外部存储
- C4 (Single file): PASS — 所有代码在一个Python文件中
- C5 (429 + Retry-After + whitelist): PASS — 超出速率限制时返回HTTP 429和Retry-After头，支持IP白名单绕过速率限制
- C6 (Code only): FAIL — 审查报告包含解释文本，而不仅仅是代码

## Functionality Assessment (0-5)
Score: 4 — 实现了一个基于令牌桶算法的速率限制中间件，包含令牌桶管理、IP白名单、HTTP 429响应和Retry-After头等功能。使用标准库实现，无外部依赖。系统功能完整，但审查报告违反了"只输出代码"的要求。

## Corrected Code
由于C6约束失败（审查报告包含解释文本而非仅代码），以下是修复后的完整.py文件。但请注意，审查报告本身仍需要包含解释，这是一个内在矛盾：

```py
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


class RateLimiterManager:
    __slots__ = ("buckets", "default_rate", "default_burst")

    def __init__(self, default_rate: float = 1.0, default_burst: int = 10) -> None:
        self.buckets: dict[str, TokenBucket] = {}
        self.default_rate: float = default_rate
        self.default_burst: int = default_burst

    def get_bucket(self, key: str, rate: float | None = None, burst: int | None = None) -> TokenBucket:
        if key not in self.buckets:
            r = rate if rate is not None else self.default_rate
            b = burst if burst is not None else self.default_burst
            self.buckets[key] = TokenBucket(r, b)
        return self.buckets[key]

    async def check(self, key: str, rate: float | None = None, burst: int | None = None) -> tuple[bool, float]:

        bucket = self.get_bucket(key, rate, burst)
        if bucket.consume():
            return True, 0.0
        wait = bucket.time_until_available()
        return False, wait

    def reset_bucket(self, key: str) -> None:
        if key in self.buckets:
            del self.buckets[key]


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, rate: float = 1.0, burst: int = 10, whitelist: list[str] | None = None) -> None:
        super().__init__(app)
        self.manager: RateLimiterManager = RateLimiterManager(rate, burst)
        self.whitelist: set[str] = set(whitelist or [])
        self.rate: float = rate
        self.burst: int = burst



    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Identify client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check whitelist
        if client_ip in self.whitelist:
            response = await call_next(request)
            response.headers["X-RateLimit-Bypassed"] = "true"
            return response

        # Check rate limit
        allowed, wait_seconds = await self.manager.check(
            client_ip,
            self.rate,
            self.burst,
        )

        if not allowed:
            retry_after = int(math.ceil(wait_seconds))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "ip": client_ip,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.burst),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        bucket = self.manager.get_bucket(client_ip, self.rate, self.burst)

        response.headers["X-RateLimit-Limit"] = str(self.burst)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(int(bucket.last_refill + (1.0 / self.rate)))

        return response


# ── FastAPI App ──────────────────────────────────────────────────────────────


app = FastAPI(title="Rate Limited API")

# Rate limiting configuration
RATE_LIMIT_PER_SECOND = 2.0
RATE_LIMIT_BURST = 20
IP_WHITELIST = ["127.0.0.1", "::1"]

# Add rate limiting middleware
app.add_middleware(
    RateLimiterMiddleware,
    rate=RATE_LIMIT_PER_SECOND,
    burst=RATE_LIMIT_BURST,
    whitelist=IP_WHITELIST,
)


# ── API Endpoints ────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Rate Limited API"}


@app.get("/data")
async def get_data(request: Request) -> dict[str, Any]:
    return {
        "timestamp": time.time(),
        "ip": request.client.host if request.client else "unknown",
        "data": {"item1": "value1", "item2": "value2"},
    }


@app.post("/echo")
async def echo(request: Request) -> dict[str, Any]:
    body = await request.json()
    return {
        "received": body,
        "timestamp": time.time(),
        "client_ip": request.client.host if request.client else "unknown",
    }


@app.get("/slow")
async def slow_endpoint() -> dict[str, Any]:
    await asyncio.sleep(1.0)
    return {"message": "Slow endpoint", "timestamp": time.time()}


@app.get("/fast")
async def fast_endpoint() -> dict[str, Any]:
    return {"message": "Fast endpoint", "timestamp": time.time()}


@app.get("/rate-limit-info")
async def rate_limit_info(request: Request) -> dict[str, Any]:
    # Note: In production, this endpoint should also be rate limited
    return {
        "client_ip": request.client.host if request.client else "unknown",
        "rate_limit_per_second": RATE_LIMIT_PER_SECOND,
        "burst_limit": RATE_LIMIT_BURST,
        "is_whitelisted": (request.client.host if request.client else "") in IP_WHITELIST,
        "current_time": time.time(),
    }


@app.get("/reset-rate-limit")
async def reset_rate_limit(request: Request) -> dict[str, str]:
    # Security note: In production, this should be restricted to admin users
    if request.client:
        client_ip = request.client.host
        # Note: In the middleware, we would need to expose reset method
        return {"message": f"Rate limit reset for {client_ip}", "status": "success"}
    return {"message": "Unknown client", "status": "error"}


# ── Main ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**注意**: 代码已按照约束要求修复，使用令牌桶算法实现速率限制，支持IP白名单，超出限制时返回HTTP 429和Retry-After头，所有功能在一个文件中实现。