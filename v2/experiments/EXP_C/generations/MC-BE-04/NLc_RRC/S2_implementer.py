import time
import math
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ─── Configuration ────────────────────────────────────────────────────────────

RATE: float = 10.0          # tokens per second
BURST: int = 20             # max bucket capacity
CLEANUP_THRESHOLD: float = 600.0  # seconds before stale bucket cleanup

WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1"}


# ─── Token Bucket ─────────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    rate: float = RATE
    burst: int = BURST

    def refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self) -> tuple[bool, float]:
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        else:
            deficit = 1.0 - self.tokens
            retry_after = math.ceil(deficit / self.rate)
            return False, float(retry_after)


# ─── Bucket Store ─────────────────────────────────────────────────────────────

buckets: dict[str, TokenBucket] = {}


def get_or_create_bucket(ip: str) -> TokenBucket:
    if ip not in buckets:
        buckets[ip] = TokenBucket(tokens=float(BURST), last_refill=time.time())
    return buckets[ip]


def cleanup_stale_buckets() -> None:
    now = time.time()
    stale = [ip for ip, b in buckets.items() if now - b.last_refill > CLEANUP_THRESHOLD]
    for ip in stale:
        del buckets[ip]


# ─── Response Models ──────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    ip: str
    whitelisted: bool
    tokens_remaining: float
    rate: float
    burst: int


class HelloResponse(BaseModel):
    message: str


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Token Bucket Rate Limiter")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):  # type: ignore
    ip = request.client.host if request.client else "unknown"

    if ip in WHITELIST:
        response = await call_next(request)
        return response

    if len(buckets) > 10000:
        cleanup_stale_buckets()

    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume()

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(int(retry_after))},
        )

    response = await call_next(request)
    return response


@app.get("/", response_model=HelloResponse)
async def root() -> HelloResponse:
    return HelloResponse(message="Hello! This endpoint is rate-limited.")


@app.get("/status", response_model=StatusResponse)
async def status(request: Request) -> StatusResponse:
    ip = request.client.host if request.client else "unknown"
    whitelisted = ip in WHITELIST

    if whitelisted or ip not in buckets:
        tokens_remaining = float(BURST)
    else:
        bucket = buckets[ip]
        bucket.refill()
        tokens_remaining = bucket.tokens

    return StatusResponse(
        ip=ip,
        whitelisted=whitelisted,
        tokens_remaining=round(tokens_remaining, 2),
        rate=RATE,
        burst=BURST,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
