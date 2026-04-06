import asyncio
import math
import time
from typing import Dict, Optional, Set

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self.rate = rate
        self.burst = burst

class RateLimitConfig:
    def __init__(self, rate: float = 10.0, burst: int = 20, whitelist: Optional[Set[str]] = None):
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or {"127.0.0.1"}
        self.cleanup_interval = 300
        self.bucket_ttl = 3600

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        self.buckets: Dict[str, TokenBucket] = {}
        self.last_access: Dict[str, float] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
    
    async def startup(self):
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def shutdown(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(self.config.cleanup_interval)
            now = time.monotonic()
            stale = [ip for ip, last in self.last_access.items() if now - last > self.config.bucket_ttl]
            for ip in stale:
                self.buckets.pop(ip, None)
                self.last_access.pop(ip, None)
    
    def _get_bucket(self, ip: str) -> TokenBucket:
        now = time.monotonic()
        self.last_access[ip] = now
        
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.config.rate, self.config.burst)
            return self.buckets[ip]
        
        bucket = self.buckets[ip]
        elapsed = now - bucket.last_refill
        bucket.tokens = min(bucket.burst, bucket.tokens + elapsed * bucket.rate)
        bucket.last_refill = now
        return bucket
    
    def _calculate_retry_after(self, bucket: TokenBucket) -> int:
        deficit = 1.0 - bucket.tokens
        wait_seconds = deficit / bucket.rate
        return math.ceil(wait_seconds)
    
    def _calculate_reset_time(self, bucket: TokenBucket) -> int:
        tokens_needed = bucket.burst - bucket.tokens
        seconds_to_full = tokens_needed / bucket.rate
        return int(time.monotonic() + seconds_to_full)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        if client_ip in self.config.whitelist:
            return await call_next(request)
        
        bucket = self._get_bucket(client_ip)
        
        headers = {
            "X-RateLimit-Limit": str(bucket.burst),
            "X-RateLimit-Remaining": str(int(bucket.tokens)),
            "X-RateLimit-Reset": str(self._calculate_reset_time(bucket))
        }
        
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
            response = await call_next(request)
            for key, value in headers.items():
                response.headers[key] = value
            return response
        else:
            retry_after = self._calculate_retry_after(bucket)
            headers["Retry-After"] = str(retry_after)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
                headers=headers
            )

config = RateLimitConfig()
middleware = RateLimiterMiddleware(app, config)

@app.on_event("startup")
async def startup():
    await middleware.startup()

@app.on_event("shutdown")
async def shutdown():
    await middleware.shutdown()

app.add_middleware(RateLimiterMiddleware, config=config)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
