import time
import threading
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Data models
class RateLimitConfig(BaseModel):
    rate_per_second: float = Field(default=1.0, description="Tokens added per second")
    burst_size: int = Field(default=5, description="Maximum tokens in bucket")
    whitelist_ips: list[str] = Field(default=[], description="IPs that bypass rate limiting")

class TokenBucketStatus(BaseModel):
    ip: str
    current_tokens: float
    last_refill_time: float
    max_tokens: int
    refill_rate: float
    is_whitelisted: bool

class RateLimitStats(BaseModel):
    total_requests: int
    limited_requests: int
    whitelisted_requests: int
    active_buckets: int
    whitelisted_ips: list[str]

# Token Bucket implementation
class TokenBucket:
    def __init__(self, rate_per_second: float, burst_size: int):
        self.rate_per_second = rate_per_second
        self.max_tokens = burst_size
        self.current_tokens = burst_size
        self.last_refill_time = time.time()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        time_passed = now - self.last_refill_time
        tokens_to_add = time_passed * self.rate_per_second
        
        with self.lock:
            self.current_tokens = min(
                self.max_tokens,
                self.current_tokens + tokens_to_add
            )
            self.last_refill_time = now
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens from the bucket.
        Returns: (success, wait_time_seconds)
        """
        self._refill()
        
        with self.lock:
            if self.current_tokens >= tokens:
                self.current_tokens -= tokens
                return True, 0.0
            else:
                # Calculate wait time
                tokens_needed = tokens - self.current_tokens
                wait_time = tokens_needed / self.rate_per_second
                return False, wait_time
    
    def get_status(self) -> Dict:
        """Get current bucket status."""
        self._refill()
        
        with self.lock:
            return {
                "current_tokens": self.current_tokens,
                "last_refill_time": self.last_refill_time,
                "max_tokens": self.max_tokens,
                "rate_per_second": self.rate_per_second
            }

# Rate Limiter Middleware
class RateLimiterMiddleware:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(config.rate_per_second, config.burst_size)
        )
        self.lock = threading.Lock()
        self.stats = {
            "total_requests": 0,
            "limited_requests": 0,
            "whitelisted_requests": 0
        }
        
        # Convert whitelist to set for faster lookup
        self.whitelist_ips = set(config.whitelist_ips)
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the list
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "127.0.0.1"
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist."""
        return ip in self.whitelist_ips
    
    async def __call__(self, request: Request, call_next):
        # Update stats
        with self.lock:
            self.stats["total_requests"] += 1
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check whitelist
        if self.is_whitelisted(client_ip):
            with self.lock:
                self.stats["whitelisted_requests"] += 1
            response = await call_next(request)
            response.headers["X-RateLimit-Whitelisted"] = "true"
            return response
        
        # Get or create bucket for this IP
        with self.lock:
            bucket = self.buckets[client_ip]
        
        # Try to consume token
        success, wait_time = bucket.consume()
        
        if not success:
            with self.lock:
                self.stats["limited_requests"] += 1
            
            # Return 429 Too Many Requests
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Try again in {wait_time:.1f} seconds.",
                    "retry_after": wait_time
                }
            )
            response.headers["Retry-After"] = str(int(wait_time) + 1)  # Round up to nearest second
            
            # Add rate limit headers
            bucket_status = bucket.get_status()
            response.headers["X-RateLimit-Limit"] = str(self.config.burst_size)
            response.headers["X-RateLimit-Remaining"] = str(int(bucket_status["current_tokens"]))
            response.headers["X-RateLimit-Reset"] = str(int(bucket_status["last_refill_time"] + 
                                                          (self.config.burst_size - bucket_status["current_tokens"]) / 
                                                          self.config.rate_per_second))
            
            return response
        
        # Request allowed, proceed
        response = await call_next(request)
        
        # Add rate limit headers
        bucket_status = bucket.get_status()
        response.headers["X-RateLimit-Limit"] = str(self.config.burst_size)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket_status["current_tokens"]))
        response.headers["X-RateLimit-Reset"] = str(int(bucket_status["last_refill_time"] + 
                                                      (self.config.burst_size - bucket_status["current_tokens"]) / 
                                                      self.config.rate_per_second))
        
        return response
    
    def get_bucket_status(self, ip: str) -> Optional[TokenBucketStatus]:
        """Get status of a specific bucket."""
        if ip in self.buckets:
            bucket = self.buckets[ip]
            status = bucket.get_status()
            return TokenBucketStatus(
                ip=ip,
                current_tokens=status["current_tokens"],
                last_refill_time=status["last_refill_time"],
                max_tokens=status["max_tokens"],
                refill_rate=status["rate_per_second"],
                is_whitelisted=self.is_whitelisted(ip)
            )
        return None
    
    def get_stats(self) -> RateLimitStats:
        """Get overall statistics."""
        with self.lock:
            return RateLimitStats(
                total_requests=self.stats["total_requests"],
                limited_requests=self.stats["limited_requests"],
                whitelisted_requests=self.stats["whitelisted_requests"],
                active_buckets=len(self.buckets),
                whitelisted_ips=list(self.whitelist_ips)
            )
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove buckets that haven't been used for a while."""
        now = time.time()
        to_remove = []
        
        with self.lock:
            for ip, bucket in self.buckets.items():
                status = bucket.get_status()
                if now - status["last_refill_time"] > max_age_seconds:
                    to_remove.append(ip)
            
            for ip in to_remove:
                del self.buckets[ip]

