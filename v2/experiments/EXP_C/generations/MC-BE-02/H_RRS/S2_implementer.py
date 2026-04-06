"""JWT Auth Middleware — MC-BE-02 (H × RRS)"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

# ─── Config ───
SECRET_KEY = "super-secret-key-for-demo-purposes-only"
ACCESS_TOKEN_TTL = 3600       # 1 hour
REFRESH_TOKEN_TTL = 604800    # 7 days

# ─── Mock user store ───
def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


USERS: dict[str, dict[str, str]] = {
    "john": {"password_hash": _hash_password("password123"), "user_id": "u001"},
    "jane": {"password_hash": _hash_password("securepass"), "user_id": "u002"},
}


# ─── Base64url helpers ───
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ─── JWT creation ───
def _create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def create_access_token(user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "type": "access",
    }
    return _create_jwt(payload)


def create_refresh_token(user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL,
        "type": "refresh",
    }
    return _create_jwt(payload)


# ─── JWT verification ───
def verify_jwt(token: str, expected_type: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    header_b64, payload_b64, sig_b64 = parts

    # Recompute signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    # Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Check expiry
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise HTTPException(status_code=401, detail="Token expired")

    # Check token type
    token_type = payload.get("type", "")
    if token_type != expected_type:
        raise HTTPException(status_code=401, detail=f"Expected {expected_type} token, got {token_type}")

    return payload


# ─── Token extraction ───
def extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    return parts[1]


# ─── Dependencies ───
async def require_auth(request: Request) -> dict[str, Any]:
    token = extract_token(request)
    return verify_jwt(token, expected_type="access")


async def require_refresh_token(request: Request) -> dict[str, Any]:
    token = extract_token(request)
    return verify_jwt(token, expected_type="refresh")


# ─── Pydantic models ───
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ProtectedResponse(BaseModel):
    message: str
    user_id: str
    username: str


# ─── FastAPI App ───
app = FastAPI(title="JWT Auth Middleware")


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = USERS.get(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    pw_hash = _hash_password(req.password)
    if pw_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user["user_id"], req.username)
    refresh = create_refresh_token(user["user_id"], req.username)
    return TokenResponse(access_token=access, refresh_token=refresh)


@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(claims: dict[str, Any] = Depends(require_auth)) -> ProtectedResponse:
    return ProtectedResponse(
        message="You have access to the protected resource.",
        user_id=claims["sub"],
        username=claims["username"],
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(claims: dict[str, Any] = Depends(require_refresh_token)) -> TokenResponse:
    access = create_access_token(claims["sub"], claims["username"])
    refresh = create_refresh_token(claims["sub"], claims["username"])
    return TokenResponse(access_token=access, refresh_token=refresh)
