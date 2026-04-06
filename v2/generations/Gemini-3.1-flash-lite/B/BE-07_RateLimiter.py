import time
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate=5, burst=10):
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self.buckets = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        if client_ip == "127.0.0.1": return await call_next(request)
        
        now = time.time()
        if client_ip not in self.buckets:
            self.buckets[client_ip] = {"tokens": self.burst, "last": now}
        
        b = self.buckets[client_ip]
        b["tokens"] = min(self.burst, b["tokens"] + (now - b["last"]) * self.rate)
        b["last"] = now
        
        if b["tokens"] < 1:
            return Response("Too Many Requests", status_code=429, headers={"Retry-After": "1"})
        
        b["tokens"] -= 1
        return await call_next(request)

app.add_middleware(RateLimiterMiddleware)

@app.get("/status")
def status(request: Request):
    ip = request.client.host
    return {"ip": ip, "tokens": app.user_middleware[0].cls.buckets.get(ip, {}).get("tokens", 0)}
