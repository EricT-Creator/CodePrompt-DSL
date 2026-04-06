import math
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

RATE_PER_SECOND = float(os.getenv("RATE_LIMIT_PER_SECOND", "1.5"))
BURST_CAPACITY = int(os.getenv("RATE_LIMIT_BURST", "5"))
WHITELIST_IPS = {
    ip.strip()
    for ip in os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1,::1").split(",")
    if ip.strip()
}
SKIP_RATE_LIMIT_PATHS = {"/status", "/docs", "/openapi.json", "/redoc"}


@dataclass
class TokenBucket:
    tokens: float
    last_refill: float


buckets: Dict[str, TokenBucket] = {}
buckets_lock = threading.Lock()


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    client = request.client
    return client.host if client else "unknown"


def refill_bucket(bucket: TokenBucket, now: float) -> None:
    elapsed = max(0.0, now - bucket.last_refill)
    bucket.tokens = min(BURST_CAPACITY, bucket.tokens + elapsed * RATE_PER_SECOND)
    bucket.last_refill = now


def consume_token(ip: str) -> Tuple[bool, float, float]:
    now = time.monotonic()
    with buckets_lock:
        bucket = buckets.get(ip)
        if bucket is None:
            bucket = TokenBucket(tokens=float(BURST_CAPACITY), last_refill=now)
            buckets[ip] = bucket

        refill_bucket(bucket, now)
        available_before_consume = bucket.tokens
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True, bucket.tokens, 0.0

        missing_tokens = 1 - bucket.tokens
        retry_after = missing_tokens / RATE_PER_SECOND if RATE_PER_SECOND > 0 else 1.0
        return False, available_before_consume, retry_after


def peek_token_count(ip: str) -> float:
    now = time.monotonic()
    with buckets_lock:
        bucket = buckets.get(ip)
        if bucket is None:
            bucket = TokenBucket(tokens=float(BURST_CAPACITY), last_refill=now)
            buckets[ip] = bucket
        refill_bucket(bucket, now)
        return bucket.tokens


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    path = request.url.path
    ip = get_client_ip(request)

    if ip not in WHITELIST_IPS and path not in SKIP_RATE_LIMIT_PATHS:
        allowed, remaining_tokens, retry_after = consume_token(ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "ip": ip,
                    "available_tokens": round(remaining_tokens, 3),
                },
                headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
            )

    response = await call_next(request)
    response.headers["X-Rate-Limit-Rate"] = str(RATE_PER_SECOND)
    response.headers["X-Rate-Limit-Burst"] = str(BURST_CAPACITY)
    return response


@app.get("/")
def root() -> Dict[str, object]:
    return {
        "message": "Rate limiter is active",
        "rate_per_second": RATE_PER_SECOND,
        "burst_capacity": BURST_CAPACITY,
        "whitelist_size": len(WHITELIST_IPS),
    }


@app.get("/status")
def status_endpoint(request: Request) -> Dict[str, object]:
    ip = get_client_ip(request)
    return {
        "ip": ip,
        "whitelisted": ip in WHITELIST_IPS,
        "tokens": round(peek_token_count(ip), 3),
        "rate_per_second": RATE_PER_SECOND,
        "burst_capacity": BURST_CAPACITY,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
