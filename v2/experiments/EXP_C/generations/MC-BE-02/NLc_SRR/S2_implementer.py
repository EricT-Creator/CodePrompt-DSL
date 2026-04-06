"""
MC-BE-02: FastAPI JWT Authentication System
Engineering Constraints: Python + FastAPI. Manual JWT via hmac+base64, no PyJWT.
stdlib + fastapi + uvicorn only. Single file. Endpoints: login, protected, refresh. Code only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ── Configuration ───────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production-2024"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_HOURS = 24

# ── Manual JWT Implementation ───────────────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


class JWTManager:
    def __init__(self, secret_key: str, expire_minutes: int = 30) -> None:
        self.secret_key = secret_key.encode("utf-8")
        self.expire_minutes = expire_minutes

    def _create_header(self) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        return _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))

    def _create_payload(self, user_id: str, username: str, extra: Optional[Dict[str, Any]] = None) -> str:
        now_ts = int(datetime.utcnow().timestamp())
        payload: Dict[str, Any] = {
            "sub": user_id,
            "username": username,
            "iat": now_ts,
            "exp": now_ts + self.expire_minutes * 60,
            "jti": str(uuid.uuid4()),
        }
        if extra:
            payload.update(extra)
        return _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _sign(self, header_b64: str, payload_b64: str) -> str:
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        return _b64url_encode(signature)

    def create_token(self, user_id: str, username: str, extra: Optional[Dict[str, Any]] = None) -> str:
        header_b64 = self._create_header()
        payload_b64 = self._create_payload(user_id, username, extra)
        sig_b64 = self._sign(header_b64, payload_b64)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_and_decode(self, token: str) -> Optional[Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        # Verify signature using constant-time comparison
        expected_sig = self._sign(header_b64, payload_b64)
        if not hmac.compare_digest(sig_b64, expected_sig):
            return None

        try:
            payload_json = _b64url_decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)
        except Exception:
            return None

        # Check expiration
        current_time = int(datetime.utcnow().timestamp())
        if payload.get("exp", 0) < current_time:
            return None

        return payload


# ── Refresh Token Manager ───────────────────────────────────────────────


@dataclass
class RefreshTokenInfo:
    user_id: str
    username: str
    created_at: datetime
    expires_at: datetime
    used: bool = False


class RefreshTokenManager:
    def __init__(self, expire_hours: int = 24) -> None:
        self.expire_hours = expire_hours
        self.tokens: Dict[str, RefreshTokenInfo] = {}

    def create(self, user_id: str, username: str) -> str:
        token = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.tokens[token_hash] = RefreshTokenInfo(
            user_id=user_id,
            username=username,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=self.expire_hours),
        )
        return token

    def validate(self, token: str) -> Optional[Dict[str, str]]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        info = self.tokens.get(token_hash)
        if not info:
            return None
        if info.used:
            return None
        if datetime.utcnow() > info.expires_at:
            del self.tokens[token_hash]
            return None
        # Rotate: mark used
        info.used = True
        return {"user_id": info.user_id, "username": info.username}

    def revoke_all_for_user(self, user_id: str) -> int:
        revoked = 0
        for info in self.tokens.values():
            if info.user_id == user_id and not info.used:
                info.used = True
                revoked += 1
        return revoked


# ── Mock User Store ─────────────────────────────────────────────────────


@dataclass
class User:
    id: str
    username: str
    password_hash: str  # In real app, use bcrypt
    email: str = ""
    is_active: bool = True


# Simple password hashing (NOT production-safe, just for demo constraints)
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


USERS_DB: Dict[str, User] = {
    "alice": User(id="u1", username="alice", password_hash=_hash_password("alice123"), email="alice@example.com"),
    "bob": User(id="u2", username="bob", password_hash=_hash_password("bob123"), email="bob@example.com"),
    "charlie": User(id="u3", username="charlie", password_hash=_hash_password("charlie123"), email="charlie@example.com"),
}


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = USERS_DB.get(username)
    if not user:
        return None
    if user.password_hash != _hash_password(password):
        return None
    if not user.is_active:
        return None
    return user


# ── Instances ───────────────────────────────────────────────────────────

jwt_manager = JWTManager(SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES)
refresh_manager = RefreshTokenManager(REFRESH_TOKEN_EXPIRE_HOURS)

# ── Request / Response Models ───────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    message: str
    expires_at: int


# ── Auth Dependency ─────────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = jwt_manager.verify_and_decode(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ── App ─────────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Authentication System")


@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = jwt_manager.create_token(user.id, user.username)
    refresh_token = refresh_manager.create(user.id, user.username)

    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    user_info = refresh_manager.validate(req.refresh_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_access = jwt_manager.create_token(user_info["user_id"], user_info["username"])
    new_refresh = refresh_manager.create(user_info["user_id"], user_info["username"])

    return TokenResponse(
        access_token=new_access,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh,
    )


@app.get("/auth/protected", response_model=UserInfoResponse)
async def protected_route(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserInfoResponse(
        user_id=current_user["sub"],
        username=current_user["username"],
        message=f"Hello {current_user['username']}! You are authenticated.",
        expires_at=current_user["exp"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
