from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
import hmac
import hashlib
import base64
import json
import time

app = FastAPI()
SECRET = b"supersecret"

class User(BaseModel):
    username: str
    password: str

def create_jwt(payload):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode()
    payload['exp'] = time.time() + 1800
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = base64.urlsafe_b64encode(hmac.new(SECRET, (header + "." + p).encode(), hashlib.sha256).digest()).decode()
    return f"{header}.{p}.{sig}"

@app.post("/login")
def login(user: User):
    return {"token": create_jwt({"user": user.username})}

@app.get("/protected")
def protected(authorization: str = Header(...)):
    try:
        parts = authorization.split(".")
        sig = base64.urlsafe_b64encode(hmac.new(SECRET, (parts[0] + "." + parts[1]).encode(), hashlib.sha256).digest()).decode()
        if sig != parts[2]: raise Exception()
        payload = json.loads(base64.urlsafe_b64decode(parts[1]).decode())
        if payload['exp'] < time.time(): raise Exception()
        return {"user": payload['user']}
    except:
        raise HTTPException(status_code=401)
