import time
import math
from typing import Dict, Set, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

RATE = 10.0
BURST = 20
WHITELIST: Set[str] = {"127.0.0.1", "::1"}


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()

    def refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self) -> bool:
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> float:
        if self.tokens >= 1.0:
            return 0.0
        needed = 1.0 - self.tokens
        return math.ceil(needed / self.rate)

    def current_tokens(self) -> float:
        self.refill()
        return round(self.tokens, 2)


buckets: Dict[str, TokenBucket] = {}


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/status":
        return await call_next(request)

    client_ip = get_client_ip(request)

    if client_ip in WHITELIST:
        return await call_next(request)

    if client_ip not in buckets:
        buckets[client_ip] = TokenBucket(rate=RATE, burst=BURST)

    bucket = buckets[client_ip]

    if not bucket.consume():
        retry_after = bucket.retry_after()
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(int(retry_after))},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.current_tokens()))
    response.headers["X-RateLimit-Limit"] = str(BURST)
    return response


@app.get("/")
async def root():
    return {"message": "Welcome! This endpoint is rate-limited."}


@app.get("/ping")
async def ping():
    return {"pong": True, "timestamp": time.time()}


@app.get("/status")
async def status(request: Request):
    client_ip = get_client_ip(request)
    is_whitelisted = client_ip in WHITELIST

    if client_ip in buckets:
        bucket = buckets[client_ip]
        tokens = bucket.current_tokens()
    else:
        tokens = float(BURST)

    return {
        "ip": client_ip,
        "tokens_remaining": tokens,
        "rate": RATE,
        "burst": BURST,
        "whitelisted": is_whitelisted,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
