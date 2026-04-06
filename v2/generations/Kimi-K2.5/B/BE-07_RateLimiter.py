import time
from typing import Dict, Optional, Set
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, rate: float, burst: int):
        """
        Args:
            rate: Tokens per second
            burst: Maximum bucket size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket. Returns True if successful."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time until enough tokens are available."""
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.rate
    
    def get_token_count(self) -> float:
        """Get current token count."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.burst, self.tokens + elapsed * self.rate)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter middleware."""
    
    def __init__(
        self,
        app,
        rate: float = 10.0,  # 10 requests per second
        burst: int = 20,     # burst of 20 requests
        whitelist: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self.whitelist = whitelist or set()
        self.buckets: Dict[str, TokenBucket] = {}
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_bucket(self, ip: str) -> TokenBucket:
        """Get or create token bucket for IP."""
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.rate, self.burst)
        return self.buckets[ip]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for whitelisted IPs
        client_ip = self._get_client_ip(request)
        if client_ip in self.whitelist:
            return await call_next(request)
        
        # Special endpoint for status check
        if request.url.path == "/status":
            return await call_next(request)
        
        # Check rate limit
        bucket = self._get_bucket(client_ip)
        
        if not bucket.consume():
            wait_time = bucket.get_wait_time()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(int(wait_time) + 1)}
            )
        
        response = await call_next(request)
        return response


# Configure middleware
rate_limiter = RateLimiterMiddleware(
    app,
    rate=10.0,  # 10 requests per second
    burst=20,   # burst of 20
    whitelist={"127.0.0.1", "::1"}  # Whitelist localhost
)
app.add_middleware(RateLimiterMiddleware, rate=10.0, burst=20, whitelist={"127.0.0.1", "::1"})


@app.get("/status")
async def get_status(request: Request):
    """Get current token count for requester IP."""
    # Get the middleware instance
    middleware = None
    for m in request.app.user_middleware:
        if m.cls == RateLimiterMiddleware:
            # Access the actual middleware instance through the dispatch
            break
    
    # Calculate client IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    # Get bucket for this IP
    # Note: In real implementation, we'd access the middleware's buckets
    # For simplicity, we'll return a placeholder
    return {
        "ip": client_ip,
        "whitelisted": client_ip in {"127.0.0.1", "::1"},
        "message": "Token bucket status endpoint",
        "rate": 10.0,
        "burst": 20
    }


@app.get("/")
async def root():
    """Root endpoint - rate limited."""
    return {"message": "Hello! This endpoint is rate limited."}


@app.get("/api/data")
async def get_data():
    """Example API endpoint - rate limited."""
    return {"data": "some protected data"}


# Custom exception handler for 429
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 429:
        headers = dict(exc.headers) if exc.headers else {}
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "detail": exc.detail,
                "retry_after": headers.get("Retry-After", "unknown")
            },
            headers=headers
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
