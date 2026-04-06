"""
MC-BE-02: JWT Auth Middleware
[L]Python [F]FastAPI [!D]NO_JWT_LIB [AUTH]MANUAL_JWT [D]STDLIB+FASTAPI [O]SINGLE_FILE [API]LOGIN_PROTECTED_REFRESH [OUT]CODE_ONLY
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Annotated


# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-access-key-do-not-share"
REFRESH_SECRET = "super-secret-refresh-key-do-not-share"
ACCESS_TOKEN_TTL = 15 * 60       # 15 minutes
REFRESH_TOKEN_TTL = 7 * 24 * 3600  # 7 days

# ─── In-memory user store (mock) ─────────────────────────────────────────────

USERS_DB: dict[str, dict[str, str]] = {
    "alice": {"id": "user-001", "username": "alice", "password": "password123"},
    "bob": {"id": "user-002", "username": "bob", "password": "secret456"},
}

# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class User:
    id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_TTL


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_TTL


class ProtectedResponse(BaseModel):
    message: str
    user_id: str
    username: str


# ─── Manual JWT Implementation ────────────────────────────────────────────────

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_token(payload: dict, secret: str, ttl: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    now = int(time.time())
    claims = {
        **payload,
        "iat": now,
        "exp": now + ttl,
        "jti": str(uuid.uuid4()),
    }

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(claims, separators=(",", ":")).encode())

    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_token(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    header_b64, payload_b64, signature_b64 = parts

    # Verify signature
    message = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    expected_sig_b64 = base64url_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise ValueError("Invalid signature")

    # Decode payload
    payload_json = base64url_decode(payload_b64)
    payload = json.loads(payload_json)

    # Check expiry
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")

    return payload


def create_access_token(user_id: str, username: str) -> str:
    return create_token(
        {"sub": user_id, "username": username},
        SECRET_KEY,
        ACCESS_TOKEN_TTL,
    )


def create_refresh_token(user_id: str, username: str) -> str:
    return create_token(
        {"sub": user_id, "username": username},
        REFRESH_SECRET,
        REFRESH_TOKEN_TTL,
    )


# ─── FastAPI Dependency ───────────────────────────────────────────────────────

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]

    try:
        payload = verify_token(token, SECRET_KEY)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return User(id=payload["sub"], username=payload["username"])


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Auth Middleware")


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = USERS_DB.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user["id"], user["username"])
    refresh_token = create_refresh_token(user["id"], user["username"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@app.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest) -> RefreshResponse:
    try:
        payload = verify_token(req.refresh_token, REFRESH_SECRET)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}")

    new_access_token = create_access_token(
        user_id=payload["sub"],
        username=payload["username"],
    )

    return RefreshResponse(access_token=new_access_token)


@app.get("/protected", response_model=ProtectedResponse)
async def protected_route(user: User = Depends(get_current_user)) -> ProtectedResponse:
    return ProtectedResponse(
        message=f"Hello, {user.username}! You are authenticated.",
        user_id=user.id,
        username=user.username,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
