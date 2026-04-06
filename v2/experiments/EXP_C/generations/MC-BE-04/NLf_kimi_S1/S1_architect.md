# MC-BE-04: Token Bucket Rate Limiter - Technical Design

## Overview

This document outlines the technical design for a FastAPI Token Bucket rate limiter middleware with per-IP bucket management, Retry-After header support, and IP whitelist bypass.

## 1. Token Bucket Algorithm Details

### Algorithm Explanation

The Token Bucket algorithm controls request rate by maintaining a "bucket" of tokens for each client:

- **Bucket Capacity**: Maximum burst size (e.g., 10 requests)
- **Refill Rate**: Tokens added per second (e.g., 2 tokens/sec)
- **Token Cost**: Each request consumes 1 token
- **Empty Bucket**: Requests rejected when no tokens available

### State Transitions

```
Request Arrives:
  ├─ Calculate tokens to add: (now - last_update) × refill_rate
  ├─ Update bucket: min(capacity, current_tokens + new_tokens)
  ├─ Check if tokens >= 1
  │   ├─ Yes: Decrement tokens, allow request
  │   └─ No:  Reject with 429, calculate Retry-After
  └─ Update last_update timestamp
```

### Bucket Data Structure

```python
from dataclasses import dataclass
from time import time

@dataclass
class TokenBucket:
    capacity: int           # Maximum burst size
    refill_rate: float      # Tokens per second
    tokens: float           # Current token count
    last_update: float      # Last timestamp (seconds)
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if successful."""
        now = time()
        
        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now
        
        # Check if enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate seconds until enough tokens available."""
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.refill_rate
```

## 2. Per-IP Bucket Management

### Bucket Registry

```python
class RateLimiter:
    def __init__(
        self,
        capacity: int = 10,
        refill_rate: float = 2.0,
        whitelist: Optional[Set[str]] = None
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.whitelist = whitelist or set()
        
        # IP address -> TokenBucket
        self.buckets: Dict[str, TokenBucket] = {}
    
    def get_bucket(self, ip: str) -> TokenBucket:
        """Get or create bucket for IP address."""
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(
                capacity=self.capacity,
                refill_rate=self.refill_rate,
                tokens=self.capacity,  # Start full
                last_update=time()
            )
        return self.buckets[ip]
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist."""
        return ip in self.whitelist
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, float]:
        """
        Check if request should be allowed.
        Returns: (allowed: bool, retry_after: float)
        """
        if self.is_whitelisted(ip):
            return True, 0
        
        bucket = self.get_bucket(ip)
        allowed = bucket.consume(1)
        
        if allowed:
            return True, 0
        
        retry_after = bucket.time_until_available(1)
        return False, retry_after
```

### IP Extraction

```python
def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (for proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    return request.client.host if request.client else "unknown"
```

## 3. Middleware Integration

### FastAPI Middleware

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        capacity: int = 10,
        refill_rate: float = 2.0,
        whitelist: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter(capacity, refill_rate, whitelist)
    
    async def dispatch(self, request: Request, call_next):
        # Extract client IP
        client_ip = get_client_ip(request)
        
        # Check rate limit
        allowed, retry_after = self.limiter.check_rate_limit(client_ip)
        
        if not allowed:
            return Response(
                content=json.dumps({
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after
                }),
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
                media_type="application/json"
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        bucket = self.limiter.get_bucket(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        
        return response
```

### Alternative: Dependency-Based Rate Limiting

```python
async def rate_limit_dependency(
    request: Request,
    capacity: int = 10,
    refill_rate: float = 2.0
) -> None:
    """Dependency for endpoint-specific rate limiting."""
    client_ip = get_client_ip(request)
    
    # Use app state for shared limiter
    limiter: RateLimiter = request.app.state.rate_limiter
    allowed, retry_after = limiter.check_rate_limit(client_ip)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after) + 1)}
        )

# Usage on specific endpoints
@app.get("/api/data")
async def get_data(_: None = Depends(rate_limit_dependency)):
    return {"data": "..."}
```

## 4. Retry-After Calculation

### Calculation Logic

```python
def calculate_retry_after(bucket: TokenBucket) -> int:
    """
    Calculate Retry-After header value in seconds.
    Rounds up to ensure client waits long enough.
    """
    seconds = bucket.time_until_available(1)
    return int(seconds) + 1  # Round up, add buffer
```

### HTTP 429 Response

```python
{
    "error": "Rate limit exceeded",
    "message": "Too many requests. Please slow down.",
    "retry_after": 3,
    "limit": 10,
    "window": "per second"
}
```

### Response Headers

| Header | Description |
|--------|-------------|
| `Retry-After` | Seconds until request will be accepted |
| `X-RateLimit-Limit` | Maximum burst size |
| `X-RateLimit-Remaining` | Current available tokens |

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python + FastAPI** | Use FastAPI with Starlette middleware base class |
| **Token Bucket algorithm** | Implement `TokenBucket` class with capacity, refill_rate, consume() method |
| **Standard library + FastAPI only** | No Redis, memcached, or external storage; in-memory Dict for buckets |
| **Single Python file** | All code (TokenBucket, RateLimiter, middleware, helpers) in one file |
| **HTTP 429 + Retry-After** | Return 429 status with Retry-After header calculated from token deficit |
| **IP whitelist bypass** | `whitelist: Set[str]` checked before rate limiting; whitelisted IPs skip all checks |
| **Output code only** | Design structured for direct implementation |

## Summary

This design implements a Token Bucket rate limiter using only Python's standard library. Each IP address gets its own bucket tracking tokens and last update time. The algorithm allows burst traffic up to capacity while maintaining average rate through refill. Whitelisted IPs bypass all checks. The middleware integrates cleanly with FastAPI's request/response cycle, adding rate limit headers to successful responses and proper Retry-After values to throttled requests.
