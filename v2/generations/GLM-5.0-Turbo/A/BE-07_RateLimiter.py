import time
import threading
from typing import Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# --- Token Bucket Implementation ---

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self.tokens = float(burst)
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                wait_time = (tokens - self.tokens) / self.rate
                return False, wait_time


# --- Middleware Configuration ---

RATE = 2.0  # 2 tokens per second
BURST = 5  # max 5 tokens burst
WHITELIST_IPS = {"127.0.0.1", "::1", "10.0.0.1"}

buckets: Dict[str, TokenBucket] = {}
buckets_lock = threading.Lock()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_or_create_bucket(ip: str) -> TokenBucket:
    with buckets_lock:
        if ip not in buckets:
            buckets[ip] = TokenBucket(rate=RATE, burst=BURST)
        return buckets[ip]


# --- Middleware ---

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip non-path-specific checks; apply to all routes
    ip = get_client_ip(request)

    # Whitelist bypass
    if ip in WHITELIST_IPS:
        return await call_next(request)

    # Skip rate limiting for the status endpoint itself to avoid lockout
    if request.url.path == "/status":
        return await call_next(request)

    bucket = get_or_create_bucket(ip)
    allowed, wait_time = bucket.consume()

    if not allowed:
        retry_after = int(wait_time) + 1
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    response = await call_next(request)
    return response


# --- Endpoints ---

@app.get("/status")
async def status(request: Request):
    ip = get_client_ip(request)
    bucket = get_or_create_bucket(ip)
    with bucket.lock:
        now = time.time()
        elapsed = now - bucket.last_refill
        current_tokens = min(bucket.burst, bucket.tokens + elapsed * bucket.rate)
    return {
        "ip": ip,
        "tokens": round(current_tokens, 2),
        "max_tokens": bucket.burst,
        "rate": bucket.rate,
        "whitelisted": ip in WHITELIST_IPS,
    }


@app.get("/")
async def index():
    return {"message": "Rate Limiter API", "rate": f"{RATE} req/s", "burst": BURST}


@app.get("/test")
async def test_endpoint():
    return {"message": "Request successful"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
