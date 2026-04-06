import time
from typing import Dict, Set

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

# Configuration
RATE = 10.0         # tokens per second
BURST = 20          # max bucket size
IP_WHITELIST: Set[str] = {"127.0.0.1", "::1"}


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()

    def refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self, count: int = 1) -> bool:
        self.refill()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False

    def retry_after(self) -> float:
        self.refill()
        if self.tokens >= 1:
            return 0.0
        needed = 1.0 - self.tokens
        return needed / self.rate


buckets: Dict[str, TokenBucket] = {}


def get_bucket(ip: str) -> TokenBucket:
    if ip not in buckets:
        buckets[ip] = TokenBucket(rate=RATE, burst=BURST)
    return buckets[ip]


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)

    # Bypass whitelist
    if client_ip in IP_WHITELIST:
        response = await call_next(request)
        return response

    bucket = get_bucket(client_ip)

    if not bucket.consume():
        retry = bucket.retry_after()
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests",
                "retry_after": round(retry, 2),
            },
            headers={"Retry-After": str(int(retry) + 1)},
        )

    response = await call_next(request)

    # Add rate limit headers
    bucket.refill()
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Limit"] = str(BURST)
    return response


@app.get("/")
async def root():
    return {"message": "Welcome to the rate-limited API"}


@app.get("/status")
async def rate_limit_status(request: Request):
    client_ip = get_client_ip(request)
    is_whitelisted = client_ip in IP_WHITELIST

    if is_whitelisted:
        return {
            "ip": client_ip,
            "whitelisted": True,
            "message": "No rate limit applied",
        }

    bucket = get_bucket(client_ip)
    bucket.refill()

    return {
        "ip": client_ip,
        "whitelisted": False,
        "tokens_remaining": round(bucket.tokens, 2),
        "max_tokens": BURST,
        "refill_rate": f"{RATE} tokens/sec",
    }


@app.get("/test")
async def test_endpoint():
    return {"message": "This is a rate-limited endpoint", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
