import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ==================== Configuration ====================

RATE_LIMIT_RATE = 10.0  # tokens per second
RATE_LIMIT_BURST = 20   # maximum tokens in bucket
WHITELIST_IPS = {"127.0.0.1", "10.0.0.1", "192.168.1.1"}
CLEANUP_THRESHOLD_SECONDS = 300  # 5 minutes


# ==================== Data Models ====================

class RateLimitStatus(BaseModel):
    ip: str
    tokens: float
    burst: int
    rate: float
    last_refill: float
    is_whitelisted: bool


class RateLimitConfig(BaseModel):
    rate: float
    burst: int
    whitelist_count: int


# ==================== Token Bucket Implementation ====================

@dataclass
class TokenBucket:
    tokens: float = RATE_LIMIT_BURST
    last_refill: float = field(default_factory=time.time)
    rate: float = RATE_LIMIT_RATE
    burst: int = RATE_LIMIT_BURST
    
    def refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            new_tokens = elapsed * self.rate
            self.tokens = min(self.burst, self.tokens + new_tokens)
            self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> Tuple[bool, float]:
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            # Calculate retry-after time
            deficit = tokens - self.tokens
            retry_after = math.ceil(deficit / self.rate)
            return False, retry_after


class RateLimiter:
    def __init__(self, rate: float = RATE_LIMIT_RATE, burst: int = RATE_LIMIT_BURST):
        self.rate = rate
        self.burst = burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.whitelist = WHITELIST_IPS.copy()
        self.cleanup_threshold = CLEANUP_THRESHOLD_SECONDS
    
    def get_or_create_bucket(self, ip: str) -> TokenBucket:
        # Clean up old buckets first
        self._cleanup_stale_buckets()
        
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(
                tokens=self.burst,
                last_refill=time.time(),
                rate=self.rate,
                burst=self.burst
            )
        
        return self.buckets[ip]
    
    def is_whitelisted(self, ip: str) -> bool:
        return ip in self.whitelist
    
    def consume(self, ip: str, tokens: float = 1.0) -> Tuple[bool, float]:
        if self.is_whitelisted(ip):
            return True, 0.0
        
        bucket = self.get_or_create_bucket(ip)
        return bucket.consume(tokens)
    
    def get_status(self, ip: str) -> Optional[RateLimitStatus]:
        if ip not in self.buckets and not self.is_whitelisted(ip):
            return None
        
        is_whitelisted = self.is_whitelisted(ip)
        
        if is_whitelisted:
            return RateLimitStatus(
                ip=ip,
                tokens=self.burst,
                burst=self.burst,
                rate=self.rate,
                last_refill=time.time(),
                is_whitelisted=True
            )
        
        bucket = self.buckets[ip]
        # Ensure bucket is up to date
        bucket.refill()
        
        return RateLimitStatus(
            ip=ip,
            tokens=bucket.tokens,
            burst=bucket.burst,
            rate=bucket.rate,
            last_refill=bucket.last_refill,
            is_whitelisted=False
        )
    
    def _cleanup_stale_buckets(self):
        now = time.time()
        stale_ips = []
        
        for ip, bucket in self.buckets.items():
            if now - bucket.last_refill > self.cleanup_threshold:
                stale_ips.append(ip)
        
        for ip in stale_ips:
            del self.buckets[ip]
    
    def add_to_whitelist(self, ip: str):
        self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        if ip in self.whitelist:
            self.whitelist.remove(ip)


# ==================== FastAPI Middleware ====================

app = FastAPI(title="Token Bucket Rate Limiter")
rate_limiter = RateLimiter()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Extract client IP
    ip = request.client.host if request.client else "0.0.0.0"
    
    # Check whitelist
    if rate_limiter.is_whitelisted(ip):
        return await call_next(request)
    
    # Apply rate limiting
    allowed, retry_after = rate_limiter.consume(ip)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    
    # Get current bucket status for headers
    status = rate_limiter.get_status(ip)
    if status:
        response.headers["X-RateLimit-Limit"] = str(status.burst)
        response.headers["X-RateLimit-Remaining"] = str(int(max(0, status.tokens)))
        response.headers["X-RateLimit-Reset"] = str(int(status.last_refill + (status.burst - status.tokens) / status.rate))
    
    return response


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {"message": "Hello, this endpoint is rate limited!"}


@app.get("/status")
async def get_status(request: Request):
    ip = request.client.host if request.client else "0.0.0.0"
    status = rate_limiter.get_status(ip)
    
    if status is None:
        return {"message": "No bucket created for this IP yet"}
    
    return {
        "ip": status.ip,
        "tokens": status.tokens,
        "burst": status.burst,
        "rate": status.rate,
        "is_whitelisted": status.is_whitelisted,
        "remaining_percentage": f"{(status.tokens / status.burst) * 100:.1f}%",
        "last_refill_seconds_ago": time.time() - status.last_refill
    }


@app.get("/config")
async def get_config():
    return RateLimitConfig(
        rate=rate_limiter.rate,
        burst=rate_limiter.burst,
        whitelist_count=len(rate_limiter.whitelist)
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_buckets": len(rate_limiter.buckets),
        "whitelisted_ips": len(rate_limiter.whitelist)
    }


# ==================== Demo Endpoints ====================

class WhitelistRequest(BaseModel):
    ip: str


@app.post("/demo/whitelist/add")
async def add_to_whitelist(request: WhitelistRequest):
    rate_limiter.add_to_whitelist(request.ip)
    return {"message": f"IP {request.ip} added to whitelist"}


@app.post("/demo/whitelist/remove")
async def remove_from_whitelist(request: WhitelistRequest):
    rate_limiter.remove_from_whitelist(request.ip)
    return {"message": f"IP {request.ip} removed from whitelist"}


@app.get("/demo/whitelist")
async def list_whitelist():
    return {
        "whitelist": list(rate_limiter.whitelist),
        "count": len(rate_limiter.whitelist)
    }


@app.get("/demo/buckets")
async def list_buckets():
    buckets_info = []
    
    for ip, bucket in rate_limiter.buckets.items():
        # Ensure bucket is up to date
        bucket.refill()
        
        buckets_info.append({
            "ip": ip,
            "tokens": bucket.tokens,
            "last_refill_seconds_ago": time.time() - bucket.last_refill,
            "is_whitelisted": ip in rate_limiter.whitelist
        })
    
    return {
        "buckets": buckets_info,
        "count": len(buckets_info)
    }


@app.get("/demo/heavy")
async def heavy_endpoint():
    # Simulate some work
    time.sleep(0.1)
    return {"message": "Heavy endpoint completed", "timestamp": time.time()}


# ==================== Main Execution ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)