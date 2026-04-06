"""
Token Bucket Rate Limiter Middleware for FastAPI

This module implements a token bucket rate limiter with lazy refill,
IP-based client identification, and whitelist support.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Set

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ============================================================================
# Configuration
# ============================================================================

# Rate limiting parameters
DEFAULT_RATE = 10.0      # tokens per second
DEFAULT_BURST = 20.0     # maximum bucket capacity

# IP whitelist (exempt from rate limiting)
IP_WHITELIST: Set[str] = {
    "127.0.0.1",         # localhost
    "::1",               # IPv6 localhost
    "192.168.1.100",     # example internal IP
}

# Cleanup configuration
CLEANUP_INTERVAL_REQUESTS = 1000  # Run cleanup every N requests
INACTIVE_THRESHOLD_SECONDS = 3600  # 1 hour

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TokenBucket:
    """Represents a token bucket for a single client."""
    tokens: float = field(default_factory=lambda: DEFAULT_BURST)
    last_access: float = field(default_factory=time.monotonic)
    
    def refill(self, rate: float, burst: float) -> None:
        """Refill tokens based on elapsed time since last access."""
        current_time = time.monotonic()
        elapsed = current_time - self.last_access
        
        # Add tokens proportional to elapsed time
        self.tokens = min(self.tokens + elapsed * rate, burst)
        self.last_access = current_time
    
    def consume(self, tokens_needed: float = 1.0) -> bool:
        """Attempt to consume tokens from the bucket."""
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        return False
    
    def get_deficit(self, tokens_needed: float = 1.0) -> float:
        """Calculate token deficit if consumption would fail."""
        return max(0, tokens_needed - self.tokens)

class BucketStore:
    """Manages token buckets for all clients."""
    
    def __init__(self, rate: float = DEFAULT_RATE, burst: float = DEFAULT_BURST):
        self._buckets: Dict[str, TokenBucket] = {}
        self.rate = rate
        self.burst = burst
        self.request_count = 0
    
    def get_or_create(self, client_id: str) -> TokenBucket:
        """Get existing bucket or create a new one with full tokens."""
        if client_id not in self._buckets:
            self._buckets[client_id] = TokenBucket()
        return self._buckets[client_id]
    
    def consume(self, client_id: str, tokens_needed: float = 1.0) -> Tuple[bool, float]:
        """
        Attempt to consume tokens for a client.
        
        Returns:
            (allowed: bool, retry_after: float)
        """
        bucket = self.get_or_create(client_id)
        
        # Refill based on elapsed time
        bucket.refill(self.rate, self.burst)
        
        # Try to consume
        if bucket.consume(tokens_needed):
            self._maybe_cleanup()
            return True, 0.0
        
        # Calculate retry time
        deficit = bucket.get_deficit(tokens_needed)
        retry_after = deficit / self.rate
        self._maybe_cleanup()
        return False, retry_after
    
    def _maybe_cleanup(self) -> None:
        """Periodically clean up inactive buckets."""
        self.request_count += 1
        if self.request_count % CLEANUP_INTERVAL_REQUESTS == 0:
            self._cleanup_inactive()
    
    def _cleanup_inactive(self) -> None:
        """Remove buckets that haven't been accessed in a while."""
        current_time = time.monotonic()
        inactive_keys = [
            key for key, bucket in self._buckets.items()
            if current_time - bucket.last_access > INACTIVE_THRESHOLD_SECONDS
        ]
        
        for key in inactive_keys:
            del self._buckets[key]

# ============================================================================
# IP Extraction
# ============================================================================

