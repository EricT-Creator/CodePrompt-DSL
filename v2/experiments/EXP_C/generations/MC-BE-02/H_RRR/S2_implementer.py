"""JWT Auth Middleware — MC-BE-02 (H × RRR)"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Configuration ──
SECRET_KEY: str = "super-secret-key-for-jwt-signing-do-not-share"
ACCESS_TOKEN_EXPIRY: int = 3600        # 1 hour
REFRESH_TOKEN_EXPIRY: int = 604800     # 7 days

# ── Mock User Store ──
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

USERS: dict[str, dict[str, str]] = {
    "john": {"password_hash": hash_password("password123"), "user_id": "u001"},
    "jane": {"password_hash": hash_password("secret456"), "user_id": "u002"},
}

# ── Base64url Helpers ──
def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

# ── JWT Functions ──
def create_jwt(payload: dict[str, Any]) -> str:
    header: dict[str, str] = {"alg": "HS256", "typ": "JWT"}

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_jwt(token: str, expected_type: str = "access") -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    header_b64, payload_b64, sig_b64 = parts

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    actual_sig = base64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    # Decode payload
    try:
        payload = json.loads(base64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Check expiry
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise HTTPException(status_code=401, detail="Token expired")

    # Check token type
    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise HTTPException(
            status_code=401,
            detail=f"Expected {expected_type} token, got {token_type}",
        )

    return payload

def create_access_token(user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRY,
        "type": "access",
    }
    return create_jwt(payload)

def create_refresh_token(user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRY,
        "type": "refresh",
    }
    return create_jwt(payload)

# ── Token Extraction ──
def extract_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    return parts[1]

# ── Dependencies ──
async def require_auth(request: Request) -> dict[str, Any]:
    token = extract_token(request)
    payload = verify_jwt(token, expected_type="access")
    return payload

async def require_refresh_token(request: Request) -> dict[str, Any]:
    token = extract_token(request)
    payload = verify_jwt(token, expected_type="refresh")
    return payload

# ── Pydantic Models ──
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRY

class ProtectedResponse(BaseModel):
    message: str
    user_id: str
    username: str

class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRY

# ── Application ──
app = FastAPI(title="JWT Auth API")

# ── Routes ──
@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = USERS.get(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_hash = hash_password(req.password)
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = user["user_id"]
    access_token = create_access_token(user_id, req.username)
    refresh_token = create_refresh_token(user_id, req.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(claims: dict[str, Any] = Depends(require_auth)) -> ProtectedResponse:
    return ProtectedResponse(
        message="You have access to this protected resource",
        user_id=claims["sub"],
        username=claims["username"],
    )

@app.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(claims: dict[str, Any] = Depends(require_refresh_token)) -> RefreshResponse:
    user_id = claims["sub"]
    username = claims["username"]

    new_access = create_access_token(user_id, username)
    new_refresh = create_refresh_token(user_id, username)

    return RefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )
