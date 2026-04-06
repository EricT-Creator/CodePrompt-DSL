"""
MC-BE-04: Token Bucket Rate Limiter
Engineering Constraints: Python + FastAPI. Token Bucket required, no simple counter.
stdlib + fastapi only, no Redis. Single file. 429 with Retry-After, IP whitelist. Code only.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# ── Token Bucket ────────────────────────────────────────────────────────


@dataclass
class TokenBucket:
    rate_per_second: float
    burst_size: int
    tokens: float = 0.0
    last_refill_time: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        # Start with full bucket
        if self.tokens == 0.0:
            self.tokens = float(self.burst_size)

    def refill(self) -> None:
        current = time.time()
        elapsed = current - self.last_refill_time
        new_tokens = elapsed * self.rate_per_second
        self.tokens = min(self.tokens + new_tokens, float(self.burst_size))
        self.last_refill_time = current

    def consume(self, count: float = 1.0) -> bool:
        self.refill()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False

    def get_wait_time(self, count: float = 1.0) -> float:
        self.refill()
        if self.tokens >= count:
            return 0.0
        needed = count - self.tokens
        return needed / self.rate_per_second


class UnlimitedBucket:
    """Bucket for whitelisted IPs."""

    rate_per_second: float = 0.0
    burst_size: int = 0
    tokens: float = float("inf")
    last_refill_time: float = 0.0

    def consume(self, count: float = 1.0) -> bool:
        return True

    def get_wait_time(self, count: float = 1.0) -> float:
        return 0.0

    def refill(self) -> None:
        pass


# ── IP Bucket Manager ───────────────────────────────────────────────────


class IPBucketManager:
    def __init__(
        self,
        default_rate: float = 10.0,
        default_burst: int = 20,
        cleanup_interval: int = 300,
    ) -> None:
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.whitelist: Set[str] = set()
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self._unlimited = UnlimitedBucket()

    def get_bucket(self, ip_address: str) -> TokenBucket | UnlimitedBucket:
        if ip_address in self.whitelist:
            return self._unlimited

        if ip_address not in self.buckets:
            self.buckets[ip_address] = TokenBucket(
                rate_per_second=self.default_rate,
                burst_size=self.default_burst,
            )

        self._maybe_cleanup()
        return self.buckets[ip_address]

    def add_to_whitelist(self, ip_address: str) -> None:
        self.whitelist.add(ip_address)
        self.buckets.pop(ip_address, None)

    def remove_from_whitelist(self, ip_address: str) -> None:
        self.whitelist.discard(ip_address)

    def set_rate_limit(self, ip_address: str, rate: float, burst: int) -> None:
        bucket = self.buckets.get(ip_address)
        if bucket:
            bucket.rate_per_second = rate
            bucket.burst_size = burst
        else:
            self.buckets[ip_address] = TokenBucket(rate_per_second=rate, burst_size=burst)

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        inactive_ips: List[str] = []
        for ip, bucket in self.buckets.items():
            elapsed = now - bucket.last_refill_time
            if elapsed > 1800 and bucket.tokens >= bucket.burst_size:
                inactive_ips.append(ip)
        for ip in inactive_ips:
            del self.buckets[ip]
        self.last_cleanup = now

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_buckets": len(self.buckets),
            "whitelist_size": len(self.whitelist),
            "default_rate": self.default_rate,
            "default_burst": self.default_burst,
        }


# ── IP Extraction ───────────────────────────────────────────────────────


def extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "127.0.0.1"


# ── Middleware ──────────────────────────────────────────────────────────


class TokenBucketMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        ip_bucket_manager: IPBucketManager,
        cost_per_request: float = 1.0,
        excluded_paths: Optional[List[str]] = None,
    ) -> None:
        super().__init__(app)
        self.manager = ip_bucket_manager
        self.cost = cost_per_request
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        path = request.url.path

        # Skip excluded paths
        for ep in self.excluded_paths:
            if path.startswith(ep):
                return await call_next(request)

        client_ip = extract_client_ip(request)
        bucket = self.manager.get_bucket(client_ip)

        if bucket.consume(self.cost):
            response = await call_next(request)

            # Add rate limit headers
            if isinstance(bucket, TokenBucket):
                response.headers["X-RateLimit-Limit"] = str(bucket.burst_size)
                response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + 1.0 / bucket.rate_per_second))

            return response
        else:
            wait_time = bucket.get_wait_time(self.cost)
            retry_after = max(1, math.ceil(wait_time))

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(bucket.burst_size) if isinstance(bucket, TokenBucket) else "0",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + wait_time)),
                },
            )


# ── Request / Response Models ───────────────────────────────────────────


class WhitelistRequest(BaseModel):
    ip_address: str


class RateLimitConfigRequest(BaseModel):
    ip_address: str
    rate_per_second: float
    burst_size: int


class StatsResponse(BaseModel):
    total_buckets: int
    whitelist_size: int
    default_rate: float
    default_burst: int
    whitelist: List[str]


# ── App ─────────────────────────────────────────────────────────────────

ip_manager = IPBucketManager(default_rate=10.0, default_burst=20, cleanup_interval=300)
ip_manager.add_to_whitelist("127.0.0.1")
ip_manager.add_to_whitelist("::1")

app = FastAPI(title="Token Bucket Rate Limiter API")

app.add_middleware(
    TokenBucketMiddleware,
    ip_bucket_manager=ip_manager,
    cost_per_request=1.0,
    excluded_paths=["/docs", "/redoc", "/openapi.json", "/rate-limiter/stats"],
)


@app.get("/")
async def root():
    return {"message": "Token Bucket Rate Limiter is active"}


@app.get("/api/resource")
async def sample_resource():
    return {"data": "This endpoint is rate-limited", "timestamp": time.time()}


@app.get("/api/heavy", tags=["rate-limited"])
async def heavy_resource(request: Request):
    # This endpoint costs 5 tokens
    client_ip = extract_client_ip(request)
    bucket = ip_manager.get_bucket(client_ip)
    # Extra cost already consumed 1 by middleware, consume 4 more
    if not bucket.consume(4.0):
        wait_time = bucket.get_wait_time(4.0)
        retry_after = max(1, math.ceil(wait_time))
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded for heavy endpoint", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )
    return {"data": "Heavy resource accessed", "cost": 5}


@app.get("/rate-limiter/stats", response_model=StatsResponse)
async def get_stats():
    stats = ip_manager.get_stats()
    return StatsResponse(**stats, whitelist=list(ip_manager.whitelist))


@app.post("/rate-limiter/whitelist")
async def add_whitelist(req: WhitelistRequest):
    ip_manager.add_to_whitelist(req.ip_address)
    return {"message": f"Added {req.ip_address} to whitelist"}


@app.delete("/rate-limiter/whitelist")
async def remove_whitelist(req: WhitelistRequest):
    ip_manager.remove_from_whitelist(req.ip_address)
    return {"message": f"Removed {req.ip_address} from whitelist"}


@app.post("/rate-limiter/configure")
async def configure_rate_limit(req: RateLimitConfigRequest):
    ip_manager.set_rate_limit(req.ip_address, req.rate_per_second, req.burst_size)
    return {"message": f"Configured rate limit for {req.ip_address}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