def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles X-Forwarded-For header for proxied requests.
    """
    # Check X-Forwarded-For header (common with proxies/load balancers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, first one is the client
        return forwarded.split(",")[0].strip()
    
    # Fall back to client host
    if request.client:
        return request.client.host
    
    # Default fallback
    return "unknown"

# ============================================================================
# Middleware
# ============================================================================

def create_rate_limit_middleware(bucket_store: BucketStore):
    """Create rate limiting middleware with the given bucket store."""
    
    async def rate_limit_middleware(request: Request, call_next):
        # Extract client IP
        client_ip = get_client_ip(request)
        
        # Check whitelist
        if client_ip in IP_WHITELIST:
            response = await call_next(request)
            # Add whitelist indicator header
            response.headers["X-RateLimit-Whitelisted"] = "true"
            return response
        
        # Consume token
        allowed, retry_after = bucket_store.consume(client_ip)
        
        if not allowed:
            # Calculate Retry-After header (ceiling to integer)
            retry_after_ceil = int(math.ceil(retry_after))
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after_ceil),
                    "X-RateLimit-Reset": str(retry_after_ceil)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        bucket = bucket_store.get_or_create(client_ip)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Limit"] = str(int(bucket_store.burst))
        
        return response
    
    return rate_limit_middleware

# ============================================================================
# FastAPI Application Setup
# ============================================================================

# Create bucket store
bucket_store = BucketStore(rate=DEFAULT_RATE, burst=DEFAULT_BURST)

# Create middleware
rate_limit_middleware = create_rate_limit_middleware(bucket_store)

# Initialize FastAPI with middleware
app = FastAPI(
    title="Token Bucket Rate Limiter API",
    description="API with token bucket rate limiting and IP whitelist support",
    version="1.0.0",
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]
)

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit_wrapper(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

# ============================================================================
# Pydantic Models
# ============================================================================

class RateLimitConfig(BaseModel):
    """Configuration model for dynamic rate limiting."""
    rate: float = Field(DEFAULT_RATE, ge=0.1, le=1000.0, description="Tokens per second")
    burst: float = Field(DEFAULT_BURST, ge=1.0, le=10000.0, description="Maximum bucket capacity")

class RateLimitStatus(BaseModel):
    """Status model for rate limiting information."""
    client_ip: str = Field(..., description="Client IP address")
    tokens: float = Field(..., description="Current token count")
    last_access: float = Field(..., description="Timestamp of last access")
    rate: float = Field(..., description="Tokens per second")
    burst: float = Field(..., description="Maximum bucket capacity")
    whitelisted: bool = Field(..., description="Whether IP is whitelisted")

class WhitelistUpdate(BaseModel):
    """Model for updating IP whitelist."""
    ip: str = Field(..., description="IP address to add/remove")
    action: str = Field(..., pattern="^(add|remove)$", description="Action: 'add' or 'remove'")

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with rate limiting demonstration."""
    return {
        "message": "Token Bucket Rate Limiter API",
        "description": "All endpoints are rate limited with token bucket algorithm",
        "default_rate": DEFAULT_RATE,
        "default_burst": DEFAULT_BURST,
        "whitelisted_ips": list(IP_WHITELIST)
    }

@app.get("/api/data")
async def get_data():
    """Example endpoint that returns some data."""
    return {
        "data": [{"id": i, "value": f"item_{i}"} for i in range(10)],
        "timestamp": time.time()
    }

@app.post("/api/data")
async def create_data(item: dict):
    """Example endpoint for creating data."""
    return {
        "status": "created",
        "item": item,
        "timestamp": time.time()
    }

@app.get("/ratelimit/status")
async def get_rate_limit_status(request: Request):
    """Get rate limiting status for the current client."""
    client_ip = get_client_ip(request)
    whitelisted = client_ip in IP_WHITELIST
    
    if whitelisted:
        return RateLimitStatus(
            client_ip=client_ip,
            tokens=float('inf'),
            last_access=time.monotonic(),
            rate=bucket_store.rate,
            burst=bucket_store.burst,
            whitelisted=True
        )
    
    bucket = bucket_store.get_or_create(client_ip)
    return RateLimitStatus(
        client_ip=client_ip,
        tokens=bucket.tokens,
        last_access=bucket.last_access,
        rate=bucket_store.rate,
        burst=bucket_store.burst,
        whitelisted=False
    )

@app.post("/ratelimit/config", status_code=status.HTTP_201_CREATED)
async def update_rate_limit_config(config: RateLimitConfig):
    """Update global rate limiting configuration (admin endpoint)."""
    # In a production system, this would require authentication
    bucket_store.rate = config.rate
    bucket_store.burst = config.burst
    
    return {
        "message": "Rate limit configuration updated",
        "new_rate": config.rate,
        "new_burst": config.burst
    }

@app.post("/ratelimit/whitelist", status_code=status.HTTP_201_CREATED)
async def update_whitelist(update: WhitelistUpdate):
    """Add or remove IP from whitelist (admin endpoint)."""
    if update.action == "add":
        IP_WHITELIST.add(update.ip)
        action = "added"
    else:  # remove
        IP_WHITELIST.discard(update.ip)
        action = "removed"
    
    return {
        "message": f"IP {update.ip} {action} to/from whitelist",
        "whitelist": list(IP_WHITELIST)
    }

@app.get("/ratelimit/stats")
async def get_rate_limit_stats():
    """Get rate limiting statistics (admin endpoint)."""
    return {
        "active_buckets": len(bucket_store._buckets),
        "total_requests": bucket_store.request_count,
        "rate": bucket_store.rate,
        "burst": bucket_store.burst,
        "whitelist_size": len(IP_WHITELIST)
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "rate_limiter": "active"
    }

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)