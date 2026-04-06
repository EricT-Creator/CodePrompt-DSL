import time
from typing import Dict, Optional, Tuple
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Token Bucket Rate Limiter")

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        
        wait_time = (tokens - self.tokens) / self.rate
        return False, wait_time
    
    def get_token_count(self) -> float:
        now = time.time()
        elapsed = now - self.last_update
        return min(self.burst, self.tokens + elapsed * self.rate)

class RateLimiter:
    def __init__(self, default_rate: float = 10.0, default_burst: int = 20):
        self.buckets: Dict[str, TokenBucket] = {}
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.whitelist: set = set()
    
    def add_to_whitelist(self, ip: str):
        self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        self.whitelist.discard(ip)
    
    def is_whitelisted(self, ip: str) -> bool:
        return ip in self.whitelist
    
    def get_bucket(self, ip: str) -> TokenBucket:
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.default_rate, self.default_burst)
        return self.buckets[ip]
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, float]:
        if self.is_whitelisted(ip):
            return True, 0.0
        
        bucket = self.get_bucket(ip)
        return bucket.consume(1)
    
    def get_status(self, ip: str) -> Dict:
        if self.is_whitelisted(ip):
            return {
                "ip": ip,
                "whitelisted": True,
                "tokens": None,
                "rate": None,
                "burst": None
            }
        
        bucket = self.get_bucket(ip)
        return {
            "ip": ip,
            "whitelisted": False,
            "tokens": round(bucket.get_token_count(), 2),
            "rate": bucket.rate,
            "burst": bucket.burst
        }

limiter = RateLimiter(default_rate=10.0, default_burst=20)

class StatusResponse(BaseModel):
    ip: str
    whitelisted: bool
    tokens: Optional[float]
    rate: Optional[float]
    burst: Optional[int]

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/status", "/"]:
        response = await call_next(request)
        return response
    
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.check_rate_limit(client_ip)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": round(retry_after, 2)
            },
            headers={"Retry-After": str(int(retry_after) + 1)}
        )
    
    response = await call_next(request)
    return response

@app.get("/")
async def root():
    return {
        "message": "Token Bucket Rate Limiter",
        "endpoints": ["/status", "/api/data", "/admin/whitelist"],
        "default_rate": "10 requests/second",
        "default_burst": 20
    }

@app.get("/status", response_model=StatusResponse)
async def get_status(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    return limiter.get_status(client_ip)

@app.get("/api/data")
async def get_data():
    return {
        "message": "This endpoint is rate limited",
        "data": ["item1", "item2", "item3"]
    }

@app.post("/admin/whitelist")
async def add_to_whitelist(ip: str, action: str = "add"):
    if action == "add":
        limiter.add_to_whitelist(ip)
        return {"message": f"IP {ip} added to whitelist"}
    elif action == "remove":
        limiter.remove_from_whitelist(ip)
        return {"message": f"IP {ip} removed from whitelist"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/admin/whitelist")
async def get_whitelist():
    return {"whitelist": list(limiter.whitelist)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
