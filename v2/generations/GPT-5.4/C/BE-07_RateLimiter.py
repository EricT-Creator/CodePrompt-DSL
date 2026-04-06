import os
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

RATE = float(os.getenv("RATE_LIMIT_RATE", "2.0"))
BURST = int(os.getenv("RATE_LIMIT_BURST", "5"))
WHITELIST = {item.strip() for item in os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1,::1").split(",") if item.strip()}


class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.updated_at = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.updated_at = now

    def consume(self, amount: float = 1.0) -> tuple[bool, float]:
        with self.lock:
            self._refill()
            if self.tokens >= amount:
                self.tokens -= amount
                return True, 0.0
            missing = amount - self.tokens
            retry_after = missing / self.rate if self.rate > 0 else 1.0
            return False, retry_after

    def snapshot(self) -> float:
        with self.lock:
            self._refill()
            return round(self.tokens, 3)


buckets: dict[str, TokenBucket] = {}
buckets_lock = threading.Lock()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def get_bucket(ip_address: str) -> TokenBucket:
    with buckets_lock:
        if ip_address not in buckets:
            buckets[ip_address] = TokenBucket(RATE, BURST)
        return buckets[ip_address]


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip_address = get_client_ip(request)
    if ip_address in WHITELIST:
        response = await call_next(request)
        response.headers["X-RateLimit-Bypass"] = "whitelist"
        return response

    bucket = get_bucket(ip_address)
    allowed, retry_after = bucket.consume()
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests", "retry_after": round(retry_after, 3)},
            headers={"Retry-After": str(max(1, int(retry_after) + 1))},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(bucket.snapshot())
    response.headers["X-RateLimit-Rate"] = str(RATE)
    response.headers["X-RateLimit-Burst"] = str(BURST)
    return response


@app.get("/")
async def root():
    return {"service": "rate-limiter", "rate": RATE, "burst": BURST}


@app.get("/status")
async def status(request: Request):
    ip_address = get_client_ip(request)
    if ip_address in WHITELIST:
        return {
            "ip": ip_address,
            "whitelisted": True,
            "tokens": float(BURST),
            "rate": RATE,
            "burst": BURST,
        }

    bucket = get_bucket(ip_address)
    return {
        "ip": ip_address,
        "whitelisted": False,
        "tokens": bucket.snapshot(),
        "rate": RATE,
        "burst": BURST,
    }


@app.get("/limited")
async def limited(request: Request):
    return {"message": "Request accepted", "ip": get_client_ip(request), "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
