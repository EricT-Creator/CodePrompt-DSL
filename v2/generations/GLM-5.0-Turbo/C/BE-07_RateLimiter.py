import time
import threading
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI(title="Rate Limiter (Token Bucket)")


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, count: int = 1) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= count:
                self.tokens -= count
                return True
            return False

    def get_token_count(self) -> dict:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            current_tokens = min(self.burst, self.tokens + elapsed * self.rate)
            return {
                "tokens": round(current_tokens, 2),
                "max_tokens": self.burst,
                "rate": f"{self.rate}/s",
            }


# Configuration
DEFAULT_RATE = 2.0
DEFAULT_BURST = 5
WHITELIST_IPS = {"127.0.0.1", "::1"}

buckets: dict[str, TokenBucket] = {}
buckets_lock = threading.Lock()


def get_bucket(ip: str) -> TokenBucket:
    with buckets_lock:
        if ip not in buckets:
            buckets[ip] = TokenBucket(rate=DEFAULT_RATE, burst=DEFAULT_BURST)
        return buckets[ip]


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/health", "/docs", "/openapi.json", "/status"):
        return await call_next(request)

    ip = get_client_ip(request)
    if ip in WHITELIST_IPS:
        return await call_next(request)

    bucket = get_bucket(ip)
    if not bucket.consume():
        tokens_info = bucket.get_token_count()
        retry_after = (1.0 / bucket.rate) * 1.0
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "detail": f"Rate limit exceeded. Retry after {retry_after:.1f}s.",
                "tokens": tokens_info,
            },
            headers={"Retry-After": str(round(retry_after, 1))},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Tokens"] = str(int(bucket.get_token_count()["tokens"]))
    return response


@app.get("/status")
def get_status(request: Request):
    ip = get_client_ip(request)
    bucket = get_bucket(ip)
    return {
        "ip": ip,
        "whitelisted": ip in WHITELIST_IPS,
        **bucket.get_token_count(),
    }


@app.get("/limited-endpoint")
def limited_endpoint():
    return {"message": "This endpoint is rate-limited."}


@app.post("/limited-endpoint")
def limited_post():
    return {"message": "POST request processed."}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
