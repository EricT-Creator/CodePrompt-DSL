"""JWT Authentication System with FastAPI — HMAC-SHA256 signing via standard library only."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-abc123"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ─── Models ───────────────────────────────────────────────────────────────────

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


class UserResponse(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    message: str


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    roles: List[str]


# ─── In-Memory User Store ────────────────────────────────────────────────────

USERS_DB: Dict[str, User] = {
    "alice": User(
        id="user-001",
        username="alice",
        password_hash="password123",  # Plaintext for demo; use bcrypt in production
        roles=["admin", "user"],
    ),
    "bob": User(
        id="user-002",
        username="bob",
        password_hash="password456",
        roles=["user"],
    ),
    "charlie": User(
        id="user-003",
        username="charlie",
        password_hash="password789",
        roles=["editor", "user"],
    ),
}


# ─── JWT Implementation (Standard Library Only) ──────────────────────────────

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def sign_jwt(payload: dict, secret_key: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str, secret_key: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    header_b64, payload_b64, signature_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_signature_b64 = base64url_encode(expected_signature)

    if not hmac.compare_digest(signature_b64, expected_signature_b64):
        raise ValueError("Invalid signature")

    payload_json = base64url_decode(payload_b64)
    payload = json.loads(payload_json)

    # Check expiration
    exp = payload.get("exp")
    if exp is not None:
        now_ts = datetime.utcnow().timestamp()
        if now_ts > exp:
            raise ValueError("Token expired")

    return payload


# ─── Token Store ──────────────────────────────────────────────────────────────

class TokenStore:
    def __init__(self) -> None:
        self._refresh_tokens: Dict[str, dict] = {}
        self._revoked_tokens: Set[str] = set()

    def store_refresh_token(self, jti: str, user_id: str, expires_at: datetime) -> None:
        self._refresh_tokens[jti] = {
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        }

    def is_refresh_token_valid(self, jti: str) -> bool:
        if jti in self._revoked_tokens:
            return False
        token_data = self._refresh_tokens.get(jti)
        if not token_data:
            return False
        return datetime.utcnow() < token_data["expires_at"]

    def revoke_refresh_token(self, jti: str) -> None:
        self._revoked_tokens.add(jti)

    def get_user_id(self, jti: str) -> Optional[str]:
        data = self._refresh_tokens.get(jti)
        return data["user_id"] if data else None


token_store = TokenStore()


# ─── Token Creation Helpers ───────────────────────────────────────────────────

def create_access_token(user: User) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.id,
        "username": user.username,
        "roles": user.roles,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return sign_jwt(payload, SECRET_KEY)


def create_refresh_token(user: User) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user.id,
        "username": user.username,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti,
        "type": "refresh",
    }
    token_store.store_refresh_token(jti, user.id, exp)
    return sign_jwt(payload, SECRET_KEY)


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = USERS_DB.get(username)
    if user and user.password_hash == password:
        return user
    return None


def get_user_by_id(user_id: str) -> Optional[User]:
    for user in USERS_DB.values():
        if user.id == user_id:
            return user
    return None


# ─── FastAPI Dependencies ─────────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    try:
        payload = verify_jwt(token, SECRET_KEY)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.get("/protected", response_model=UserResponse)
async def protected_route(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        user_id=user.id,
        username=user.username,
        roles=user.roles,
        message=f"Hello {user.username}, you have access!",
    )


@app.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    try:
        payload = verify_jwt(request.refresh_token, SECRET_KEY)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    jti = payload.get("jti")
    if not jti or not token_store.is_refresh_token_valid(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or invalid",
        )

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new access token, keep same refresh token
    new_access_token = create_access_token(user)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
