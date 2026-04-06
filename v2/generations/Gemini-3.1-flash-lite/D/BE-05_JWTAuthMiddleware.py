import time
import hmac
import hashlib
import base64
import json
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

SECRET = "supersecret"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')

def sign(header: str, payload: str) -> str:
    msg = f"{header}.{payload}".encode('utf-8')
    sig = hmac.new(SECRET.encode('utf-8'), msg, hashlib.sha256).digest()
    return base64url_encode(sig)

@app.post("/login")
def login():
    header = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = base64url_encode(json.dumps({"sub": "user", "exp": time.time() + 1800}).encode())
    token = f"{header}.{payload}.{sign(header, payload)}"
    return {"token": token}

@app.get("/protected")
def protected(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "): raise HTTPException(401)
    token = auth[7:]
    parts = token.split('.')
    if len(parts) != 3 or sign(parts[0], parts[1]) != parts[2]: raise HTTPException(401)
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    if payload["exp"] < time.time(): raise HTTPException(401)
    return {"message": "Success"}