# FastAPI app
app = FastAPI(
    title="Rate Limiter API",
    version="1.0.0",
    description="Token Bucket Rate Limiter with per-IP tracking"
)

# Rate limiter configuration
rate_limit_config = RateLimitConfig(
    rate_per_second=1.0,  # 1 request per second
    burst_size=5,         # Allow bursts of up to 5 requests
    whitelist_ips=["127.0.0.1", "::1"]  # Localhost is whitelisted
)

# Create rate limiter middleware
rate_limiter = RateLimiterMiddleware(rate_limit_config)

# Add middleware to app
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    return await rate_limiter(request, call_next)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get client IP
def get_client_ip(request: Request) -> str:
    return rate_limiter.get_client_ip(request)

# Routes
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Rate Limiter API",
        "endpoints": {
            "GET /": "This info page",
            "GET /status": "Get rate limit status for your IP",
            "GET /stats": "Get overall rate limit statistics",
            "GET /protected": "Protected endpoint (rate limited)",
            "POST /protected": "Protected endpoint (rate limited)",
            "GET /whitelist": "Get whitelisted IPs",
            "POST /cleanup": "Clean up old buckets (admin)"
        },
        "rate_limit_config": rate_limit_config.dict()
    }

@app.get("/status")
async def get_status(request: Request, client_ip: str = Depends(get_client_ip)):
    """Get rate limit status for the requesting IP."""
    bucket_status = rate_limiter.get_bucket_status(client_ip)
    
    if bucket_status:
        return {
            "ip": client_ip,
            "status": bucket_status.dict(),
            "is_whitelisted": rate_limiter.is_whitelisted(client_ip),
            "headers_explanation": {
                "X-RateLimit-Limit": "Maximum burst size",
                "X-RateLimit-Remaining": "Tokens remaining in bucket",
                "X-RateLimit-Reset": "Unix timestamp when bucket will be full",
                "Retry-After": "Seconds to wait when rate limited (429)"
            }
        }
    else:
        return {
            "ip": client_ip,
            "status": "No active rate limit bucket",
            "is_whitelisted": rate_limiter.is_whitelisted(client_ip),
            "message": "Bucket will be created on first request"
        }

@app.get("/stats")
async def get_stats():
    """Get overall rate limit statistics."""
    stats = rate_limiter.get_stats()
    
    # Calculate success rate
    total_allowed = stats.total_requests - stats.limited_requests
    success_rate = (total_allowed / stats.total_requests * 100) if stats.total_requests > 0 else 0
    
    return {
        "statistics": stats.dict(),
        "calculated_metrics": {
            "success_rate_percent": round(success_rate, 2),
            "limit_rate_percent": round((stats.limited_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0, 2),
            "whitelist_rate_percent": round((stats.whitelisted_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0, 2),
            "average_requests_per_bucket": round(stats.total_requests / max(stats.active_buckets, 1), 2)
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/protected")
async def protected_get(request: Request):
    """Protected GET endpoint."""
    return {
        "message": "This is a rate-limited GET endpoint",
        "timestamp": datetime.now().isoformat(),
        "your_ip": rate_limiter.get_client_ip(request),
        "rate_limit_info": "Check response headers for rate limit status"
    }

@app.post("/protected")
async def protected_post(request: Request):
    """Protected POST endpoint."""
    try:
        body = await request.json()
    except:
        body = {}
    
    return {
        "message": "This is a rate-limited POST endpoint",
        "timestamp": datetime.now().isoformat(),
        "your_ip": rate_limiter.get_client_ip(request),
        "received_data": body,
        "rate_limit_info": "Check response headers for rate limit status"
    }

@app.get("/whitelist")
async def get_whitelist():
    """Get list of whitelisted IPs."""
    return {
        "whitelisted_ips": list(rate_limiter.whitelist_ips),
        "count": len(rate_limiter.whitelist_ips),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/cleanup")
async def cleanup_buckets(max_age_seconds: int = 3600):
    """Clean up old rate limit buckets (admin endpoint)."""
    old_count = len(rate_limiter.buckets)
    rate_limiter.cleanup_old_buckets(max_age_seconds)
    new_count = len(rate_limiter.buckets)
    
    return {
        "message": "Old buckets cleaned up",
        "removed_count": old_count - new_count,
        "remaining_buckets": new_count,
        "max_age_seconds": max_age_seconds,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test/multiple")
async def test_multiple_requests():
    """Test endpoint for making multiple quick requests."""
    return {
        "message": "Test request successful",
        "timestamp": datetime.now().isoformat(),
        "request_number": "Check rate limit headers"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 429:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": exc.detail,
                "retry_after": request.headers.get("Retry-After", "unknown")
            },
            headers={"Retry-After": request.headers.get("Retry-After", "60")}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# Background task to periodically clean up old buckets
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Rate Limiter API starting up...")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    print("Rate Limiter API shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

async def periodic_cleanup():
    """Periodically clean up old buckets every hour."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        rate_limiter.cleanup_old_buckets(3600)
        print(f"Periodic cleanup completed. Active buckets: {len(rate_limiter.buckets)}")

# Update app with lifespan
app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)