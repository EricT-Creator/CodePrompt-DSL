"""JWT Authentication System with FastAPI — manual HMAC-SHA256 JWT."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel


# ── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2026"
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days


# ── User Store ───────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


users_db: dict[str, dict[str, str]] = {
    "admin": {
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "user_id": "u-001",
    },
    "alice": {
        "username": "alice",
        "password_hash": hash_password("alice456"),
        "user_id": "u-002",
    },
    "bob": {
        "username": "bob",
        "password_hash": hash_password("bob789"),
        "user_id": "u-003",
    },
}

# Revoked token JTIs
revoked_jtis: set[str] = set()


# ── Pydantic Models ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    username: str


# ── JWT Implementation ───────────────────────────────────────────────────────


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(
    sub: str,
    username: str,
    token_type: str = "access",
    expires_in: int = ACCESS_TOKEN_EXPIRE,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "username": username,
        "iat": now,
        "exp": now + expires_in,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    header_b64, payload_b64, signature_b64 = parts

    # Recompute signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    expected_sig_b64 = base64url_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise ValueError("Invalid token signature")

    # Decode payload
    payload_bytes = base64url_decode(payload_b64)
    payload: dict[str, Any] = json.loads(payload_bytes)

    # Check expiration
    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise ValueError("Token has expired")

    # Check revocation
    jti = payload.get("jti", "")
    if jti in revoked_jtis:
        raise ValueError("Token has been revoked")

    return payload


# ── Dependencies ─────────────────────────────────────────────────────────────


async def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    token = authorization[7:]

    try:
        payload = verify_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return payload


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = users_db.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    provided_hash = hash_password(request.password)
    if not hmac.compare_digest(provided_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_jwt(
        sub=user["user_id"],
        username=user["username"],
        token_type="access",
        expires_in=ACCESS_TOKEN_EXPIRE,
    )
    refresh_token = create_jwt(
        sub=user["user_id"],
        username=user["username"],
        token_type="refresh",
        expires_in=REFRESH_TOKEN_EXPIRE,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.get("/protected", response_model=UserResponse)
async def protected(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        user_id=current_user["sub"],
        username=current_user["username"],
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    try:
        payload = verify_jwt(request.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Revoke the old refresh token
    old_jti = payload.get("jti", "")
    if old_jti:
        revoked_jtis.add(old_jti)

    # Issue new tokens
    access_token = create_jwt(
        sub=payload["sub"],
        username=payload["username"],
        token_type="access",
        expires_in=ACCESS_TOKEN_EXPIRE,
    )
    refresh_token = create_jwt(
        sub=payload["sub"],
        username=payload["username"],
        token_type="refresh",
        expires_in=REFRESH_TOKEN_EXPIRE,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
