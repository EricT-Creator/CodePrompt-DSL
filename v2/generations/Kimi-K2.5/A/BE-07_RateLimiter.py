import time
import threading
from typing import Dict, Set
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_wait_time(self, tokens: int = 1) -> float:
        with self.lock:
            if self.tokens >= tokens:
                return 0
            return (tokens - self.tokens) / self.rate

    def get_token_count(self) -> float:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            return min(self.burst, self.tokens + elapsed * self.rate)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate: float = 1.0,
        burst: int = 5,
        whitelist: Set[str] = None
    ):
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or set()
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def get_bucket(self, ip: str) -> TokenBucket:
        with self.lock:
            if ip not in self.buckets:
                self.buckets[ip] = TokenBucket(self.rate, self.burst)
            return self.buckets[ip]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        if client_ip in self.whitelist:
            return await call_next(request)
        
        bucket = self.get_bucket(client_ip)
        
        if not bucket.consume():
            wait_time = bucket.get_wait_time()
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests",
                headers={"Retry-After": str(int(wait_time) + 1)}
            )
        
        return await call_next(request)


# Configure rate limiter: 1 request per second, burst of 5
# Whitelist localhost
rate_limiter = RateLimitMiddleware(
    app,
    rate=1.0,
    burst=5,
    whitelist={"127.0.0.1", "::1"}
)
app.add_middleware(RateLimitMiddleware, rate=1.0, burst=5, whitelist={"127.0.0.1", "::1"})


@app.get("/status")
async def get_status(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    
    # Get or create bucket for this IP
    middleware = None
    for m in request.app.user_middleware:
        if isinstance(m.cls, type) and m.cls.__name__ == "RateLimitMiddleware":
            break
    
    # Access the middleware instance through a workaround
    # Since we can't easily access the instance, we'll create a temporary bucket
    bucket = TokenBucket(1.0, 5)
    
    # Try to get from existing buckets
    for m in app.user_middleware:
        if hasattr(m, 'buckets') and client_ip in m.buckets:
            bucket = m.buckets[client_ip]
            break
    
    return {
        "ip": client_ip,
        "tokens": round(bucket.get_token_count(), 2),
        "rate": 1.0,
        "burst": 5
    }


@app.get("/")
async def root():
    return {"message": "Rate limited API"}


@app.get("/test")
async def test_endpoint():
    return {"message": "This endpoint is rate limited"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
