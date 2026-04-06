import json
import base64
import hmac
import hashlib
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = "your-secret-key-here"

users = {
    "admin": "password123",
    "user1": "pass456"
}

used_refresh_tokens: set[str] = set()

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class ProtectedResponse(BaseModel):
    user: str
    message: str

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)

def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    return f"{signing_input}.{signature_b64}"

def verify_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None
        payload_json = base64url_decode(payload_b64)
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def create_tokens(username: str) -> tuple[str, str]:
    access_payload = {
        "sub": username,
        "iat": time.time(),
        "exp": time.time() + 900,
        "type": "access"
    }
    refresh_payload = {
        "sub": username,
        "iat": time.time(),
        "exp": time.time() + 604800,
        "type": "refresh",
        "jti": str(time.time()) + username
    }
    return create_jwt(access_payload), create_jwt(refresh_payload)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload["sub"]

@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    if request.username not in users or users[request.username] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token, refresh_token = create_tokens(request.username)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@app.get("/protected", response_model=ProtectedResponse)
async def protected(user: str = Depends(get_current_user)):
    return ProtectedResponse(user=user, message="Access granted")

@app.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    payload = verify_jwt(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    if request.refresh_token in used_refresh_tokens:
        raise HTTPException(status_code=401, detail="Token already used")
    used_refresh_tokens.add(request.refresh_token)
    username = payload["sub"]
    access_token, refresh_token = create_tokens(username)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
