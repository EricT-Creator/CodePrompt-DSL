import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Token Bucket Rate Limiter")

# Token Bucket implementation
class TokenBucket:
    def __init__(self, rate: float, burst: int):
        """
        Initialize a token bucket.
        
        Args:
            rate: Tokens per second
            burst: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = burst
        self.tokens = burst
        self.last_refill = time.time()
    
    def refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate
        
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Returns:
            True if tokens were consumed, False otherwise
        """
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_remaining_tokens(self) -> float:
        """Get current token count"""
        self.refill()
        return self.tokens
    
    def get_time_to_next_token(self) -> float:
        """Get time until next token is available"""
        self.refill()
        
        if self.tokens >= 1:
            return 0.0
        
        tokens_needed = 1 - self.tokens
        return tokens_needed / self.rate

# Rate limiter manager
class RateLimiter:
    def __init__(self, default_rate: float = 10, default_burst: int = 20):
        """
        Initialize rate limiter with default settings.
        
        Args:
            default_rate: Default tokens per second
            default_burst: Default burst capacity
        """
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(default_rate, default_burst)
        )
        self.whitelist: set = set()
    
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist (bypass rate limiting)"""
        self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist"""
        self.whitelist.discard(ip)
    
    def set_limit(self, ip: str, rate: float, burst: int):
        """Set custom rate limit for specific IP"""
        self.buckets[ip] = TokenBucket(rate, burst)
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist"""
        return ip in self.whitelist
    
    def check_limit(self, ip: str) -> tuple[bool, Optional[float]]:
        """
        Check rate limit for IP.
        
        Returns:
            (allowed, retry_after_seconds)
        """
        if self.is_whitelisted(ip):
            return True, None
        
        bucket = self.buckets[ip]
        
        if bucket.consume():
            return True, None
        
        retry_after = bucket.get_time_to_next_token()
        return False, retry_after
    
    def get_status(self, ip: str) -> Dict:
        """Get rate limit status for IP"""
        bucket = self.buckets[ip]
        
        return {
            "ip": ip,
            "whitelisted": self.is_whitelisted(ip),
            "rate_per_second": bucket.rate,
            "burst_capacity": bucket.capacity,
            "remaining_tokens": bucket.get_remaining_tokens(),
            "time_to_next_token": bucket.get_time_to_next_token(),
            "last_refill": bucket.last_refill,
        }

# Global rate limiter instance
rate_limiter = RateLimiter(default_rate=5, default_burst=10)

# Add some IPs to whitelist for testing
rate_limiter.add_to_whitelist("127.0.0.1")
rate_limiter.add_to_whitelist("::1")

# Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit
    allowed, retry_after = rate_limiter.check_limit(client_ip)
    
    if not allowed:
        # Create 429 response with Retry-After header
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": "Rate limit exceeded",
                "retry_after": retry_after,
            }
        )
        response.headers["Retry-After"] = str(int(retry_after) + 1)  # Add 1 second buffer
        return response
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    status = rate_limiter.get_status(client_ip)
    response.headers["X-RateLimit-Limit"] = str(status["burst_capacity"])
    response.headers["X-RateLimit-Remaining"] = str(int(status["remaining_tokens"]))
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + status["time_to_next_token"]))
    
    return response

# Models
class RateLimitConfig(BaseModel):
    rate: float
    burst: int

class WhitelistRequest(BaseModel):
    ip: str

class StatusResponse(BaseModel):
    ip: str
    whitelisted: bool
    rate_per_second: float
    burst_capacity: int
    remaining_tokens: float
    time_to_next_token: float

# Routes
@app.get("/")
async def root():
    return {
        "message": "Token Bucket Rate Limiter API",
        "endpoints": {
            "/": "This info",
            "/protected": "Protected endpoint",
            "/status": "Get rate limit status",
            "/admin/whitelist": "Manage whitelist (POST)",
            "/admin/config": "Configure rate limits (POST)",
        }
    }

@app.get("/protected")
async def protected_endpoint():
    """Protected endpoint that requires rate limiting"""
    return {
        "message": "This is a protected endpoint",
        "timestamp": datetime.now().isoformat(),
        "request_allowed": True,
    }

@app.get("/status", response_model=StatusResponse)
async def get_status(request: Request):
    """Get rate limit status for current requester"""
    client_ip = request.client.host if request.client else "unknown"
    status = rate_limiter.get_status(client_ip)
    return StatusResponse(**status)

# Admin endpoints (in production, these should be protected)
@app.post("/admin/whitelist")
async def add_to_whitelist(request: WhitelistRequest):
    """Add IP to whitelist (bypass rate limiting)"""
    rate_limiter.add_to_whitelist(request.ip)
    return {"message": f"IP {request.ip} added to whitelist"}

@app.delete("/admin/whitelist/{ip}")
async def remove_from_whitelist(ip: str):
    """Remove IP from whitelist"""
    rate_limiter.remove_from_whitelist(ip)
    return {"message": f"IP {ip} removed from whitelist"}

@app.post("/admin/config/{ip}")
async def configure_rate_limit(ip: str, config: RateLimitConfig):
    """Configure custom rate limit for specific IP"""
    if config.rate <= 0 or config.burst <= 0:
        raise HTTPException(
            status_code=400,
            detail="Rate and burst must be positive numbers"
        )
    
    rate_limiter.set_limit(ip, config.rate, config.burst)
    return {
        "message": f"Rate limit configured for {ip}",
        "config": config.dict(),
    }

@app.get("/admin/buckets")
async def list_all_buckets():
    """List all active token buckets (admin only)"""
    buckets_info = {}
    for ip, bucket in rate_limiter.buckets.items():
        buckets_info[ip] = {
            "rate": bucket.rate,
            "capacity": bucket.capacity,
            "remaining": bucket.get_remaining_tokens(),
            "whitelisted": ip in rate_limiter.whitelist,
        }
    
    return {
        "total_buckets": len(buckets_info),
        "whitelisted_ips": list(rate_limiter.whitelist),
        "buckets": buckets_info,
    }

# Test endpoint for load testing
@app.get("/test/load")
async def load_test_endpoint():
    """Endpoint for testing rate limiting"""
    return {
        "message": "Load test successful",
        "timestamp": datetime.now().isoformat(),
        "data": {"test": "value", "count": 42},
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)