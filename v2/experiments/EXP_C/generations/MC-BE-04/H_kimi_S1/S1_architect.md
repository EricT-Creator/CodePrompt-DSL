# MC-BE-04: Rate Limiter Middleware — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. Token Bucket Algorithm Details

### 1.1 Algorithm Overview

The Token Bucket algorithm controls request rate by maintaining a "bucket" of tokens:
- Each token represents permission to make one request
- Tokens are added to the bucket at a fixed rate
- Requests consume tokens from the bucket
- If bucket is empty, request is rate-limited

### 1.2 Bucket State

```python
from dataclasses import dataclass
from time import time

@dataclass
class TokenBucket:
    capacity: float      # Maximum tokens (burst size)
    tokens: float        # Current token count
    rate: float          # Tokens added per second
    last_update: float   # Last timestamp tokens were added
```

### 1.3 Token Replenishment

```python
def replenish(bucket: TokenBucket) -> TokenBucket:
    """Add tokens based on elapsed time"""
    now = time()
    elapsed = now - bucket.last_update
    
    # Add tokens proportional to elapsed time
    bucket.tokens = min(
        bucket.capacity,
        bucket.tokens + (elapsed * bucket.rate)
    )
    bucket.last_update = now
    
    return bucket
```

### 1.4 Request Consumption

```python
def consume(bucket: TokenBucket) -> tuple[bool, TokenBucket]:
    """Try to consume one token, return success/failure"""
    bucket = replenish(bucket)
    
    if bucket.tokens >= 1:
        bucket.tokens -= 1
        return True, bucket
    else:
        return False, bucket
```

---

## 2. Per-IP Bucket Management

### 2.1 In-Memory Store

```python
# IP address -> TokenBucket
buckets: dict[str, TokenBucket] = {}

# Configuration
DEFAULT_RATE = 10      # tokens per second
DEFAULT_CAPACITY = 20  # burst size
```

### 2.2 Lazy Bucket Creation

```python
def get_bucket(ip: str) -> TokenBucket:
    """Get or create bucket for IP"""
    if ip not in buckets:
        buckets[ip] = TokenBucket(
            capacity=DEFAULT_CAPACITY,
            tokens=DEFAULT_CAPACITY,  # Start full
            rate=DEFAULT_RATE,
            last_update=time()
        )
    return buckets[ip]
```

### 2.3 Cleanup (Optional)

```python
def cleanup_buckets(max_age: float = 3600):
    """Remove buckets inactive for max_age seconds"""
    now = time()
    stale_ips = [
        ip for ip, bucket in buckets.items()
        if now - bucket.last_update > max_age
    ]
    for ip in stale_ips:
        del buckets[ip]
```

---

## 3. Middleware Integration

### 3.1 FastAPI Middleware

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelist: list[str] = None):
        super().__init__(app)
        self.whitelist = set(whitelist or [])
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # Check whitelist
        if client_ip in self.whitelist:
            return await call_next(request)
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        
        if not allowed:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)
```

### 3.2 Alternative: Dependency Injection

```python
from fastapi import Depends, HTTPException, Header

async def rate_limit_check(request: Request):
    client_ip = request.client.host
    allowed, retry_after = check_rate_limit(client_ip)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )

# Usage
@app.get("/api/data", dependencies=[Depends(rate_limit_check)])
async def get_data():
    return {"data": "..."}
```

---

## 4. Retry-After Calculation

### 4.1 Formula

```python
def calculate_retry_after(bucket: TokenBucket) -> int:
    """Calculate seconds until next token available"""
    if bucket.tokens >= 1:
        return 0
    
    # Time needed to generate 1 token
    tokens_needed = 1 - bucket.tokens
    seconds_needed = tokens_needed / bucket.rate
    
    return int(seconds_needed) + 1  # Round up
```

### 4.2 Response Headers

```python
headers = {
    "Retry-After": str(retry_after),  # Seconds
    "X-RateLimit-Limit": str(bucket.capacity),
    "X-RateLimit-Remaining": str(int(bucket.tokens))
}
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]Python` | Python 3.10+ implementation |
| `[F]FastAPI` | FastAPI middleware/dependency |
| `[ALGO]TOKEN_BUCKET` | Token bucket rate limiting algorithm |
| `[!A]NO_COUNTER` | No simple counter; proper token bucket |
| `[D]STDLIB+FASTAPI` | Only standard library + FastAPI |
| `[!D]NO_REDIS` | In-memory bucket storage |
| `[O]SINGLE_FILE` | All code in single file |
| `[RESP]429_RETRY_AFTER` | HTTP 429 with Retry-After header |
| `[WL]IP` | IP-based whitelist support |
| `[OUT]CODE_ONLY` | Output will be code only |

---

## 6. Configuration

```python
# Rate limiting config
RATE_LIMIT_RATE = 10        # requests per second
RATE_LIMIT_BURST = 20       # max burst
RATE_LIMIT_WHITELIST = [    # IPs that bypass rate limiting
    "127.0.0.1",
    "::1"
]
```

---

## 7. File Structure

```
MC-BE-04/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── main.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
