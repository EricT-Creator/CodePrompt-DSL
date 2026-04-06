import fastapi
from fastapi import FastAPI, Request, HTTPException
import time
import hmac
import hashlib
import base64
import json

app = FastAPI()

SECRET_KEY = b"mysecretkey"

def create_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode()
    payload["exp"] = time.time() + 1800
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY, f"{header}.{p}".encode(), hashlib.sha256).digest()
    return f"{header}.{p}.{base64.urlsafe_b64encode(sig).decode()}"

@app.post("/login")
async def login():
    return {"token": create_jwt({"user": "admin"})}

@app.get("/protected")
async def protected(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)
    token = auth.split(" ")[1]
    try:
        header, p, sig = token.split(".")
        if hmac.new(SECRET_KEY, f"{header}.{p}".encode(), hashlib.sha256).digest() != base64.urlsafe_b64decode(sig):
            raise HTTPException(status_code=401)
    except:
        raise HTTPException(status_code=401)
    return {"status": "ok"}
