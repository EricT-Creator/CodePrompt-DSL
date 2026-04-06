from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time

app = FastAPI()
RATE_LIMIT = 5
BURST = 10
tokens = {}
last_refill = {}

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host
    if client_ip in ["127.0.0.1"]: return await call_next(request)
    
    now = time.time()
    if client_ip not in tokens:
        tokens[client_ip] = BURST
        last_refill[client_ip] = now
    
    tokens[client_ip] = min(BURST, tokens[client_ip] + (now - last_refill[client_ip]) * RATE_LIMIT)
    last_refill[client_ip] = now
    
    if tokens[client_ip] < 1:
        return JSONResponse(status_code=429, content={"error": "Too Many Requests"}, headers={"Retry-After": "1"})
        
    tokens[client_ip] -= 1
    return await call_next(request)

@app.get("/status")
def get_status(request: Request):
    return {"tokens": tokens.get(request.client.host, BURST)}
