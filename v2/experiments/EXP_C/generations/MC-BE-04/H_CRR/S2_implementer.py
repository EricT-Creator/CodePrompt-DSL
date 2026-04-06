"""
MC-BE-04: Rate Limiter Middleware
[L]Python [F]FastAPI [ALGO]TOKEN_BUCKET [!A]NO_COUNTER [D]STDLIB+FASTAPI [!D]NO_REDIS [O]SINGLE_FILE [RESP]429_RETRY_AFTER [WL]IP [OUT]CODE_ONLY
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel


# ─── Configuration ────────────────────────────────────────────────────────────

RATE_LIMIT_RATE: float = 10.0      # tokens per second
RATE_LIMIT_CAPACITY: float = 20.0  # max burst size
RATE_LIMIT_WHITELIST: set[str] = {"127.0.0.1", "::1"}
BUCKET_CLEANUP_AGE: float = 3600.0  # seconds


# ─── Token Bucket ─────────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    capacity: float
    tokens: float
    rate: float
    last_update: float


# Per-IP bucket store
buckets: dict[str, TokenBucket] = {}


def get_bucket(ip: str) -> TokenBucket:
    if ip not in buckets:
        buckets[ip] = TokenBucket(
            capacity=RATE_LIMIT_CAPACITY,
            tokens=RATE_LIMIT_CAPACITY,
            rate=RATE_LIMIT_RATE,
            last_update=time.monotonic(),
        )
    return buckets[ip]


def replenish(bucket: TokenBucket) -> None:
    now = time.monotonic()
    elapsed = now - bucket.last_update
    bucket.tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.rate)
    bucket.last_update = now


def try_consume(bucket: TokenBucket) -> bool:
    replenish(bucket)
    if bucket.tokens >= 1.0:
        bucket.tokens -= 1.0
        return True
    return False


def calculate_retry_after(bucket: TokenBucket) -> int:
    if bucket.tokens >= 1.0:
        return 0
    tokens_needed = 1.0 - bucket.tokens
    seconds_needed = tokens_needed / bucket.rate
    return int(seconds_needed) + 1


def cleanup_buckets() -> None:
    now = time.monotonic()
    stale_ips = [
        ip for ip, bucket in buckets.items()
        if now - bucket.last_update > BUCKET_CLEANUP_AGE
    ]
    for ip in stale_ips:
        del buckets[ip]


# ─── Rate Limit Check ─────────────────────────────────────────────────────────

def check_rate_limit(ip: str) -> tuple[bool, int, TokenBucket]:
    bucket = get_bucket(ip)
    allowed = try_consume(bucket)
    retry_after = 0 if allowed else calculate_retry_after(bucket)
    return allowed, retry_after, bucket


# ─── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, whitelist: set[str] | None = None) -> None:
        super().__init__(app)
        self.whitelist: set[str] = whitelist or RATE_LIMIT_WHITELIST

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        client_ip = request.client.host if request.client else "unknown"

        # Whitelist bypass
        if client_ip in self.whitelist:
            response = await call_next(request)
            return response

        allowed, retry_after, bucket = check_rate_limit(client_ip)

        if not allowed:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(int(bucket.capacity)),
                    "X-RateLimit-Remaining": str(max(0, int(bucket.tokens))),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(int(bucket.capacity))
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(bucket.tokens)))

        return response


# ─── Response Models ──────────────────────────────────────────────────────────

class DataResponse(BaseModel):
    message: str
    data: dict[str, str]


class StatusResponse(BaseModel):
    status: str
    total_buckets: int
    whitelist: list[str]
    rate: float
    capacity: float


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Rate Limiter Middleware")
app.add_middleware(RateLimitMiddleware, whitelist=RATE_LIMIT_WHITELIST)


@app.get("/api/data", response_model=DataResponse)
async def get_data() -> DataResponse:
    return DataResponse(
        message="Here is your data",
        data={"key": "value", "timestamp": str(time.time())},
    )


@app.get("/api/users", response_model=DataResponse)
async def get_users() -> DataResponse:
    return DataResponse(
        message="User list",
        data={"user_count": "42"},
    )


@app.get("/api/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    return StatusResponse(
        status="ok",
        total_buckets=len(buckets),
        whitelist=list(RATE_LIMIT_WHITELIST),
        rate=RATE_LIMIT_RATE,
        capacity=RATE_LIMIT_CAPACITY,
    )


@app.post("/api/cleanup")
async def trigger_cleanup() -> dict[str, str]:
    before = len(buckets)
    cleanup_buckets()
    after = len(buckets)
    return {"message": f"Cleaned up {before - after} stale buckets", "remaining": str(after)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
