import time
import threading
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def consume(self) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def get_tokens(self) -> float:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            return min(self.burst, self.tokens + elapsed * self.rate)

    def time_until_token(self) -> float:
        with self.lock:
            if self.tokens >= 1.0:
                return 0.0
            deficit = 1.0 - self.tokens
            return deficit / self.rate


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate: float = 10.0,
        burst: int = 20,
        whitelist: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self.whitelist: set = set(whitelist or [])
        self.buckets: Dict[str, TokenBucket] = {}
        self.buckets_lock = threading.Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_bucket(self, ip: str) -> TokenBucket:
        with self.buckets_lock:
            if ip not in self.buckets:
                self.buckets[ip] = TokenBucket(self.rate, self.burst)
            return self.buckets[ip]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = self._get_client_ip(request)

        if client_ip in self.whitelist:
            response = await call_next(request)
            return response

        bucket = self._get_bucket(client_ip)

        if not bucket.consume():
            retry_after = bucket.time_until_token()
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests",
                    "retry_after": round(retry_after, 2),
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        response = await call_next(request)
        remaining = bucket.get_tokens()
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        response.headers["X-RateLimit-Limit"] = str(self.burst)
        return response


WHITELIST_IPS = ["127.0.0.1", "::1"]

app = FastAPI()
app.add_middleware(
    RateLimiterMiddleware,
    rate=10.0,
    burst=20,
    whitelist=WHITELIST_IPS,
)


@app.get("/")
async def root():
    return {"message": "Welcome! This endpoint is rate-limited."}


@app.get("/status")
async def status(request: Request):
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    middleware: Optional[RateLimiterMiddleware] = None
    for m in app.middleware_stack.__dict__.get("app", app).__class__.__mro__:
        break
    for route_middleware in getattr(app, "user_middleware", []):
        if route_middleware.cls == RateLimiterMiddleware:
            break

    with threading.Lock():
        buckets = {}
        for mid in app.middleware_stack.__dict__.values():
            if isinstance(mid, RateLimiterMiddleware):
                middleware = mid
                break

    if middleware is None:
        bucket_info = {"note": "Rate limiter middleware reference unavailable via this path"}
        is_whitelisted = client_ip in WHITELIST_IPS
        return {
            "client_ip": client_ip,
            "whitelisted": is_whitelisted,
            "rate_limit": 10.0,
            "burst_limit": 20,
            **bucket_info,
        }

    is_whitelisted = client_ip in middleware.whitelist
    if is_whitelisted:
        return {
            "client_ip": client_ip,
            "whitelisted": True,
            "message": "You are whitelisted and not rate-limited",
        }

    bucket = middleware._get_bucket(client_ip)
    current_tokens = bucket.get_tokens()

    return {
        "client_ip": client_ip,
        "whitelisted": False,
        "current_tokens": round(current_tokens, 2),
        "max_tokens": middleware.burst,
        "refill_rate": middleware.rate,
        "tokens_per_second": middleware.rate,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
