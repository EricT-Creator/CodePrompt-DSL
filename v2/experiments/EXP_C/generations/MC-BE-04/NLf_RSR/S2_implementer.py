from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict
import time
import math
import asyncio
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
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        async def cleanup():
            while True:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_stale_buckets()
        
        asyncio.create_task(cleanup())
    
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
        # Try to get real IP from various headers
        if request.client:
            return request.client.host
        
        # Fallback to X-Forwarded-For
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        # Last resort
        return "unknown"
    
    def _should_rate_limit(self, request: Request) -> bool:
        # Check if path should be excluded
        path = request.url.path
        
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        # Check if path should be included
        for include_path in self.include_paths:
            if path.startswith(include_path):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Check if we should rate limit this request
        if not self._should_rate_limit(request):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check whitelist
        if client_ip in self.rate_limiter.config.whitelist:
            response = await call_next(request)
            self._add_rate_limit_headers(response, -1, -1, -1)
            return response
        
        # Try to consume a token
        allowed, retry_after = await self.rate_limiter.consume(client_ip)
        
        if not allowed:
            # Rate limit exceeded
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
        
        # Request allowed
        response = await call_next(request)
        
        # Add rate limit headers
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
        """Estimate remaining tokens for a client (for headers)"""
        if key in self.rate_limiter.buckets:
            bucket = self.rate_limiter.buckets[key]
            now = time.monotonic()
            
            # Refill tokens
            elapsed = now - bucket.last_refill
            tokens_to_add = elapsed * bucket.rate
            estimated_tokens = min(bucket.burst, bucket.tokens + tokens_to_add)
            
            return int(max(0, math.floor(estimated_tokens)))
        
        return self.rate_limiter.config.burst

# ===================== API Endpoints =====================

# Create rate limiter with default config
rate_limit_config = RateLimitConfig(
    rate=10.0,      # 10 requests per second
    burst=20,       # Maximum burst of 20 requests
    whitelist={"127.0.0.1", "::1", "10.0.0.1"},
)
rate_limiter = TokenBucketRateLimiter(rate_limit_config)

# Add middleware
app.add_middleware(
    RateLimiterMiddleware,
    rate_limiter=rate_limiter,
    include_paths=["/api/"],
    exclude_paths=["/health", "/docs", "/redoc"]
)

# JSON encoder
import json

# Sample endpoints to test rate limiting

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

# Unprotected endpoints

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

# Admin endpoints for managing rate limits

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