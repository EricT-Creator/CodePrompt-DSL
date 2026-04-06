from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import uvicorn


# ── Configuration ───────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production"
ACCESS_TOKEN_TTL = 900  # 15 minutes
REFRESH_TOKEN_TTL = 604800  # 7 days


# ── Base64Url helpers ───────────────────────────────────────────────────

def b64url_encode(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ── JWT encode / decode ─────────────────────────────────────────────────

def jwt_encode(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = b64url_encode(json.dumps(header, separators=(",", ":")))
    p_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")))
    signing_input = f"{h_b64}.{p_b64}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = b64url_encode(sig)
    return f"{signing_input}.{sig_b64}"


def jwt_decode(token: str, secret: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    h_b64, p_b64, sig_b64 = parts

    # Verify signature
    signing_input = f"{h_b64}.{p_b64}"
    expected = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    provided = b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, provided):
        raise ValueError("Invalid signature")

    # Decode header
    header = json.loads(b64url_decode(h_b64))
    if header.get("alg") != "HS256":
        raise ValueError("Unsupported algorithm")

    # Decode payload
    payload = json.loads(b64url_decode(p_b64))

    # Check expiration
    exp = payload.get("exp")
    if exp is not None and time.time() > exp:
        raise ValueError("Token expired")

    return payload


# ── Token management ────────────────────────────────────────────────────

refresh_store: dict[str, dict[str, Any]] = {}

# Mock user database
USERS: dict[str, dict[str, Any]] = {
    "alice": {"password": "password123", "roles": ["admin", "user"]},
    "bob": {"password": "secret456", "roles": ["user"]},
}


def create_access_token(user_id: str, roles: list[str] | None = None) -> str:
    now = time.time()
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now),
        "exp": int(now + ACCESS_TOKEN_TTL),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if roles:
        payload["roles"] = roles
    return jwt_encode(payload, SECRET_KEY)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    now = time.time()
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now),
        "exp": int(now + REFRESH_TOKEN_TTL),
        "jti": jti,
        "type": "refresh",
    }
    token = jwt_encode(payload, SECRET_KEY)
    refresh_store[jti] = {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "revoked": False,
    }
    return token, jti


# ── FastAPI app ─────────────────────────────────────────────────────────

app = FastAPI(title="JWT Auth Service")
security = HTTPBearer()


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any]:
    try:
        payload = jwt_decode(cred.credentials, SECRET_KEY)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token")
    return {"user_id": payload["sub"], "roles": payload.get("roles", []), "claims": payload}


# ── Request / Response models ───────────────────────────────────────────

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


# ── Endpoints ───────────────────────────────────────────────────────────

@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = USERS.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = create_access_token(req.username, user.get("roles"))
    refresh, _ = create_refresh_token(req.username)
    return TokenResponse(access_token=access, refresh_token=refresh)


@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)) -> dict:
    return {
        "message": f"Hello, {user['user_id']}!",
        "user_id": user["user_id"],
        "roles": user["roles"],
    }


@app.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest) -> RefreshResponse:
    try:
        payload = jwt_decode(req.refresh_token, SECRET_KEY)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid refresh token: {exc}")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    jti = payload.get("jti")
    info = refresh_store.get(jti) if jti else None
    if not info or info.get("revoked"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or unknown")

    user_id = payload["sub"]
    user = USERS.get(user_id)
    roles = user.get("roles", []) if user else []
    new_access = create_access_token(user_id, roles)
    info["last_used_at"] = datetime.utcnow().isoformat()
    return RefreshResponse(access_token=new_access)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
