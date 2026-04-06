import time
import threading
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# ===== Token Bucket Rate Limiter =====

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate          # tokens added per second
        self.burst = burst        # max tokens
        self.tokens = float(burst)
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def get_token_count(self) -> dict:
        with self.lock:
            self._refill()
            return {
                "tokens": round(self.tokens, 2),
                "max": self.burst,
                "rate": self.rate,
            }


# Configuration
RATE_LIMIT: float = 5.0     # 5 tokens per second
BURST_LIMIT: int = 10        # max burst of 10
IP_WHITELIST: set = {
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",
}

buckets: dict = defaultdict(lambda: TokenBucket(RATE_LIMIT, BURST_LIMIT))


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_whitelisted(ip: str) -> bool:
    for pattern in IP_WHITELIST:
        if pattern.endswith("/8"):
            prefix = pattern.split("/")[0].rsplit(".", 1)[0]
            if ip.startswith(prefix + "."):
                return True
        elif ip == pattern:
            return True
    return False


# ===== Middleware =====

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/docs", "/openapi.json", "/"):
        return await call_next(request)

    client_ip = get_client_ip(request)

    if is_whitelisted(client_ip):
        return await call_next(request)

    bucket = buckets[client_ip]
    if not bucket.consume():
        tokens = bucket.get_token_count()
        retry_after = max(1, int(1.0 / RATE_LIMIT))
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": retry_after,
                "tokens_remaining": tokens["tokens"],
            },
            headers={"Retry-After": str(retry_after)},
        )

    return await call_next(request)


# ===== Routes =====

@app.get("/status")
async def status(request: Request):
    client_ip = get_client_ip(request)
    bucket = buckets[client_ip]
    token_info = bucket.get_token_count()
    return {
        "ip": client_ip,
        "whitelisted": is_whitelisted(client_ip),
        "tokens": token_info["tokens"],
        "max_tokens": token_info["max"],
        "rate": token_info["rate"],
    }


@app.get("/hello")
async def hello():
    return {"message": "Hello! This endpoint is rate limited."}


@app.get("/data")
async def data():
    return {"items": [1, 2, 3], "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
