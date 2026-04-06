from fastapi import FastAPI, Request, Response
import time

app = FastAPI()

limiters = {}

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    ip = request.client.host
    if ip == "127.0.0.1": return await call_next(request)
    
    now = time.time()
    if ip not in limiters: limiters[ip] = {"tokens": 10, "last": now}
    
    tokens = min(10, limiters[ip]["tokens"] + (now - limiters[ip]["last"]) * 1)
    
    if tokens < 1:
        return Response(status_code=429, headers={"Retry-After": "1"})
        
    limiters[ip] = {"tokens": tokens - 1, "last": now}
    return await call_next(request)

@app.get("/status")
async def status(request: Request):
    return {"tokens": limiters.get(request.client.host, {"tokens": 10})["tokens"]}
