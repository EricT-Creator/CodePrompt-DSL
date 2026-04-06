import time
import math
from dataclasses import dataclass
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

WHITELIST: set[str] = {"127.0.0.1", "10.0.0.1", "192.168.1.1"}

RATE = 10.0
BURST = 20
CLEANUP_THRESHOLD = 600

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    
    def refill(self, now: float):
        elapsed = now - self.last_refill
        self.tokens = min(BURST, self.tokens + elapsed * RATE)
        self.last_refill = now
    
    def consume(self) -> tuple[bool, int]:
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0
        deficit = 1.0 - self.tokens
        retry_after = math.ceil(deficit / RATE)
        return False, retry_after

buckets: dict[str, TokenBucket] = {}

def get_or_create_bucket(ip: str) -> TokenBucket:
    now = time.time()
    if ip in buckets:
        bucket = buckets[ip]
        elapsed = now - bucket.last_refill
        if elapsed > CLEANUP_THRESHOLD:
            bucket = TokenBucket(tokens=BURST, last_refill=now)
            buckets[ip] = bucket
        else:
            bucket.refill(now)
    else:
        bucket = TokenBucket(tokens=BURST, last_refill=now)
        buckets[ip] = bucket
    return bucket

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    
    if ip in WHITELIST:
        return await call_next(request)
    
    bucket = get_or_create_bucket(ip)
    allowed, retry_after = bucket.consume()
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after)}
        )
    
    response = await call_next(request)
    return response

@app.get("/")
async def root():
    return {"message": "Hello"}

@app.get("/status")
async def status(request: Request):
    ip = request.client.host if request.client else "unknown"
    bucket = buckets.get(ip)
    remaining = int(bucket.tokens) if bucket else BURST
    return {
        "ip": ip,
        "rate": RATE,
        "burst": BURST,
        "remaining_tokens": remaining,
        "whitelisted": ip in WHITELIST
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
