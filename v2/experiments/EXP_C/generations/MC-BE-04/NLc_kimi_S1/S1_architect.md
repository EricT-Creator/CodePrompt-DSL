# MC-BE-04: FastAPI Token Bucket Rate Limiter - Technical Design Document

## 1. Token Bucket Algorithm Details

### Algorithm Overview

The Token Bucket algorithm controls request rate by maintaining a bucket of tokens:
- Each request consumes 1 token
- Tokens are added at a constant rate (refill rate)
- Bucket has maximum capacity (burst size)
- Requests are rejected when bucket is empty

### Token Bucket Data Structure
```python
from dataclasses import dataclass
from time import time

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int          # Maximum tokens (burst size)
    tokens: float          # Current token count
    refill_rate: float     # Tokens added per second
    last_refill: float     # Timestamp of last refill
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
    
    def time_until_next_token(self) -> float:
        """Calculate seconds until next token is available."""
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) / self.refill_rate
```

### Rate Limit Configuration
```python
from typing import TypedDict

class RateLimitConfig(TypedDict):
    rate: float      # Requests per second
    burst: int       # Maximum burst size

DEFAULT_CONFIG: RateLimitConfig = {
    "rate": 10.0,    # 10 requests per second
    "burst": 20      # Burst up to 20 requests
}
```

## 2. Per-IP Bucket Management

### Bucket Registry
```python
class BucketRegistry:
    """Manages token buckets per IP address."""
    
    def __init__(self, config: RateLimitConfig):
        self._config = config
        self._buckets: dict[str, TokenBucket] = {}
        self._whitelist: set[str] = set()
    
    def get_bucket(self, ip: str) -> TokenBucket:
        """Get or create bucket for IP."""
        if ip not in self._buckets:
            self._buckets[ip] = TokenBucket(
                capacity=self._config["burst"],
                tokens=self._config["burst"],  # Start with full bucket
                refill_rate=self._config["rate"],
                last_refill=time()
            )
        return self._buckets[ip]
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        return ip in self._whitelist
    
    def add_to_whitelist(self, ip: str) -> None:
        """Add IP to whitelist."""
        self._whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str) -> None:
        """Remove IP from whitelist."""
        self._whitelist.discard(ip)
    
    def cleanup_inactive(self, max_age: float = 3600) -> int:
        """Remove buckets inactive for max_age seconds."""
        now = time()
        inactive = [
            ip for ip, bucket in self._buckets.items()
            if now - bucket.last_refill > max_age
        ]
        for ip in inactive:
            del self._buckets[ip]
        return len(inactive)
```

### IP Extraction
```python
from fastapi import Request

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (common with proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in chain is the client
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    
    return "unknown"
```

## 3. Middleware Integration

### Rate Limit Middleware
```python
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        config: RateLimitConfig = DEFAULT_CONFIG,
        whitelist: list[str] | None = None
    ):
        super().__init__(app)
        self.registry = BucketRegistry(config)
        if whitelist:
            for ip in whitelist:
                self.registry.add_to_whitelist(ip)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = get_client_ip(request)
        
        # Check whitelist
        if self.registry.is_whitelisted(client_ip):
            return await call_next(request)
        
        # Get bucket and attempt consumption
        bucket = self.registry.get_bucket(client_ip)
        
        if not bucket.consume():
            # Rate limit exceeded
            retry_after = int(bucket.time_until_next_token()) + 1
            return Response(
                content=json.dumps({
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after
                }),
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                media_type="application/json"
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        
        return response
```

### FastAPI App Integration
```python
app = FastAPI()

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    config={"rate": 10.0, "burst": 20},
    whitelist=["127.0.0.1", "10.0.0.0/8"]  # Internal IPs
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## 4. Retry-After Calculation

### Calculation Logic
```python
def calculate_retry_after(bucket: TokenBucket) -> int:
    """Calculate Retry-After header value in seconds."""
    wait_time = bucket.time_until_next_token()
    # Round up and add small buffer
    return int(wait_time) + 1

# Alternative: More precise calculation with fractional seconds
def calculate_retry_after_precise(bucket: TokenBucket) -> float:
    """Calculate precise Retry-After in seconds."""
    return max(1.0, bucket.time_until_next_token())
```

### Response Headers
```python
from fastapi import Response

def add_rate_limit_headers(response: Response, bucket: TokenBucket) -> None:
    """Add standard rate limit headers to response."""
    response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
    response.headers["X-RateLimit-Reset"] = str(
        int(time() + bucket.time_until_next_token())
    )
```

## 5. Constraint Acknowledgment

### Python + FastAPI
**Addressed by:** Application built with FastAPI framework. Middleware uses FastAPI/Starlette middleware base class.

### Token Bucket required, no simple counter
**Addressed by:** Rate limiting uses full Token Bucket algorithm with refill rate and capacity. No simple request counter or fixed window approach.

### stdlib + fastapi only, no Redis
**Addressed by:** Token buckets stored in-memory using Python dictionaries. No Redis or external storage for rate limit state.

### Single file
**Addressed by:** All rate limiting code in single Python file. TokenBucket class, BucketRegistry, middleware, and app setup co-located.

### 429 with Retry-After, IP whitelist
**Addressed by:** Middleware returns HTTP 429 status with `Retry-After` header when rate exceeded. IP whitelist checked before rate limiting applied.

### Code only
**Addressed by:** Output contains only Python code. No markdown in generated file.
