import time
import hmac
import hashlib
import base64
import json
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

SECRET_KEY = b"supersecretkey"

class User(BaseModel):
    username: str
    password: str

def create_jwt(payload: dict):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload["exp"] = time.time() + 1800
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY, f"{header}.{p}".encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{p}.{sig}"

def verify_jwt(token: str):
    parts = token.split(".")
    if len(parts) != 3: raise HTTPException(401)
    header, p, sig = parts
    signature = hmac.new(SECRET_KEY, f"{header}.{p}".encode(), hashlib.sha256).digest()
    if sig != base64.urlsafe_b64encode(signature).decode().rstrip("="): raise HTTPException(401)
    payload = json.loads(base64.urlsafe_b64decode(p + "==").decode())
    if payload["exp"] < time.time(): raise HTTPException(401)
    return payload

@app.post("/login")
def login(user: User):
    if user.username == "admin" and user.password == "secret":
        return {"token": create_jwt({"sub": "admin"})}
    raise HTTPException(401)

@app.get("/protected")
def protected(authorization: str = Header(...)):
    return verify_jwt(authorization.replace("Bearer ", ""))

@app.post("/refresh")
def refresh(authorization: str = Header(...)):
    payload = verify_jwt(authorization.replace("Bearer ", ""))
    return {"token": create_jwt({"sub": payload["sub"]})}
