"""MC-BE-02: JWT Authentication Middleware — Manual HMAC-SHA256, no JWT libraries"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ── Configuration ───────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2024"
ACCESS_TOKEN_EXPIRE = 3600        # 1 hour
REFRESH_TOKEN_EXPIRE = 86400 * 7  # 7 days

# ── Manual JWT implementation ───────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _create_signature(data: str, secret: str) -> str:
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=data.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def create_token(
    subject: str,
    username: str,
    expires_in: int = ACCESS_TOKEN_EXPIRE,
    custom_claims: Optional[Dict[str, Any]] = None,
) -> str:
    # Header
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())

    # Payload
    now = int(time.time())
    payload_data: Dict[str, Any] = {
        "sub": subject,
        "username": username,
        "iat": now,
        "exp": now + expires_in,
    }
    if custom_claims:
        payload_data.update(custom_claims)
    payload = _b64url_encode(json.dumps(payload_data, separators=(",", ":")).encode())

    # Signature
    signing_input = f"{header}.{payload}"
    signature = _create_signature(signing_input, SECRET_KEY)

    return f"{signing_input}.{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = _create_signature(signing_input, SECRET_KEY)
        if not hmac.compare_digest(expected_sig.encode(), signature.encode()):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload_data = json.loads(payload_bytes)

        if int(time.time()) > payload_data.get("exp", 0):
            return None

        return payload_data
    except Exception:
        return None


# ── Mock user store ─────────────────────────────────────────────────

USERS: Dict[str, Dict[str, Any]] = {
    "john_doe": {
        "password": "demo_password",
        "sub": "user_123",
        "username": "john_doe",
        "email": "john@example.com",
        "roles": ["user", "admin"],
    },
    "jane_doe": {
        "password": "demo_password",
        "sub": "user_456",
        "username": "jane_doe",
        "email": "jane@example.com",
        "roles": ["user"],
    },
}

# ── Token blacklist ─────────────────────────────────────────────────

_blacklist: Set[str] = set()


def blacklist_token(token: str) -> None:
    _blacklist.add(token)


def is_blacklisted(token: str) -> bool:
    return token in _blacklist


# ── Pydantic models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ProtectedResponse(BaseModel):
    message: str
    user_data: Dict[str, Any]


# ── Auth dependency ─────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token = credentials.credentials

    if is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ── FastAPI App ─────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication API")


@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    user = USERS.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_token(
        subject=user["sub"],
        username=user["username"],
        expires_in=ACCESS_TOKEN_EXPIRE,
        custom_claims={"email": user["email"], "roles": user["roles"]},
    )

    refresh_token = create_token(
        subject=user["sub"],
        username=user["username"],
        expires_in=REFRESH_TOKEN_EXPIRE,
        custom_claims={"token_type": "refresh"},
    )

    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE,
        refresh_token=refresh_token,
    )


@app.get("/api/v1/auth/protected", response_model=ProtectedResponse)
async def protected_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ProtectedResponse:
    return ProtectedResponse(
        message="Access granted",
        user_data={
            "sub": current_user.get("sub"),
            "username": current_user.get("username"),
            "email": current_user.get("email"),
            "roles": current_user.get("roles", []),
            "issued_at": current_user.get("iat"),
            "expires_at": current_user.get("exp"),
        },
    )


@app.post("/api/v1/auth/refresh", response_model=LoginResponse)
async def refresh(req: RefreshRequest) -> LoginResponse:
    payload = verify_token(req.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token type mismatch — expected refresh token",
        )

    # Blacklist the old refresh token (token rotation)
    blacklist_token(req.refresh_token)

    new_access = create_token(
        subject=payload["sub"],
        username=payload["username"],
        expires_in=ACCESS_TOKEN_EXPIRE,
        custom_claims={
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
        },
    )

    new_refresh = create_token(
        subject=payload["sub"],
        username=payload["username"],
        expires_in=REFRESH_TOKEN_EXPIRE,
        custom_claims={"token_type": "refresh"},
    )

    return LoginResponse(
        access_token=new_access,
        expires_in=ACCESS_TOKEN_EXPIRE,
        refresh_token=new_refresh,
    )
