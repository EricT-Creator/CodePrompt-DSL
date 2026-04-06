import time
import threading
from typing import Dict, Optional, Set

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

app = FastAPI()

RATE = 5.0
BURST = 10
WHITELIST_IPS: Set[str] = {"127.0.0.1", "::1"}


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def consume(self) -> tuple[bool, float]:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True, 0.0
            else:
                wait_time = (1.0 - self.tokens) / self.rate
                return False, wait_time

    def current_tokens(self) -> float:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            return min(self.burst, self.tokens + elapsed * self.rate)


class RateLimiterState:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def get_bucket(self, ip: str) -> TokenBucket:
        with self.lock:
            if ip not in self.buckets:
                self.buckets[ip] = TokenBucket(self.rate, self.burst)
            return self.buckets[ip]


rate_limiter_state = RateLimiterState(rate=RATE, burst=BURST)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = get_client_ip(request)

        if client_ip in WHITELIST_IPS:
            response = await call_next(request)
            response.headers["X-RateLimit-Whitelisted"] = "true"
            return response

        bucket = rate_limiter_state.get_bucket(client_ip)
        allowed, retry_after = bucket.consume()

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests", "retry_after": round(retry_after, 2)},
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(rate_limiter_state.burst),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        remaining = bucket.current_tokens()
        response.headers["X-RateLimit-Limit"] = str(rate_limiter_state.burst)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        return response


app.add_middleware(RateLimiterMiddleware)


@app.get("/")
async def root():
    return {"message": "Welcome to the rate-limited API"}


@app.get("/status")
async def status(request: Request):
    client_ip = get_client_ip(request)
    is_whitelisted = client_ip in WHITELIST_IPS

    if is_whitelisted:
        return {
            "ip": client_ip,
            "whitelisted": True,
            "tokens": rate_limiter_state.burst,
            "max_tokens": rate_limiter_state.burst,
            "rate": rate_limiter_state.rate,
        }

    bucket = rate_limiter_state.get_bucket(client_ip)
    current = bucket.current_tokens()

    return {
        "ip": client_ip,
        "whitelisted": False,
        "tokens": round(current, 2),
        "max_tokens": rate_limiter_state.burst,
        "rate": rate_limiter_state.rate,
    }


@app.get("/test")
async def test_endpoint():
    return {"message": "This endpoint is rate-limited", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
