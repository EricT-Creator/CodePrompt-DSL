from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time
from typing import Dict, Optional
from dataclasses import dataclass

app = FastAPI()

@dataclass
class TokenBucket:
    tokens: float
    last_update: float

class RateLimiter:
    def __init__(self, rate: float, burst: float):
        self.rate = rate
        self.burst = burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.whitelist: set = set()
    
    def add_to_whitelist(self, ip: str):
        self.whitelist.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        self.whitelist.discard(ip)
    
    def get_bucket(self, key: str) -> TokenBucket:
        now = time.time()
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(tokens=self.burst, last_update=now)
        return self.buckets[key]
    
    def update_bucket(self, bucket: TokenBucket):
        now = time.time()
        elapsed = now - bucket.last_update
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
        bucket.last_update = now
    
    def is_allowed(self, key: str) -> tuple[bool, float]:
        bucket = self.get_bucket(key)
        self.update_bucket(bucket)
        
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True, 0
        
        retry_after = (1 - bucket.tokens) / self.rate
        return False, retry_after
    
    def get_token_count(self, key: str) -> float:
        bucket = self.get_bucket(key)
        self.update_bucket(bucket)
        return bucket.tokens

limiter = RateLimiter(rate=1.0, burst=5)
limiter.add_to_whitelist("127.0.0.1")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    
    if client_ip in limiter.whitelist:
        response = await call_next(request)
        return response
    
    allowed, retry_after = limiter.is_allowed(client_ip)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(int(retry_after) + 1)}
        )
    
    response = await call_next(request)
    return response

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/status")
def get_status(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    tokens = limiter.get_token_count(client_ip)
    is_whitelisted = client_ip in limiter.whitelist
    
    return {
        "ip": client_ip,
        "tokens_remaining": round(tokens, 2),
        "whitelisted": is_whitelisted
    }

@app.post("/admin/whitelist/{ip}")
def add_whitelist(ip: str):
    limiter.add_to_whitelist(ip)
    return {"message": f"IP {ip} added to whitelist"}

@app.delete("/admin/whitelist/{ip}")
def remove_whitelist(ip: str):
    limiter.remove_from_whitelist(ip)
    return {"message": f"IP {ip} removed from whitelist"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
