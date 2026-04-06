"""JWT Authentication System — FastAPI implementation with manual HMAC-SHA256 JWT."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel


# ─── Configuration ────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2026"
ACCESS_TOKEN_EXPIRY = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRY = 7 * 24 * 3600  # 7 days

# ─── In-Memory User Store ─────────────────────────────────────


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


users_db: dict[str, dict[str, str]] = {
    "alice": {
        "username": "alice",
        "password_hash": hash_password("alice123"),
        "user_id": "u-001",
    },
    "bob": {
        "username": "bob",
        "password_hash": hash_password("bob456"),
        "user_id": "u-002",
    },
    "charlie": {
        "username": "charlie",
        "password_hash": hash_password("charlie789"),
        "user_id": "u-003",
    },
}

# Revoked token JTIs
revoked_jtis: set[str] = set()


# ─── JWT Primitives ───────────────────────────────────────────


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
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

    payload_bytes = base64url_decode(payload_b64)
    payload = json.loads(payload_bytes)

    # Check expiry
    exp = payload.get("exp")
    if exp is not None and time.time() > exp:
        raise ValueError("Token has expired")

    # Check revocation
    jti = payload.get("jti")
    if jti and jti in revoked_jtis:
        raise ValueError("Token has been revoked")

    return payload


def issue_tokens(user_id: str, username: str) -> dict[str, str]:
    now = time.time()
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_EXPIRY),
        "type": "access",
        "jti": access_jti,
    }
    refresh_payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_EXPIRY),
        "type": "refresh",
        "jti": refresh_jti,
    }

    return {
        "access_token": create_jwt(access_payload),
        "refresh_token": create_jwt(refresh_payload),
        "token_type": "Bearer",
    }


# ─── FastAPI Dependency ───────────────────────────────────────


async def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization[7:]
    try:
        payload = verify_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return payload


# ─── Request/Response Models ──────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    message: str


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = users_db.get(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_hash = user["password_hash"]
    provided_hash = hash_password(req.password)

    if not hmac.compare_digest(expected_hash, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    tokens = issue_tokens(user["user_id"], user["username"])
    return TokenResponse(**tokens)


@app.get("/protected", response_model=UserResponse)
async def protected(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        user_id=current_user["sub"],
        username=current_user["username"],
        message="Access granted to protected resource",
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest) -> TokenResponse:
    try:
        payload = verify_jwt(req.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Revoke old refresh token
    old_jti = payload.get("jti")
    if old_jti:
        revoked_jtis.add(old_jti)

    tokens = issue_tokens(payload["sub"], payload["username"])
    return TokenResponse(**tokens)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
