import math
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

RATE = float(os.getenv("RATE_LIMIT_TOKENS_PER_SECOND", "1.5"))
BURST = float(os.getenv("RATE_LIMIT_BURST", "5"))
WHITELIST = {
    ip.strip()
    for ip in os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1,::1").split(",")
    if ip.strip()
}


@dataclass
class Bucket:
    tokens: float
    last_refill: float


buckets: Dict[str, Bucket] = {}
lock = threading.Lock()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def refill(bucket: Bucket, now: float) -> None:
    elapsed = max(0.0, now - bucket.last_refill)
    bucket.tokens = min(BURST, bucket.tokens + elapsed * RATE)
    bucket.last_refill = now


def consume_token(ip: str) -> Tuple[bool, float, float]:
    now = time.time()
    with lock:
        bucket = buckets.get(ip)
        if bucket is None:
            bucket = Bucket(tokens=BURST, last_refill=now)
            buckets[ip] = bucket

        refill(bucket, now)

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0, bucket.tokens

        missing = 1.0 - bucket.tokens
        retry_after = missing / RATE if RATE > 0 else 0.0
        return False, retry_after, bucket.tokens


def get_token_snapshot(ip: str) -> float:
    now = time.time()
    with lock:
        bucket = buckets.get(ip)
        if bucket is None:
            return BURST
        refill(bucket, now)
        return bucket.tokens


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = get_client_ip(request)
    if ip in WHITELIST:
        response = await call_next(request)
        response.headers["X-RateLimit-Bypass"] = "true"
        return response

    allowed, retry_after, _ = consume_token(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too Many Requests",
                "ip": ip,
                "retry_after_seconds": round(retry_after, 3),
            },
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Bypass"] = "false"
    return response


@app.get("/status")
async def status(request: Request):
    ip = get_client_ip(request)
    return {
        "ip": ip,
        "rate": RATE,
        "burst": BURST,
        "whitelisted": ip in WHITELIST,
        "tokens": round(get_token_snapshot(ip), 3),
    }


@app.get("/")
async def index(request: Request):
    return {
        "message": "Token Bucket limiter is active.",
        "ip": get_client_ip(request),
        "tokens": round(get_token_snapshot(get_client_ip(request)), 3),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
