from __future__ import annotations

import asyncio
import math
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn


# ── Token Bucket ────────────────────────────────────────────────────────

class TokenBucket:
    __slots__ = ("rate", "capacity", "tokens", "last_refill")

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def wait_time(self, n: int = 1) -> float:
        self._refill()
        deficit = n - self.tokens
        if deficit <= 0:
            return 0.0
        return deficit / self.rate

    @property
    def remaining(self) -> int:
        self._refill()
        return int(self.tokens)


# ── Per-IP Bucket Manager ──────────────────────────────────────────────

class BucketManager:
    def __init__(self, rate: float, capacity: int, cleanup_seconds: float = 300) -> None:
        self.rate = rate
        self.capacity = capacity
        self.cleanup_seconds = cleanup_seconds
        self._buckets: dict[str, TokenBucket] = {}
        self._last_access: dict[str, float] = {}

    def get(self, ip: str) -> TokenBucket:
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(self.rate, self.capacity)
        self._last_access[ip] = time.monotonic()
        return self._buckets[ip]

    def consume(self, ip: str) -> tuple[bool, float]:
        bucket = self.get(ip)
        ok = bucket.consume()
        if ok:
            return True, 0.0
        return False, bucket.wait_time()

    def cleanup(self) -> int:
        now = time.monotonic()
        threshold = now - self.cleanup_seconds
        stale = [ip for ip, ts in self._last_access.items() if ts < threshold]
        for ip in stale:
            self._buckets.pop(ip, None)
            self._last_access.pop(ip, None)
        return len(stale)


# ── IP resolver ─────────────────────────────────────────────────────────

def resolve_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip and ip != "unknown":
            return _normalize(ip)
    real = request.headers.get("x-real-ip")
    if real and real != "unknown":
        return _normalize(real)
    if request.client:
        return _normalize(request.client.host)
    return "0.0.0.0"


def _normalize(ip: str) -> str:
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    return ip.strip()


# ── Configuration ───────────────────────────────────────────────────────

RATE_PER_IP = 10.0
CAPACITY_PER_IP = 20
IP_WHITELIST: set[str] = {"127.0.0.1", "::1"}


# ── FastAPI app ─────────────────────────────────────────────────────────

app = FastAPI(title="Token-Bucket Rate Limiter")
manager = BucketManager(rate=RATE_PER_IP, capacity=CAPACITY_PER_IP)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
    ip = resolve_ip(request)

    if ip in IP_WHITELIST:
        response = await call_next(request)
        return response

    allowed, wait = manager.consume(ip)

    if not allowed:
        retry_after = math.ceil(wait)
        bucket = manager.get(ip)
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after_seconds": retry_after,
                },
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(CAPACITY_PER_IP),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            },
        )

    response = await call_next(request)
    bucket = manager.get(ip)
    response.headers["X-RateLimit-Limit"] = str(CAPACITY_PER_IP)
    response.headers["X-RateLimit-Remaining"] = str(bucket.remaining)
    return response


# ── Periodic cleanup ────────────────────────────────────────────────────

@app.on_event("startup")
async def start_cleanup() -> None:
    async def _cleanup_loop() -> None:
        while True:
            await asyncio.sleep(60)
            manager.cleanup()
    asyncio.create_task(_cleanup_loop())


# ── Demo endpoints ──────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    return {"message": "Hello! This endpoint is rate-limited."}


@app.get("/status")
async def status_endpoint(request: Request) -> dict:
    ip = resolve_ip(request)
    bucket = manager.get(ip)
    return {
        "ip": ip,
        "tokens_remaining": bucket.remaining,
        "capacity": CAPACITY_PER_IP,
        "rate_per_second": RATE_PER_IP,
        "whitelisted": ip in IP_WHITELIST,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "tracked_ips": len(manager._buckets)}


@app.post("/whitelist/{ip}")
async def add_whitelist(ip: str) -> dict:
    IP_WHITELIST.add(ip)
    return {"message": f"{ip} added to whitelist", "whitelist": list(IP_WHITELIST)}


@app.delete("/whitelist/{ip}")
async def remove_whitelist(ip: str) -> dict:
    IP_WHITELIST.discard(ip)
    return {"message": f"{ip} removed from whitelist", "whitelist": list(IP_WHITELIST)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
