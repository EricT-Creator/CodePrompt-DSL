"""
令牌桶限流中间件 - Token Bucket Algorithm
不使用Redis/限流库，仅标准库实现
"""

import time
import threading
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Token Bucket Rate Limiter")

# ===== 令牌桶实现 =====

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate          # tokens per second
        self.burst = burst        # max tokens
        self.tokens = float(burst)
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_retry_after(self) -> float:
        with self.lock:
            if self.tokens >= 1:
                return 0
            deficit = 1 - self.tokens
            return deficit / self.rate

    def get_token_count(self) -> float:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.burst, self.tokens + elapsed * self.rate)

# ===== 限流器配置 =====

DEFAULT_RATE = 5.0       # 5 tokens/second
DEFAULT_BURST = 10       # max 10 tokens

WHITELIST_IPS = {"127.0.0.1", "::1", "localhost"}

buckets: dict[str, TokenBucket] = {}
buckets_lock = threading.Lock()

def get_bucket(ip: str) -> TokenBucket:
    with buckets_lock:
        if ip not in buckets:
            buckets[ip] = TokenBucket(DEFAULT_RATE, DEFAULT_BURST)
        return buckets[ip]

# ===== 中间件 =====

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"

    if client_ip in WHITELIST_IPS:
        return await call_next(request)

    if request.url.path in ("/status", "/docs", "/openapi.json"):
        return await call_next(request)

    bucket = get_bucket(client_ip)

    if not bucket.consume():
        retry_after = bucket.get_retry_after()
        response = JSONResponse(
            status_code=429,
            content={
                "detail": "请求过于频繁，请稍后重试",
                "retry_after": round(retry_after, 2),
            },
        )
        response.headers["Retry-After"] = str(int(retry_after) + 1)
        return response

    response: Response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(DEFAULT_BURST)
    response.headers["X-RateLimit-Remaining"] = str(int(bucket.get_token_count()))
    return response

# ===== 路由 =====

@app.get("/")
async def root():
    return {"message": "令牌桶限流中间件运行中", "rate": DEFAULT_RATE, "burst": DEFAULT_BURST}

@app.get("/status")
async def status(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    bucket = get_bucket(client_ip)
    return {
        "ip": client_ip,
        "tokens_remaining": round(bucket.get_token_count(), 2),
        "rate": DEFAULT_RATE,
        "burst": DEFAULT_BURST,
    }

@app.get("/slow")
async def slow_endpoint():
    time.sleep(0.1)
    return {"message": "这是一个慢接口，会消耗令牌"}

@app.post("/data")
async def post_data():
    return {"message": "POST请求成功"}

# ===== 全局异常处理 =====

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
