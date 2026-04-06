"""JWT Auth Middleware — MC-BE-02 (H × RRC, S2 Implementer)"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Configuration ───

SECRET_KEY = "super-secret-key-for-hmac-signing-do-not-expose"
ACCESS_TOKEN_TTL = 3600       # 1 hour
REFRESH_TOKEN_TTL = 604800    # 7 days

# ─── Mock User Store ───

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

USERS: dict[str, dict[str, str]] = {
    "john": {"password_hash": _hash_password("password123"), "user_id": "u001"},
    "jane": {"password_hash": _hash_password("password456"), "user_id": "u002"},
}

# ─── Base64url helpers ───

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

# ─── JWT creation / verification ───

def _create_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _verify_jwt(token: str, expected_type: str = "access") -> dict[str, Any]:
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
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    # Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Check expiry
    if "exp" in payload and payload["exp"] < time.time():
        raise HTTPException(status_code=401, detail="Token expired")

    # Check token type
    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=401,
            detail=f"Expected {expected_type} token, got {payload.get('type')}",
        )

    return payload

# ─── Token generation ───

def _generate_tokens(user_id: str, username: str) -> dict[str, str]:
    now = time.time()
    access_payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_TTL),
        "type": "access",
    }
    refresh_payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_TTL),
        "type": "refresh",
    }
    return {
        "access_token": _create_jwt(access_payload),
        "refresh_token": _create_jwt(refresh_payload),
    }

# ─── Token extraction helper ───

def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    return parts[1]

# ─── FastAPI Dependencies ───

async def require_auth(request: Request) -> dict[str, Any]:
    token = _extract_token(request)
    return _verify_jwt(token, expected_type="access")


async def require_refresh_token(request: Request) -> dict[str, Any]:
    token = _extract_token(request)
    return _verify_jwt(token, expected_type="refresh")

# ─── Request / Response Models ───

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

# ─── Application ───

app = FastAPI(title="JWT Auth Middleware")


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = USERS.get(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user["password_hash"] != _hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    tokens = _generate_tokens(user["user_id"], req.username)
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@app.get("/protected", response_model=ProtectedResponse)
async def protected(claims: dict[str, Any] = Depends(require_auth)) -> ProtectedResponse:
    return ProtectedResponse(
        message="You have access to this protected resource",
        user_id=claims["sub"],
        username=claims["username"],
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh(claims: dict[str, Any] = Depends(require_refresh_token)) -> TokenResponse:
    tokens = _generate_tokens(claims["sub"], claims["username"])
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )
