"""JWT Authentication System with FastAPI — manual HMAC-SHA256 signing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel


# ── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2026"
ACCESS_TOKEN_EXPIRY = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRY = 7 * 24 * 60 * 60  # 7 days


# ── User Store ───────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


users_db: dict[str, dict[str, str]] = {
    "alice": {
        "username": "alice",
        "password_hash": hash_password("password123"),
        "user_id": "u-001",
    },
    "bob": {
        "username": "bob",
        "password_hash": hash_password("secret456"),
        "user_id": "u-002",
    },
    "charlie": {
        "username": "charlie",
        "password_hash": hash_password("charlie789"),
        "user_id": "u-003",
    },
}

revoked_jtis: set[str] = set()


# ── JWT Implementation ───────────────────────────────────────────────────────


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(
    sub: str,
    username: str,
    token_type: str = "access",
    expiry_seconds: int = ACCESS_TOKEN_EXPIRY,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())

    payload: dict[str, Any] = {
        "sub": sub,
        "username": username,
        "iat": now,
        "exp": now + expiry_seconds,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_token(token: str) -> dict[str, Any]:
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

    if not hmac.compare_digest(expected_sig_b64, signature_b64):
        raise ValueError("Invalid token signature")

    # Decode payload
    payload_bytes = base64url_decode(payload_b64)
    payload: dict[str, Any] = json.loads(payload_bytes)

    # Check expiry
    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise ValueError("Token has expired")

    # Check revocation
    jti = payload.get("jti")
    if jti and jti in revoked_jtis:
        raise ValueError("Token has been revoked")

    return payload


# ── Request / Response Models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRY


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRY


class UserResponse(BaseModel):
    user_id: str
    username: str
    message: str = "Access granted"


# ── Dependencies ─────────────────────────────────────────────────────────────


async def get_current_user(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid authorization scheme. Use Bearer."
        )

    token = auth_header[7:]

    try:
        payload = verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return payload


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    user = users_db.get(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_hash = user["password_hash"]
    provided_hash = hash_password(body.password)

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_token(
        sub=user["user_id"],
        username=user["username"],
        token_type="access",
        expiry_seconds=ACCESS_TOKEN_EXPIRY,
    )
    refresh_token = create_token(
        sub=user["user_id"],
        username=user["username"],
        token_type="refresh",
        expiry_seconds=REFRESH_TOKEN_EXPIRY,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@app.get("/protected", response_model=UserResponse)
async def protected(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        user_id=current_user["sub"],
        username=current_user["username"],
    )


@app.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest) -> RefreshResponse:
    try:
        payload = verify_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Revoke old refresh token
    old_jti = payload.get("jti")
    if old_jti:
        revoked_jtis.add(old_jti)

    access_token = create_token(
        sub=payload["sub"],
        username=payload["username"],
        token_type="access",
        expiry_seconds=ACCESS_TOKEN_EXPIRY,
    )

    return RefreshResponse(access_token=access_token)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
