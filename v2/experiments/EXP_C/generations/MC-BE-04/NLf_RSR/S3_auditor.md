## Constraint Review
- C1 (Python + FastAPI): PASS — `from fastapi import FastAPI, Request, Response`; `app = FastAPI(title="Token Bucket Rate Limiter")`.
- C2 (Token Bucket, no counter): PASS — `TokenBucket` dataclass with `tokens`, `rate`, `burst`, `last_refill`; `consume()` method refills tokens via `elapsed * bucket.rate` and caps at `bucket.burst`; classic token bucket algorithm, not a simple counter or fixed window.
- C3 (stdlib + fastapi, no Redis): PASS — Imports only from standard library (time, math, asyncio, dataclasses, datetime, json, typing) and fastapi; no Redis/memcached.
- C4 (Single file): PASS — All code (TokenBucket, RateLimitConfig, TokenBucketRateLimiter, middleware, endpoints) in a single file.
- C5 (429 + Retry-After + whitelist): PASS — Returns `status_code=429` with `response.headers["Retry-After"] = str(math.ceil(retry_after))`; whitelist check via `if client_ip in self.rate_limiter.config.whitelist:` bypasses rate limiting.
- C6 (Code only): PASS — File contains only code with no explanation text outside of code comments.

## Functionality Assessment (0-5)
Score: 4 — Complete token bucket rate limiter with: configurable rate/burst capacity, per-IP rate limiting via middleware, IP whitelist bypass, proper HTTP 429 response with Retry-After header, X-RateLimit-* headers (Limit/Remaining/Reset), path-based include/exclude filtering, async lock for thread safety, stale bucket cleanup task, admin endpoints for whitelist management and bucket inspection. Minor issue: `_start_cleanup_task()` calls `asyncio.create_task()` during `__init__`, which will fail if no event loop is running at module load time (the rate limiter is instantiated at module level before FastAPI's event loop starts). Also `import json` appears mid-file rather than at top.

## Corrected Code
```py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict
import time
import math
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

app = FastAPI(title="Token Bucket Rate Limiter")

# ===================== Token Bucket Implementation =====================

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float
    rate: float  # tokens per second
    burst: int   # maximum tokens

class RateLimitConfig:
    def __init__(
        self,
        rate: float = 10.0,        # 10 requests per second
        burst: int = 20,           # maximum burst capacity
        whitelist: Optional[set] = None,
        cleanup_interval: int = 300,  # 5 minutes
        bucket_ttl: int = 3600      # 1 hour
    ):
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or {"127.0.0.1", "::1"}
        self.cleanup_interval = cleanup_interval
        self.bucket_ttl = bucket_ttl

class TokenBucketRateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = asyncio.Lock()
        self._cleanup_task = None
    
    def start_cleanup_task(self):
        """Start the cleanup task. Must be called within a running event loop."""
        if self._cleanup_task is None:
            async def cleanup():
                while True:
                    await asyncio.sleep(self.config.cleanup_interval)
                    await self._cleanup_stale_buckets()
            self._cleanup_task = asyncio.create_task(cleanup())
    
    async def _cleanup_stale_buckets(self):
        async with self.lock:
            now = time.monotonic()
            stale_keys = []
            
            for key, bucket in self.buckets.items():
                if now - bucket.last_refill > self.config.bucket_ttl:
                    stale_keys.append(key)
            
            for key in stale_keys:
                del self.buckets[key]
    
    async def consume(self, key: str) -> tuple[bool, float]:
        """Try to consume one token from the bucket.
        Returns (allowed, retry_after) where retry_after is seconds until token available."""
        async with self.lock:
            now = time.monotonic()
            
            # Get or create bucket
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(
                    tokens=self.config.burst,
                    last_refill=now,
                    rate=self.config.rate,
                    burst=self.config.burst
                )
            
            bucket = self.buckets[key]
            
            # Refill tokens based on elapsed time
            elapsed = now - bucket.last_refill
            tokens_to_add = elapsed * bucket.rate
            bucket.tokens = min(bucket.burst, bucket.tokens + tokens_to_add)
            bucket.last_refill = now
            
            # Try to consume one token
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0.0
            
            # Not enough tokens
            deficit = 1.0 - bucket.tokens
            wait_seconds = deficit / bucket.rate
            return False, wait_seconds

# ===================== Rate Limiter Middleware =====================

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate_limiter: TokenBucketRateLimiter,
        include_paths: Optional[list] = None,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.include_paths = include_paths or ["/"]
        self.exclude_paths = exclude_paths or []
    
    def _get_client_ip(self, request: Request) -> str:
        if request.client:
            return request.client.host
        
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        return "unknown"
    
    def _should_rate_limit(self, request: Request) -> bool:
        path = request.url.path
        
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        for include_path in self.include_paths:
            if path.startswith(include_path):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        if not self._should_rate_limit(request):
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        if client_ip in self.rate_limiter.config.whitelist:
            response = await call_next(request)
            self._add_rate_limit_headers(response, -1, -1, -1)
            return response
        
        allowed, retry_after = await self.rate_limiter.consume(client_ip)
        
        if not allowed:
            response = Response(
                content=json.dumps({
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Try again in {math.ceil(retry_after)} seconds.",
                    "retry_after": math.ceil(retry_after)
                }),
                status_code=429,
                media_type="application/json"
            )
            response.headers["Retry-After"] = str(math.ceil(retry_after))
            self._add_rate_limit_headers(response, 0, 0, math.ceil(retry_after))
            return response
        
        response = await call_next(request)
        
        self._add_rate_limit_headers(
            response,
            self.rate_limiter.config.burst,
            self._estimate_remaining_tokens(client_ip),
            math.ceil(retry_after) if retry_after > 0 else 0
        )
        
        return response
    
    def _add_rate_limit_headers(
        self,
        response: Response,
        limit: int,
        remaining: int,
        reset: int
    ):
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + reset if reset > 0 else int(time.time())
        )
    
    def _estimate_remaining_tokens(self, key: str) -> int:
        if key in self.rate_limiter.buckets:
            bucket = self.rate_limiter.buckets[key]
            now = time.monotonic()
            
            elapsed = now - bucket.last_refill
            tokens_to_add = elapsed * bucket.rate
            estimated_tokens = min(bucket.burst, bucket.tokens + tokens_to_add)
            
            return int(max(0, math.floor(estimated_tokens)))
        
        return self.rate_limiter.config.burst

# ===================== API Endpoints =====================

rate_limit_config = RateLimitConfig(
    rate=10.0,
    burst=20,
    whitelist={"127.0.0.1", "::1", "10.0.0.1"},
)
rate_limiter = TokenBucketRateLimiter(rate_limit_config)

app.add_middleware(
    RateLimiterMiddleware,
    rate_limiter=rate_limiter,
    include_paths=["/api/"],
    exclude_paths=["/health", "/docs", "/redoc"]
)

@app.on_event("startup")
async def startup_event():
    rate_limiter.start_cleanup_task()

@app.get("/api/public")
async def public_endpoint():
    return {
        "message": "This is a public endpoint with rate limiting",
        "timestamp": time.time(),
        "rate_limit_info": {
            "rate": rate_limit_config.rate,
            "burst": rate_limit_config.burst
        }
    }

@app.post("/api/data")
async def post_data(request: Request):
    try:
        data = await request.json()
        return {
            "message": "Data received",
            "data": data,
            "timestamp": time.time()
        }
    except Exception:
        return {"error": "Invalid JSON"}

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "timestamp": time.time()
    }

@app.get("/api/admin/stats")
async def admin_stats():
    return {
        "active_buckets": len(rate_limiter.buckets),
        "config": {
            "rate": rate_limit_config.rate,
            "burst": rate_limit_config.burst,
            "whitelist_size": len(rate_limit_config.whitelist)
        },
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/")
async def root():
    return {
        "message": "Token Bucket Rate Limiter API",
        "endpoints": {
            "public": "/api/public",
            "post_data": "/api/data",
            "get_user": "/api/users/{id}",
            "admin_stats": "/api/admin/stats",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.post("/admin/whitelist/add/{ip}")
async def add_to_whitelist(ip: str):
    rate_limit_config.whitelist.add(ip)
    return {
        "message": f"Added {ip} to whitelist",
        "whitelist": list(rate_limit_config.whitelist)
    }

@app.post("/admin/whitelist/remove/{ip}")
async def remove_from_whitelist(ip: str):
    if ip in rate_limit_config.whitelist:
        rate_limit_config.whitelist.remove(ip)
    return {
        "message": f"Removed {ip} from whitelist",
        "whitelist": list(rate_limit_config.whitelist)
    }

@app.get("/admin/buckets")
async def list_buckets():
    buckets_info = {}
    now = time.monotonic()
    
    for key, bucket in rate_limiter.buckets.items():
        elapsed = now - bucket.last_refill
        tokens_to_add = elapsed * bucket.rate
        estimated_tokens = min(bucket.burst, bucket.tokens + tokens_to_add)
        
        buckets_info[key] = {
            "tokens": estimated_tokens,
            "last_refill": bucket.last_refill,
            "rate": bucket.rate,
            "burst": bucket.burst
        }
    
    return {
        "total_buckets": len(buckets_info),
        "buckets": buckets_info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
