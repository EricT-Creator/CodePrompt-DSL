from __future__ import annotations

import json
import hmac
import hashlib
import base64
import uuid
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# ─── Configuration ───

SECRET_KEY = "super-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRY = timedelta(days=7)

# ─── Mock user store ───

@dataclass
class User:
    id: str
    username: str
    password_hash: str  # In production, use bcrypt/scrypt


USERS: dict[str, User] = {
    "alice": User(id="u-001", username="alice", password_hash="password123"),
    "bob": User(id="u-002", username="bob", password_hash="secret456"),
    "charlie": User(id="u-003", username="charlie", password_hash="pass789"),
}

# Revoked refresh tokens
REVOKED_TOKENS: set[str] = set()


# ─── JWT Implementation (Manual HMAC + Base64) ───

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def encode_header() -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"))
    return b64url_encode(header_json.encode("utf-8"))


def encode_payload(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"))
    return b64url_encode(payload_json.encode("utf-8"))


def create_signature(message: str, secret: str) -> str:
    sig = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return b64url_encode(sig)


def verify_signature(header: str, payload: str, signature: str, secret: str = SECRET_KEY) -> bool:
    expected = create_signature(f"{header}.{payload}", secret)
    return hmac.compare_digest(signature, expected)


def sign_jwt(header: str, payload: str, secret: str = SECRET_KEY) -> str:
    signature = create_signature(f"{header}.{payload}", secret)
    return f"{header}.{payload}.{signature}"


def create_payload(
    sub: str,
    username: str,
    expires_delta: timedelta = ACCESS_TOKEN_EXPIRY,
    token_type: str = "access",
    jti: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "username": username,
        "type": token_type,
        "exp": int((now + expires_delta).timestamp()),
        "iat": int(now.timestamp()),
    }
    if jti:
        payload["jti"] = jti
    return payload


def generate_jwt(
    user_id: str,
    username: str,
    expires_delta: timedelta = ACCESS_TOKEN_EXPIRY,
    token_type: str = "access",
    jti: str | None = None,
) -> str:
    header = encode_header()
    payload = encode_payload(
        create_payload(user_id, username, expires_delta, token_type, jti)
    )
    return sign_jwt(header, payload)


def decode_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    header_b64, payload_b64, signature = parts

    if not verify_signature(header_b64, payload_b64, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload_json = b64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid payload")

    exp = payload.get("exp")
    if exp and datetime.now(timezone.utc).timestamp() > exp:
        raise HTTPException(status_code=401, detail="Token expired")

    return payload


# ─── Token Pair ───

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = int(ACCESS_TOKEN_EXPIRY.total_seconds())


def generate_token_pair(user_id: str, username: str) -> TokenPair:
    access_token = generate_jwt(user_id, username, ACCESS_TOKEN_EXPIRY, "access")
    jti = str(uuid.uuid4())
    refresh_token = generate_jwt(user_id, username, REFRESH_TOKEN_EXPIRY, "refresh", jti)
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TOKEN_EXPIRY.total_seconds()),
    )


# ─── Auth helpers ───

def authenticate_user(username: str, password: str) -> User | None:
    user = USERS.get(username)
    if user and user.password_hash == password:
        return user
    return None


def is_token_revoked(jti: str | None) -> bool:
    if jti is None:
        return False
    return jti in REVOKED_TOKENS


# ─── FastAPI App ───

app = FastAPI(title="JWT Auth System")
security = HTTPBearer()


# ─── Dependency ───

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    token = credentials.credentials
    payload = decode_jwt(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


# ─── Request models ───

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ─── Endpoints ───

@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    pair = generate_token_pair(user.id, user.username)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@app.get("/protected")
async def protected_route(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "message": "Access granted",
        "user_id": current_user["sub"],
        "username": current_user["username"],
    }


@app.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    payload = decode_jwt(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Token revoked")

    # Revoke old refresh token
    if jti:
        REVOKED_TOKENS.add(jti)

    user_id = payload["sub"]
    username = payload["username"]

    pair = generate_token_pair(user_id, username)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
