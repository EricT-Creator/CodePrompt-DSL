import time
from fastapi import FastAPI, Request, HTTPException, Response

app = FastAPI()

tokens = {}
LIMIT = 5
RATE = 1

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    if client_ip not in tokens:
        tokens[client_ip] = {"last": now, "count": LIMIT}
    
    data = tokens[client_ip]
    data["count"] = min(LIMIT, data["count"] + (now - data["last"]) * RATE)
    data["last"] = now
    
    if data["count"] < 1:
        return Response("Too Many Requests", status_code=429, headers={"Retry-After": "1"})
    
    data["count"] -= 1
    return await call_next(request)

@app.get("/status")
def status(request: Request):
    return {"tokens": tokens.get(request.client.host, {}).get("count", LIMIT)}
